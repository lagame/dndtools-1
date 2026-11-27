"""Submit item creation requirements for review without changing catalog data."""

import hashlib
import json
import secrets

from django import forms
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from dnd.editorial import can_propose
from dnd.item_requirements import (MAX_BYTES, RESOURCE, active_row, current_state, decode_submission, present_rows,
                                   publish_requirements, validate_submission)
from dnd.models import EditorialProposal, Item, Rulebook


ACTION = 'item_reqs'
PREVIEW_SESSION_KEY = 'item_requirement_preview'
PREVIEW_LIFETIME = 1200


def _snapshot_digest(snapshots):
    return hashlib.sha256(json.dumps(snapshots, sort_keys=True).encode('utf-8')).hexdigest()


def _envelope(items):
    return {'resource': RESOURCE, 'version': 1, 'items': items}


def _example_file():
    example = _envelope([{
        'item_id': 123, 'original_name': 'Example Shield Property', 'rulebook_id': 42, 'page': 10,
        'source': {'rulebook_id': 42, 'pages': [10, 11]},
        'requirements': {'op': 'all', 'children': [
            {'kind': 'feat', 'original_name': 'Example Feat', 'target_id': 456,
             'reference': {'rulebook_id': 13, 'page': 21}},
            {'op': 'any', 'children': [
                {'kind': 'spell', 'original_name': 'Example Spell',
                 'reference': {'rulebook_id': 24, 'page': 32}},
                {'kind': 'condition', 'en': 'Must have the example class feature.',
                 'pt_br': 'Deve ter a característica de classe do exemplo.'},
            ]},
        ]},
    }])
    return JsonResponse(example, json_dumps_params={'indent': 2, 'ensure_ascii': False}, headers={
        'Content-Disposition': 'attachment; filename="dndtools-item-creation-requirements-example.json"',
    })


def _read_upload(upload):
    if not upload or upload.size > MAX_BYTES or not upload.name.lower().endswith('.json'):
        raise forms.ValidationError(_('Choose a UTF-8 .json file up to 1 MiB.'))
    return decode_submission(upload.read(MAX_BYTES + 1))


def _item_row(item, source_book_id, source_pages, requirements):
    page_parts = [page.strip() for page in source_pages.split(',', 20)]
    try:
        if source_book_id is None or any(not page.isascii() or not page.isdecimal() for page in page_parts):
            raise ValueError
        pages = [int(page) for page in page_parts]
    except ValueError as error:
        raise forms.ValidationError(_('Choose a source rulebook and enter the printed pages separated by commas.')) from error
    return {
        'item_id': item.pk, 'original_name': item.name, 'rulebook_id': item.rulebook_id, 'page': item.page,
        'source': {'rulebook_id': source_book_id, 'pages': pages},
        'requirements': requirements,
    }


def preview_rows(envelope):
    """Show both the current catalog data and the wording the proposal would publish."""
    rows = envelope['items']
    items = (Item.objects.filter(pk__in=[row['item_id'] for row in rows])
             .select_related('rulebook', 'creation_requirements')
             .prefetch_related('required_feats', 'required_spells').in_bulk())
    current_rows = {item.pk: row for item in items.values() if (row := active_row(item)) is not None}
    current_structures = dict(zip(current_rows, present_rows(current_rows.values())))
    previews = []
    for row, proposed in zip(rows, present_rows(rows)):
        item = items.get(row['item_id'])
        previews.append({
            'item': item,
            'row': row,
            'current_text': item.required_extra if item else '',
            'current_links': [*item.required_feats.all(), *item.required_spells.all()] if item else [],
            'current_structure': current_structures.get(row['item_id']),
            'structured_requirements': proposed,
        })
    return previews


def approve_item_requirements(proposal):
    """Called by the existing proposal approval transaction after checking the owner."""
    if proposal.resource != 'Item':
        raise forms.ValidationError(_('This proposal must target an item.'))
    envelope, snapshots = validate_submission(proposal.payload, lock=True)
    if _snapshot_digest(snapshots) != proposal.source_digest:
        raise forms.ValidationError(_('The original changed after submission. Request a new proposal.'))
    publish_requirements(envelope, proposal)


