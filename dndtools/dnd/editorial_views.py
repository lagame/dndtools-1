"""A review queue for catalog additions, corrections and complete translations."""

import hashlib
import logging
import secrets
import smtplib
from datetime import timedelta

from django import forms
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F
from django.db.models.functions import Collate
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from dnd.editorial import (RESOURCE_GROUPS, GRANT_CHOICES, approve, can_propose, editable_form,
                           model_for, owner, serialize_form, source_digest,
                           translation_form, validate_new_edition, detect_duplicate)
from dnd.models import CollaboratorInvite, EditorialGrant, EditorialProposal, SupplementalEntry


logger = logging.getLogger(__name__)


class SourceForm(forms.Form):
    source_reference = forms.CharField(
        label='Official D&D 3.5 source, page and editorial notes',
        widget=forms.Textarea(attrs={'rows': 3}), max_length=2000)


class InviteForm(forms.Form):
    email = forms.EmailField(max_length=254)
    resources = forms.MultipleChoiceField(
        choices=GRANT_CHOICES,
        widget=forms.SelectMultiple(attrs={'size': 12}))
    permissions = forms.MultipleChoiceField(
        choices=(('create', 'Add records'), ('correct', 'Correct records'),
                 ('translate', 'Translate records'), ('delete', 'Propose removals')),
        widget=forms.CheckboxSelectMultiple)

    def clean_email(self):
        email = self.cleaned_data['email'].casefold()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('This email already has a Django account. Review it before inviting.')
        return email


class ActivationForm(forms.Form):
    code = forms.CharField(max_length=100, widget=forms.PasswordInput)
    password1 = forms.CharField(widget=forms.PasswordInput, label='New password')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Repeat password')

    def clean(self):
        data = super().clean()
        if data.get('password1') != data.get('password2'):
            raise forms.ValidationError('Passwords do not match.')
        return data


@staff_member_required
def dashboard(request):
    groups = [(label, [(name, model_for(name)._meta.verbose_name_plural.title(),
                        can_propose(request.user, name, 'create'),
                        can_propose(request.user, name, 'correct'),
                        can_propose(request.user, name, 'translate'),
                        can_propose(request.user, name, 'delete'))
                       for name in names if name != 'SupplementalEntry'])
              for label, names in RESOURCE_GROUPS.items()]
    proposals = (EditorialProposal.objects.all() if owner(request.user) else
                 EditorialProposal.objects.filter(author=request.user))
    return render(request, 'admin/editorial/dashboard.html', {
        'groups': groups, 'pending_count': proposals.filter(status='pending').count(),
        'proposals': proposals.select_related('author')[:30],
        'collaborators': (CollaboratorInvite.objects.select_related('user').order_by('-created_at')[:50]
                          if owner(request.user) else ()),
        'supplemental_kinds': [(kind, label) for kind, label in SupplementalEntry.KINDS
                               if any(can_propose(request.user, 'SupplementalEntry', action, kind=kind)
                                      for action in ('create', 'correct', 'translate', 'delete'))],
        'is_owner': owner(request.user), 'title': 'Editorial workspace',
    })


@staff_member_required
def invite(request):
    if not owner(request.user):
        return HttpResponseForbidden()
    form = InviteForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        code = secrets.token_urlsafe(32)
        email = form.cleaned_data['email']
        with transaction.atomic():
            username = 'editor-' + secrets.token_hex(6)
            user = User(username=username, email=email, is_staff=True, is_active=False)
            user.set_unusable_password()
            user.save()
            for resource in form.cleaned_data['resources']:
                EditorialGrant.objects.create(
                    user=user, resource=resource,
                    can_create='create' in form.cleaned_data['permissions'],
                    can_correct='correct' in form.cleaned_data['permissions'],
                    can_translate='translate' in form.cleaned_data['permissions'],
                    can_delete='delete' in form.cleaned_data['permissions'])
            CollaboratorInvite.objects.create(
                user=user, token_hash=hashlib.sha256(code.encode()).hexdigest(),
                expires_at=timezone.now() + timedelta(days=7))
        response = render(request, 'admin/editorial/invite_code.html', {
            'title': 'Invite created', 'email': email, 'code': code,
        })
        response['Cache-Control'] = 'no-store'
        return response
    return render(request, 'admin/editorial/invite.html', {
        'title': 'Invite collaborator', 'form': form,
    })


