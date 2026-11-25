"""A review queue for catalog additions, corrections and complete translations."""

import hashlib
import logging
import secrets
import smtplib
from datetime import timedelta

from django import forms
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.conf import settings
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.db.models.functions import Collate
from django.http import Http404, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from dnd.editorial import (IMPORT_RESOURCES, RESOURCE_GROUPS, RESOURCE_LABELS, KIND_LABELS,
                           GRANT_CHOICES, approve, can_import, can_propose, editable_form,
                           model_for, owner, serialize_form, source_digest,
                           translation_form, validate_new_edition, detect_duplicate)
from dnd.models import CatalogImportBatch, CollaboratorInvite, EditorialGrant, EditorialProposal, SupplementalEntry
from dnd.editorial_import import (DOWNLOAD_FORMATS, INLINE_BYTES, INLINE_ROWS, MAX_BYTES, MAX_MIB, MAX_ROWS,
                                  ImportRowLimitError, example_file, preview_digest, publish_rows, validated_rows)
from dnd.editorial_batches import (CANCELLABLE_STATES, WORKING_STATES, enqueue_batch, notify_direct_import,
                                   review_expired, update_batch_from_review)
from dnd.supplemental.catalog import detail_for


logger = logging.getLogger(__name__)


@staff_member_required
@require_POST
def switch_account(request):
    logout(request)
    return redirect('/cdn-cgi/access/logout' if settings.ACCESS_REQUIRED else 'admin:login')


class SourceForm(forms.Form):
    source_reference = forms.CharField(
        label=_('Official D&D 3.5 source, page and editorial notes'),
        widget=forms.Textarea(attrs={'rows': 3}), max_length=2000)


class InviteForm(forms.Form):
    email = forms.EmailField(max_length=254, label=_('Email'))
    resources = forms.MultipleChoiceField(
        label=_('Catalog resources'),
        choices=GRANT_CHOICES,
        widget=forms.SelectMultiple(attrs={'size': 12}))
    permissions = forms.MultipleChoiceField(
        label=_('Permissions'),
        choices=(('create', _('Add records')),
                 ('correct', _('Correct records')),
                 ('translate', _('Translate records')), ('delete', _('Propose removals'))),
        widget=forms.CheckboxSelectMultiple)

    def clean_email(self):
        email = self.cleaned_data['email'].casefold()
        accounts = list(User.objects.filter(email__iexact=email).order_by('pk')[:2])
        if len(accounts) > 1:
            raise forms.ValidationError(_('Multiple Django accounts use this email. Resolve them before inviting.'))
        existing = accounts[0] if accounts else None
        if existing and (existing.is_superuser or not hasattr(existing, 'editorial_invite') or
                         existing.editorial_invite.access_state == 'active'):
            raise forms.ValidationError(_('This email already has an active or unrelated Django account.'))
        return email

class ActivationForm(forms.Form):
    code = forms.CharField(max_length=100, widget=forms.PasswordInput, label=_('Invitation code'))


def _dashboard_resource(user, name, label, *, kind=None):
    can_create = can_propose(user, name, 'create', kind=kind)
    if not can_create and not any(can_propose(user, name, action, kind=kind)
                                  for action in ('correct', 'translate', 'delete')):
        return None
    return {
        'name': name, 'label': label, 'kind': kind,
        'can_create': can_create,
        'can_import': can_create and can_import(user, name, kind=kind),
    }


@staff_member_required
def dashboard(request):
    groups = []
    for label, names in RESOURCE_GROUPS.items():
        if names == ('SupplementalEntry',):
            label = _('Additional D&D 3.5 mechanics')
            resources = [_dashboard_resource(request.user, 'SupplementalEntry', KIND_LABELS[kind], kind=kind)
                         for kind, _ in SupplementalEntry.KINDS]
        else:
            resources = [_dashboard_resource(request.user, name, RESOURCE_LABELS[name]) for name in names]
        available = [resource for resource in resources if resource is not None]
        if available:
            groups.append((label, available))
    is_owner = owner(request.user)
    proposals = (EditorialProposal.objects.all() if is_owner else
                 EditorialProposal.objects.filter(author=request.user))
    pending_count = proposals.filter(status='pending').count()
    proposals = list(proposals.select_related('author')[:30])
    for proposal in proposals:
        proposal.resource_label = RESOURCE_LABELS[proposal.resource]
    return render(request, 'admin/editorial/dashboard.html', {
        'groups': groups, 'pending_count': pending_count,
        'proposals': proposals,
        'collaborators': (CollaboratorInvite.objects.select_related('user').order_by('-created_at')[:50]
                          if is_owner else ()),
        'is_owner': is_owner, 'title': _('Editorial workspace'),
    })