@staff_member_required
@require_http_methods(['GET', 'HEAD', 'POST'])
@never_cache
def item_requirements_editor(request, target_pk=None):
    if not can_propose(request.user, 'Item', 'correct'):
        return HttpResponseForbidden()

    item = (get_object_or_404(Item.objects.select_related('creation_requirements', 'rulebook'), pk=target_pk)
            if target_pk is not None else None)
    if item is None and request.method in ('GET', 'HEAD') and request.GET.get('template') == 'json':
        return _example_file()

    current = getattr(item, 'creation_requirements', None)
    initial = current.requirements if current else None
    source_book_id = current.source['rulebook_id'] if current else (item.rulebook_id if item else None)
    source_pages = ', '.join(map(str, current.source['pages'])) if current else (str(item.page or '') if item else '')
    errors, preview, token = [], [], ''
    submitted_action = request.POST.get('action')
    if request.method == 'POST':
        try:
            if submitted_action == 'preview':
                request.session.pop(PREVIEW_SESSION_KEY, None)
                if item:
                    selection = request.POST.get('source_book_id', '')
                    source_book_id = (int(selection)
                                      if len(selection) <= 10 and selection.isascii() and selection.isdecimal()
                                      else None)
                    source_pages = request.POST.get('source_pages', '')
                    initial = decode_submission(request.POST.get('requirements', ''))
                    raw = _envelope([_item_row(item, source_book_id, source_pages, initial)])
                else:
                    raw = _read_upload(request.FILES.get('file'))
                envelope, snapshots = validate_submission(raw)
                preview = preview_rows(envelope)
                token = secrets.token_urlsafe(24)
                request.session[PREVIEW_SESSION_KEY] = {
                    'token': token, 'user': request.user.pk, 'target_pk': target_pk,
                    'created': timezone.now().timestamp(), 'envelope': envelope,
                    'digest': _snapshot_digest(snapshots),
                }
            elif submitted_action == 'submit':
                saved = request.session.get(PREVIEW_SESSION_KEY, {})
                if (not saved.get('token') or saved['token'] != request.POST.get('token')
                        or saved.get('user') != request.user.pk or saved.get('target_pk') != target_pk
                        or timezone.now().timestamp() - saved.get('created', 0) > PREVIEW_LIFETIME):
                    raise forms.ValidationError(_('Import preview expired. Upload the file again.') if item is None
                                                else _('The preview expired. Preview the prerequisites again.'))
                request.session.pop(PREVIEW_SESSION_KEY, None)
                envelope, snapshots = validate_submission(saved['envelope'])
                if _snapshot_digest(snapshots) != saved['digest']:
                    raise forms.ValidationError(_('The original changed after preview. Preview the prerequisites again.'))
                proposal = EditorialProposal.objects.create(
                    resource='Item', action=ACTION,
                    target_pk=envelope['items'][0]['item_id'] if len(envelope['items']) == 1 else None,
                    payload=envelope, source_digest=saved['digest'], source_reference='', author=request.user,
                )
                from dnd.editorial_views import notify_proposal
                notify_proposal(request, proposal)
                messages.success(request, _('Proposal submitted for Ronassic’s review.'))
                return redirect('editorial_dashboard')
            else:
                return HttpResponseForbidden()
        except forms.ValidationError as error:
            errors = error.messages
    return render(request, 'admin/editorial/item_requirements.html', {
        'title': _('Structure prerequisites') if item else _('Import creation prerequisites'),
        'item': item, 'rulebooks': Rulebook.objects.order_by('name') if item else [],
        'initial': initial, 'source_book_id': source_book_id, 'source_pages': source_pages,
        'stale': current_state(item) == 'stale' if item else False,
        'errors': errors, 'preview': preview, 'token': token,
    })


def requirements_review_context(proposal):
    preview, error = [], ''
    try:
        if proposal.status == 'pending':
            _, snapshots = validate_submission(proposal.payload)
            if _snapshot_digest(snapshots) != proposal.source_digest:
                error = _('The original changed after submission. Request a new proposal.')
        preview = preview_rows(proposal.payload)
    except forms.ValidationError as exc:
        error = '; '.join(exc.messages)
    return {'requirements_review': True, 'requirements_preview': preview, 'requirements_error': error}