def activate(request):
    """Access-authenticated invitees set their own password via a one-time code."""
    email = getattr(request, 'access_email', None)
    if not email:
        return HttpResponseForbidden('Cloudflare Access sign-in required.')
    invite_record = CollaboratorInvite.objects.select_related('user').filter(
        user__email__iexact=email, access_state='pending').first()
    if not invite_record:
        return HttpResponseForbidden('No pending invitation for this Access identity.')
    form = ActivationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        digest = hashlib.sha256(form.cleaned_data['code'].encode()).hexdigest()
        if (timezone.now() >= invite_record.expires_at or
                not secrets.compare_digest(digest, invite_record.token_hash)):
            form.add_error('code', 'Code invalid or expired.')
        else:
            try:
                validate_password(form.cleaned_data['password1'], user=invite_record.user)
            except forms.ValidationError as error:
                form.add_error('password1', error)
        if not form.errors:
            with transaction.atomic():
                invite_record = CollaboratorInvite.objects.select_for_update().select_related('user').get(
                    pk=invite_record.pk)
                if (invite_record.access_state != 'pending' or
                        not secrets.compare_digest(digest, invite_record.token_hash)):
                    return HttpResponseForbidden('Invitation no longer available.')
                invite_record.user.set_password(form.cleaned_data['password1'])
                invite_record.user.is_active = True
                invite_record.user.save(update_fields=('password', 'is_active'))
                invite_record.access_state = 'active'
                invite_record.token_hash = ''
                invite_record.activated_at = timezone.now()
                invite_record.save(update_fields=('access_state', 'token_hash', 'activated_at'))
            messages.success(request, 'Account activated. Sign in with your new password.')
            return redirect('admin:login')
    response = render(request, 'admin/editorial/activate.html', {
        'title': 'Activate editorial access', 'form': form, 'email': email,
    })
    response['Cache-Control'] = 'no-store'
    return response


@staff_member_required
@require_POST
def revoke(request, invite_id):
    if not owner(request.user):
        return HttpResponseForbidden()
    with transaction.atomic():
        record = get_object_or_404(CollaboratorInvite.objects.select_for_update().select_related('user'), pk=invite_id)
        record.user.is_active = False
        record.user.save(update_fields=('is_active',))
        record.access_state = 'revoked'
        record.token_hash = ''
        record.save(update_fields=('access_state', 'token_hash'))
    messages.success(request, 'Django access revoked immediately. Synchronize the Access group as well.')
    return redirect('editorial_dashboard')


@staff_member_required
def catalog(request, resource):
    try:
        model = model_for(resource)
    except ValueError:
        raise Http404
    kind = request.GET.get('kind', '') if resource == 'SupplementalEntry' else ''
    if kind:
        if kind not in dict(SupplementalEntry.KINDS):
            raise Http404
    if resource == 'SupplementalEntry' and not kind and not owner(request.user):
        return HttpResponseForbidden('Select a catalog type from the editorial workspace.')
    if not any(can_propose(request.user, resource, action, kind=kind or None)
               for action in ('create', 'correct', 'translate', 'delete')):
        return HttpResponseForbidden()
    entries = model.objects.all().order_by('pk')
    if kind:
        entries = entries.filter(kind=kind)
    query = request.GET.get('q', '').strip()[:100]
    if query:
        if query.isdigit():
            entries = entries.filter(pk=int(query))
        elif any(field.name == 'name' for field in model._meta.concrete_fields):
            entries = entries.alias(search_name=Collate(F('name'), 'utf8mb4_0900_ai_ci')).filter(
                search_name__contains=query)
        else:
            entries = entries.none()
    return render(request, 'admin/editorial/catalog.html', {
        'title': model._meta.verbose_name_plural.title(),
        'resource': resource, 'resource_label': model._meta.verbose_name_plural.title(),
        'query': query,
        'kind': kind, 'kind_label': dict(SupplementalEntry.KINDS).get(kind, ''),
        'entries': Paginator(entries, 50).get_page(request.GET.get('page')),
        'can_create': can_propose(request.user, resource, 'create', kind=kind or None),
        'can_correct': can_propose(request.user, resource, 'correct', kind=kind or None),
        'can_translate': can_propose(request.user, resource, 'translate', kind=kind or None),
        'can_delete': can_propose(request.user, resource, 'delete', kind=kind or None),
    })