@staff_member_required
def invite(request):
    if not owner(request.user):
        return HttpResponseForbidden()
    form = InviteForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        code = secrets.token_urlsafe(32)
        email = form.cleaned_data['email']
        try:
            with transaction.atomic():
                user = User.objects.select_for_update().filter(email__iexact=email).first()
                if user:
                    user.is_active = False
                    user.is_staff = True
                    user.set_unusable_password()
                    user.save(update_fields=('is_active', 'is_staff', 'password'))
                    record = user.editorial_invite
                    record.token_hash = hashlib.sha256(code.encode()).hexdigest()
                    record.expires_at = timezone.now() + timedelta(days=7)
                    record.access_state = 'pending'
                    record.activated_at = None
                    record.save(update_fields=('token_hash', 'expires_at', 'access_state', 'activated_at'))
                    EditorialGrant.objects.filter(user=user).delete()
                else:
                    user = User(username='editor-' + secrets.token_hex(6), email=email,
                                is_staff=True, is_active=False)
                    user.set_unusable_password()
                    user.save()
                    CollaboratorInvite.objects.create(
                        user=user, token_hash=hashlib.sha256(code.encode()).hexdigest(),
                        expires_at=timezone.now() + timedelta(days=7))
                for resource in form.cleaned_data['resources']:
                    EditorialGrant.objects.create(
                        user=user, resource=resource,
                        can_create='create' in form.cleaned_data['permissions'],
                        can_correct='correct' in form.cleaned_data['permissions'],
                        can_translate='translate' in form.cleaned_data['permissions'],
                        can_delete='delete' in form.cleaned_data['permissions'])
                sent = send_mail(
                    'D&D Tools: convite para colaborar',
                    'Abra https://%s%s após entrar no Cloudflare Access com seu e-mail e autenticador.\n'
                    'Use o campo Email no Cloudflare; o botão Cloudflare é para administradores da conta.\n\n'
                    'Código do convite (válido por 7 dias): %s\n\n'
                    'O código do Cloudflare recebido por e-mail é diferente deste código do convite.\n'
                    'Após a ativação, não é preciso criar outra senha.\n'
                    'Suas propostas só serão publicadas após aprovação de Ronassic.\n'
                    % (settings.PUBLIC_HOST, reverse('editorial_activate'), code),
                    settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
                if sent != 1:
                    raise smtplib.SMTPException('Invitation email was not accepted.')
        except (OSError, smtplib.SMTPException) as error:
            logger.warning('Editorial invitation email failed: %s', type(error).__name__)
            form.add_error(None, _('The invitation could not be sent. Please try again; no account was changed.'))
        else:
            messages.success(request, _('Invitation emailed. The collaborator must complete Cloudflare MFA and activation.'))
            return redirect('editorial_dashboard')
    return render(request, 'admin/editorial/invite.html', {
        'title': _('Invite collaborator'), 'form': form,
    })


def activate(request):
    """Activate an Access-authenticated invitee with an emailed one-time code."""
    email = getattr(request, 'access_email', None)
    if not email:
        return HttpResponseForbidden(_('Cloudflare Access sign-in required.'))
    invitations = list(CollaboratorInvite.objects.select_related('user').filter(
        user__email__iexact=email, access_state='pending').order_by('pk')[:2])
    if len(invitations) != 1:
        if request.user.is_authenticated:
            return redirect('editorial_dashboard')
        return HttpResponseForbidden(_('No pending invitation for this Access identity.'))
    invite_record = invitations[0]
    form = ActivationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        digest = hashlib.sha256(form.cleaned_data['code'].encode()).hexdigest()
        if (timezone.now() >= invite_record.expires_at or
                not secrets.compare_digest(digest, invite_record.token_hash)):
            form.add_error('code', _('Code invalid or expired.'))
        if not form.errors:
            with transaction.atomic():
                invite_record = CollaboratorInvite.objects.select_for_update().select_related('user').get(
                    pk=invite_record.pk)
                if (invite_record.access_state != 'pending' or timezone.now() >= invite_record.expires_at or
                        not secrets.compare_digest(digest, invite_record.token_hash)):
                    return HttpResponseForbidden(_('Invitation no longer available.'))
                invite_record.user.is_active = True
                invite_record.user.save(update_fields=('is_active',))
                invite_record.access_state = 'active'
                invite_record.token_hash = ''
                invite_record.activated_at = timezone.now()
                invite_record.save(update_fields=('access_state', 'token_hash', 'activated_at'))
            login(request, invite_record.user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, _('Account activated. Your Cloudflare identity now signs you in.'))
            return redirect('editorial_dashboard')
    response = render(request, 'admin/editorial/activate.html', {
        'title': _('Activate editorial access'), 'form': form, 'email': email,
        'expired': timezone.now() >= invite_record.expires_at,
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
    messages.success(request, _('Django access revoked immediately. Synchronize the Access group as well.'))
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
        return HttpResponseForbidden(_('Select a catalog type from the editorial workspace.'))
    if not any(can_propose(request.user, resource, action, kind=kind or None)
               for action in ('create', 'correct', 'translate', 'delete')):
        return HttpResponseForbidden()
    related_fields = [field.name for field in model._meta.concrete_fields
                      if field.many_to_one and any(related.name == 'name'
                                                   for related in field.related_model._meta.concrete_fields)]
    entries = model.objects.select_related(*related_fields).order_by('pk')
    if kind:
        entries = entries.filter(kind=kind)
    query = request.GET.get('q', '').strip()[:100]
    if query:
        if query.isdigit():
            entries = entries.filter(pk=int(query))
        else:
            lookups = Q()
            aliases = {}
            if any(field.name == 'name' for field in model._meta.concrete_fields):
                aliases['search_name'] = Collate(F('name'), 'utf8mb4_0900_ai_ci')
                lookups |= Q(search_name__contains=query)
            for field in related_fields:
                alias = 'search_' + field
                aliases[alias] = Collate(F(field + '__name'), 'utf8mb4_0900_ai_ci')
                lookups |= Q(**{alias + '__contains': query})
            entries = entries.alias(**aliases).filter(lookups) if lookups else entries.none()
    return render(request, 'admin/editorial/catalog.html', {
        'title': KIND_LABELS.get(kind, RESOURCE_LABELS[resource]),
        'resource': resource,
        'query': query,
        'kind': kind,
        'entries': Paginator(entries, 50).get_page(request.GET.get('page')),
        'can_create': can_propose(request.user, resource, 'create', kind=kind or None),
        'can_import': can_import(request.user, resource, kind=kind or None),
        'can_correct': can_propose(request.user, resource, 'correct', kind=kind or None),
        'can_translate': can_propose(request.user, resource, 'translate', kind=kind or None),
        'can_delete': can_propose(request.user, resource, 'delete', kind=kind or None),
    })


@staff_member_required
@require_http_methods(['GET', 'HEAD', 'POST'])
def import_catalog(request, resource):
    if resource not in IMPORT_RESOURCES:
        raise Http404
    kind = request.GET.get('kind', '') if resource == 'SupplementalEntry' else ''
    if resource == 'SupplementalEntry' and kind not in dict(SupplementalEntry.KINDS):
        raise Http404
    if not can_import(request.user, resource, kind=kind or None):
        return HttpResponseForbidden()
    file_format = request.GET.get('template')
    if request.method in ('GET', 'HEAD') and file_format in DOWNLOAD_FORMATS:
        extension = 'json' if file_format == 'json' else 'csv'
        media_type = 'application/json' if extension == 'json' else 'text/csv'
        response = HttpResponse(example_file(resource, kind, file_format),
                                content_type=media_type + '; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="dndtools-%s-%s-example.%s"' % (
            kind or resource.lower(), file_format, extension)
        response['Cache-Control'] = 'no-store'
        return response
    preview = None
    if request.method == 'POST':
        if request.POST.get('confirm'):
            saved = request.session.get('editorial_import_preview', {})
            if (saved.get('token') != request.POST.get('token') or saved.get('user') != request.user.pk
                    or saved.get('resource') != resource or saved.get('kind') != kind or not saved.get('digest')
                    or timezone.now().timestamp() - saved.get('created', 0) > 1200):
                messages.error(request, _('Import preview expired. Upload the file again.'))
            else:
                request.session.pop('editorial_import_preview', None)
                try:
                    count = publish_rows(saved['content'], resource, kind, request.user,
                                         json_file=saved['json_file'], expected_digest=saved['digest'], wait=False)
                except (forms.ValidationError, ValueError) as error:
                    detail = '; '.join(error.messages) if isinstance(error, forms.ValidationError) else str(error)
                    messages.error(request, _('Nothing was published: %(error)s') % {'error': detail})
                except IntegrityError:
                    messages.error(request, _('The catalog changed while publishing. Nothing was saved. Upload the file again.'))
                else:
                    if not notify_direct_import(request.user, resource, kind, count):
                        messages.warning(request, _('Records published, but the email alert could not be sent.'))
                    messages.success(request, ngettext(
                        'Published %(count)s catalog record.',
                        'Published %(count)s catalog records.', count) % {'count': count})
                    return redirect(reverse('editorial_catalog', kwargs={'resource': resource},
                                            query={'kind': kind} if kind else None))
        else:
            request.session.pop('editorial_import_preview', None)
            upload = request.FILES.get('file')
            if not upload or upload.size > MAX_BYTES or not upload.name.lower().endswith(('.csv', '.json')):
                messages.error(request, _('Choose a UTF-8 .csv or .json file up to %(mib)s MiB.') % {
                    'mib': MAX_MIB,
                })
            else:
                json_file = upload.name.lower().endswith('.json')
                try:
                    content = upload.read(MAX_BYTES + 1).decode('utf-8-sig')
                    if upload.size > INLINE_BYTES:
                        return _queue_import(request, resource, kind, content, json_file=json_file)
                    rows = validated_rows(content, resource, kind, json_file=json_file, max_rows=INLINE_ROWS)
                    digest = preview_digest(rows)
                except UnicodeError:
                    messages.error(request, _('The file must use UTF-8 encoding.'))
                except ImportRowLimitError:
                    return _queue_import(request, resource, kind, content, json_file=json_file)
                except forms.ValidationError as error:
                    messages.error(request, '; '.join(error.messages))
                else:
                    preview = rows
                    request.session['editorial_import_preview'] = {
                        'token': secrets.token_urlsafe(24), 'user': request.user.pk,
                        'resource': resource, 'kind': kind,
                        'created': timezone.now().timestamp(), 'content': content,
                        'json_file': json_file, 'digest': digest,
                    }
    label = KIND_LABELS.get(kind, RESOURCE_LABELS[resource])
    response = render(request, 'admin/editorial/import.html', {
        'title': _('Import catalog records — %(resource)s') % {'resource': label},
        'resource': resource, 'kind': kind,
        'preview': preview, 'token': request.session.get('editorial_import_preview', {}).get('token')
        if preview else '',
        'resource_label': label,
        'max_rows': MAX_ROWS, 'max_mib': MAX_MIB,
        'recent_batch': (CatalogImportBatch.objects.only('pk', 'state')
                         .filter(author=request.user, resource=resource, kind=kind).order_by('-pk').first()),
    })
    response['Cache-Control'] = 'no-store'
    return response


def _queue_import(request, resource, kind, content, *, json_file):
    batch, created = enqueue_batch(request.user, resource, kind, content, json_file=json_file)
    if not created:
        messages.warning(request, _('Finish or cancel the current batch before uploading another large file.'))
    return redirect('editorial_import_batch', batch.pk)


@staff_member_required
@require_http_methods(['GET', 'HEAD', 'POST'])
@never_cache
def import_batch(request, batch_id):
    batch = get_object_or_404(CatalogImportBatch.objects.defer('payload', 'preview'), pk=batch_id,
                              author=request.user)
    if not can_import(request.user, batch.resource, kind=batch.kind or None):
        return HttpResponseForbidden()
    if request.method == 'POST':
        update_batch_from_review(batch.pk, request.user, request.POST.get('action'))
        return redirect('editorial_import_batch', batch.pk)
    if review_expired(batch):
        batch.state = CatalogImportBatch.State.EXPIRED
    working = batch.state in WORKING_STATES or batch.notify_pending
    if request.GET.get('status') == '1':
        return JsonResponse({
            'state': batch.state, 'processed': batch.processed, 'working': working,
        })
    preview = Paginator(batch.preview, 50).get_page(request.GET.get('page')) if batch.state == 'ready' else None
    return render(request, 'admin/editorial/import_batch.html', {
        'title': _('Import batch #%(number)s') % {'number': batch.pk},
        'batch': batch,
        'resource_label': KIND_LABELS.get(batch.kind, RESOURCE_LABELS[batch.resource]),
        'preview': preview, 'working': working,
        'can_cancel': batch.state in CANCELLABLE_STATES,
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
    query_kind = request.GET.get('kind', '') if resource == 'SupplementalEntry' else ''
    kind = (query_kind or (request.POST.get('kind', '') if request.method == 'POST' else '')
            or (target.kind if target else '')) if resource == 'SupplementalEntry' else ''
    if kind:
        if kind not in dict(SupplementalEntry.KINDS) or (target and target.kind != kind):
            raise Http404
    if not can_propose(request.user, resource, action, kind=kind or (target.kind if resource == 'SupplementalEntry' and target else None)):
        return HttpResponseForbidden()
    if resource == 'SupplementalEntry' and action == 'create' and not kind and not owner(request.user) and not EditorialGrant.objects.filter(user=request.user, resource='SupplementalEntry', can_create=True).exists():
        return HttpResponseForbidden(_('Select a catalog type from the editorial workspace.'))
    original_digest = (source_digest(target, translation=action == 'translate')
                       if target and request.method == 'POST' else '')
    structured = request.GET.get('structured') == '1'
    legacy_supplemental = (resource == 'SupplementalEntry' and action == 'correct'
                           and target is not None and detail_for(target) is None)
    Form = (translation_form(target) if action == 'translate' else
            editable_form(resource, kind=kind if action == 'create' or target else None,
                          target=target, structured=structured) if action != 'delete' else None)
    form = (Form(request.POST or None, instance=target) if action not in ('translate', 'delete') else
            Form(request.POST or None) if action == 'translate' else None)
    if action == 'create' and kind:
        form.fields['kind'].initial = kind
        form.fields['kind'].widget = forms.HiddenInput()
    source_form = SourceForm(request.POST or None)
    if request.method == 'POST' and (form is None or form.is_valid()) and source_form.is_valid():
        if action == 'create':
            try:
                if query_kind and form.cleaned_data.get('kind') != query_kind:
                    raise forms.ValidationError(_('The selected catalog type changed. Reload the form.'))
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
                    messages.warning(request, _('Proposal saved, but the email alert could not be sent. '
                                                  'The pending queue still shows it.'))
            messages.success(request, _('Proposal submitted for Ronassic’s review.'))
            return redirect('editorial_dashboard')
    return render(request, 'admin/editorial/propose.html', {
        'title': '%s — %s' % ({'create': _('Propose addition'), 'correct': _('Propose correction'),
                              'translate': _('Propose translation'), 'delete': _('Propose removal')}[action],
                             RESOURCE_LABELS[resource]),
        'resource': resource,
        'action': action, 'target': target, 'form': form, 'source_form': source_form,
        'kind': kind, 'legacy_supplemental': legacy_supplemental, 'structured': structured,
    })


@staff_member_required
def review(request, proposal_id):
    if not owner(request.user):
        return HttpResponseForbidden()
    proposal = get_object_or_404(EditorialProposal.objects.select_related('author', 'reviewer'), pk=proposal_id)
    original = (model_for(proposal.resource).objects.filter(pk=proposal.target_pk).first()
                if proposal.target_pk else None)
    review_rows = []
    if proposal.resource == 'SupplementalEntry' and proposal.action in ('create', 'correct'):
        from dnd.supplemental.catalog import detail_for
        typed = any(name.startswith('detail_') for name in proposal.payload)
        form = editable_form(proposal.resource,
                             kind=proposal.payload.get('kind') if typed else None,
                             target=original, structured=typed)()
        detail = detail_for(original) if original else None
        for name, value in proposal.payload.items():
            field = form.fields.get(name)
            before = ''
            if original:
                if name.startswith('detail_') and detail:
                    if name == 'detail_class_levels':
                        before = '\n'.join('%s | %s' % (row.character_class.name, row.level)
                                           for row in detail.class_levels.select_related('character_class'))
                    else:
                        before = getattr(detail, name[7:], '')
                elif not name.startswith('detail_'):
                    before = getattr(original, name, '')
            if isinstance(field, forms.ModelMultipleChoiceField):
                value = ', '.join(str(item) for item in field.queryset.filter(pk__in=value or []))
                if detail and name == 'detail_monsters':
                    before = ', '.join(str(item) for item in detail.monsters.all())
            elif isinstance(field, forms.ModelChoiceField):
                value = (field.queryset.filter(pk=value).first() or value) if value else ''
            review_rows.append((field.label if field else name, before, value))
    return render(request, 'admin/editorial/review.html', {
        'title': _('Review proposal'), 'proposal': proposal,
        'resource_label': RESOURCE_LABELS[proposal.resource],
        'original': original, 'review_rows': review_rows,
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
        messages.success(request, _('Proposal approved and published.'))
    elif decision == 'reject':
        with transaction.atomic():
            proposal = EditorialProposal.objects.select_for_update().get(pk=proposal_id)
            if proposal.status != 'pending':
                messages.error(request, _('This proposal has already been reviewed.'))
                return redirect('editorial_review', proposal_id=proposal.pk)
            proposal.status = 'rejected'
            proposal.review_note = request.POST.get('review_note', '').strip()[:2000]
            proposal.reviewer = request.user
            proposal.reviewed_at = timezone.now()
            proposal.save(update_fields=('status', 'review_note', 'reviewer', 'reviewed_at'))
        messages.success(request, _('Proposal rejected.'))
    else:
        return HttpResponseForbidden()
    return redirect('editorial_dashboard')