@staff_member_required
def propose(request, resource, action, target_pk=None):
    if action not in ('create', 'correct', 'translate', 'delete'):
        return HttpResponseForbidden()
    try:
        model = model_for(resource)
    except ValueError:
        raise Http404
    if (action == 'create') != (target_pk is None):
        raise Http404
    target = get_object_or_404(model, pk=target_pk) if target_pk else None
    kind = request.GET.get('kind', '') if resource == 'SupplementalEntry' else ''
    if kind:
        if kind not in dict(SupplementalEntry.KINDS) or (target and target.kind != kind):
            raise Http404
    if not can_propose(request.user, resource, action, kind=kind or (target.kind if resource == 'SupplementalEntry' and target else None)):
        return HttpResponseForbidden()
    if resource == 'SupplementalEntry' and action == 'create' and not kind and not owner(request.user) and not EditorialGrant.objects.filter(user=request.user, resource='SupplementalEntry', can_create=True).exists():
        return HttpResponseForbidden('Select a catalog type from the editorial workspace.')
    original_digest = (source_digest(target, translation=action == 'translate')
                       if target and request.method == 'POST' else '')
    Form = (translation_form(target) if action == 'translate' else
            editable_form(resource) if action != 'delete' else None)
    form = (Form(request.POST or None, instance=target) if action not in ('translate', 'delete') else
            Form(request.POST or None) if action == 'translate' else None)
    if action == 'create' and kind:
        form.fields['kind'].initial = kind
        form.fields['kind'].widget = forms.HiddenInput()
    source_form = SourceForm(request.POST or None)
    if request.method == 'POST' and (form is None or form.is_valid()) and source_form.is_valid():
        if action == 'create':
            try:
                if kind and form.cleaned_data.get('kind') != kind:
                    raise forms.ValidationError('The selected catalog type changed. Reload the form.')
                validate_new_edition(resource, form)
                detect_duplicate(resource, form)
            except forms.ValidationError as error:
                form.add_error(None, error)
        if form is None or not form.errors:
            proposal = EditorialProposal.objects.create(
                resource=resource, action=action, target_pk=target_pk,
                locale='pt-br' if action == 'translate' else '',
                payload=serialize_form(form) if form is not None else {},
                source_reference=source_form.cleaned_data['source_reference'],
                source_digest=original_digest,
                author=request.user,
            )
            if settings.EDITORIAL_NOTIFY_EMAIL:
                try:
                    send_mail(
                        'D&D Tools: new collaboration #%s' % proposal.pk,
                        'A %s proposal for %s is pending review. Open the private editorial queue.'
                        % (action, resource),
                        settings.DEFAULT_FROM_EMAIL,
                        [settings.EDITORIAL_NOTIFY_EMAIL], fail_silently=False,
                    )
                except (OSError, smtplib.SMTPException):
                    logger.exception('Editorial email notification failed for proposal %s', proposal.pk)
                    messages.warning(request, 'Proposal saved, but the email alert could not be sent. '
                                              'The pending queue still shows it.')
            messages.success(request, 'Proposal submitted for Ronassic’s review.')
            return redirect('editorial_dashboard')
    return render(request, 'admin/editorial/propose.html', {
        'title': '%s %s' % (action.title(), model._meta.verbose_name),
        'resource': resource,
        'action': action, 'target': target, 'form': form, 'source_form': source_form,
        'kind': kind,
    })


@staff_member_required
def review(request, proposal_id):
    if not owner(request.user):
        return HttpResponseForbidden()
    proposal = get_object_or_404(EditorialProposal.objects.select_related('author', 'reviewer'), pk=proposal_id)
    return render(request, 'admin/editorial/review.html', {
        'title': 'Review proposal', 'proposal': proposal,
        'original': (model_for(proposal.resource).objects.filter(pk=proposal.target_pk).first()
                     if proposal.target_pk else None),
    })


@staff_member_required
@require_POST
def decide(request, proposal_id):
    if not owner(request.user):
        return HttpResponseForbidden()
    proposal = get_object_or_404(EditorialProposal, pk=proposal_id)
    decision = request.POST.get('decision')
    if decision == 'approve':
        try:
            approve(proposal, request.user)
        except (forms.ValidationError, ValueError) as error:
            messages.error(request, str(error))
            return redirect('editorial_review', proposal_id=proposal.pk)
        messages.success(request, 'Proposal approved and published.')
    elif decision == 'reject':
        with transaction.atomic():
            proposal = EditorialProposal.objects.select_for_update().get(pk=proposal_id)
            if proposal.status != 'pending':
                messages.error(request, 'This proposal has already been reviewed.')
                return redirect('editorial_review', proposal_id=proposal.pk)
            proposal.status = 'rejected'
            proposal.review_note = request.POST.get('review_note', '').strip()[:2000]
            proposal.reviewer = request.user
            proposal.reviewed_at = timezone.now()
            proposal.save(update_fields=('status', 'review_note', 'reviewer', 'reviewed_at'))
        messages.success(request, 'Proposal rejected.')
    else:
        return HttpResponseForbidden()
    return redirect('editorial_dashboard')
