"""Durable processing for uploads that exceed the inline import limits."""

import base64
import gzip
import hashlib
import logging
import smtplib
from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.mail import get_connection, send_mail
from django.db import IntegrityError, InterfaceError, OperationalError, connection, transaction
from django.utils import timezone
from django.utils.translation import get_language, gettext as _, override

from dnd.editorial import KIND_LABELS, RESOURCE_LABELS, can_import
from dnd.editorial_import import preview_digest, publish_rows, validated_rows
from dnd.models import CatalogImportBatch


logger = logging.getLogger(__name__)
State = CatalogImportBatch.State
WORKING_STATES = (State.QUEUED, State.VALIDATING, State.APPROVED, State.PUBLISHING)
CANCELLABLE_STATES = (State.QUEUED, State.READY, State.APPROVED)
PENDING_STATES = (*WORKING_STATES, State.READY)
REVIEW_LIFETIME = timedelta(hours=24)
HISTORY_LIFETIME = timedelta(days=7)


def notify_direct_import(user, resource, kind, count):
    if not settings.EDITORIAL_NOTIFY_EMAIL:
        return True
    try:
        sent = send_mail(_('D&D Tools: direct catalog import'),
                         _('%(email)s published %(count)s records in %(resource)s. '
                           'Review the private editorial history.') % {
                             'email': user.email, 'count': count,
                             'resource': KIND_LABELS.get(kind, RESOURCE_LABELS[resource]),
                         }, settings.DEFAULT_FROM_EMAIL, [settings.EDITORIAL_NOTIFY_EMAIL],
                         fail_silently=False, connection=get_connection(timeout=12))
        if sent != 1:
            raise smtplib.SMTPException('Import notification was not accepted.')
        return True
    except (OSError, smtplib.SMTPException):
        logger.warning('Editorial import email notification failed')
        return False


def _update(batch, **fields):
    CatalogImportBatch.objects.filter(pk=batch.pk).update(updated_at=timezone.now(), **fields)


def _finish(batch, state, **fields):
    _update(batch, state=state, payload='', preview=[], digest='', **fields)


def review_expired(batch):
    return batch.state == State.READY and batch.updated_at < timezone.now() - REVIEW_LIFETIME


@transaction.atomic
def enqueue_batch(user, resource, kind, content, *, json_file):
    # Lock the author so simultaneous uploads cannot create two active batches.
    User.objects.select_for_update().only('pk').get(pk=user.pk)
    existing = (CatalogImportBatch.objects.defer('payload', 'preview')
                .filter(author=user, state__in=PENDING_STATES).order_by('pk').first())
    if existing:
        if review_expired(existing):
            _finish(existing, State.EXPIRED)
        else:
            return existing, False
    # Base64 limits SQL escaping overhead even for a full 40 MiB of incompressible input.
    payload = base64.b64encode(gzip.compress(content.encode('utf-8'), compresslevel=1)).decode('ascii')
    batch = CatalogImportBatch.objects.create(
        author=user, resource=resource, kind=kind, payload=payload, json_file=json_file,
        language=get_language() or 'en-us',
    )
    return batch, True


@transaction.atomic
def update_batch_from_review(batch_id, user, action):
    batch = (CatalogImportBatch.objects.select_for_update().defer('payload', 'preview')
             .get(pk=batch_id, author=user))
    if review_expired(batch):
        _finish(batch, State.EXPIRED)
    elif action == 'confirm' and batch.state == State.READY:
        _update(batch, state=State.APPROVED)
    elif action == 'cancel' and batch.state in CANCELLABLE_STATES:
        _finish(batch, State.CANCELLED)


def _validate(batch, content):
    rows = validated_rows(
        content, batch.resource, batch.kind, json_file=batch.json_file,
        progress=lambda count: _update(batch, processed=count),
    )
    summary = [
        (number, form.cleaned_data['name'], str(form.cleaned_data['rulebook']), raw['source_reference'].strip())
        for number, raw, form in rows
    ]
    _update(batch, state=State.READY, count=len(rows), processed=len(rows),
            digest=preview_digest(rows), preview=summary)


@transaction.atomic
def _publish(batch, content):
    count = publish_rows(content, batch.resource, batch.kind, batch.author,
                         json_file=batch.json_file, expected_digest=batch.digest)
    _finish(batch, State.PUBLISHED, count=count, notify_pending=True)


def _process_batch(batch):
    validating = batch.state in (State.QUEUED, State.VALIDATING)
    pending_state = State.QUEUED if validating else State.APPROVED
    active_state = State.VALIDATING if validating else State.PUBLISHING
    # The status transition serializes against cancellation.
    changed = CatalogImportBatch.objects.filter(pk=batch.pk, state__in=(pending_state, active_state)).update(
        state=active_state, processed=0 if validating else batch.count, updated_at=timezone.now())
    if not changed:
        return
    with override(batch.language):
        try:
            if not can_import(batch.author, batch.resource, kind=batch.kind or None):
                raise PermissionDenied
            content = gzip.decompress(base64.b64decode(batch.payload, validate=True)).decode('utf-8')
            if validating:
                _validate(batch, content)
            else:
                _publish(batch, content)
        except PermissionDenied:
            _finish(batch, State.FAILED, error=_('Your import permission has changed. Nothing was published.'))
        except forms.ValidationError as error:
            _finish(batch, State.FAILED, error='; '.join(error.messages))
        except IntegrityError:
            _finish(batch, State.FAILED, error=_(
                'The catalog changed while publishing. Nothing was saved. Upload the file again.'))
        except (InterfaceError, OperationalError):
            # If MySQL disconnects, leave the phase queued for recovery on the next connection.
            raise
        except Exception as error:
            logger.error('Unexpected error processing editorial import batch %s (%s)',
                         batch.pk, type(error).__name__)
            _finish(batch, State.FAILED, error=_('The import could not be processed. Nothing was published.'))


def process_next_batch():
    # A restarted worker can resume an active phase once the old connection releases this lock.
    lock_name = 'editorial_import_' + hashlib.sha256(connection.settings_dict['NAME'].encode()).hexdigest()[:32]
    with connection.cursor() as cursor:
        cursor.execute('SELECT GET_LOCK(%s, 0)', [lock_name])
        if cursor.fetchone()[0] != 1:
            return False
    try:
        now = timezone.now()
        CatalogImportBatch.objects.filter(state=State.READY, updated_at__lt=now - REVIEW_LIFETIME).update(
            state=State.EXPIRED, payload='', preview=[], digest='', updated_at=now)
        CatalogImportBatch.objects.filter(notify_pending=False, updated_at__lt=now - HISTORY_LIFETIME).exclude(
            state__in=PENDING_STATES).delete()
        notification = (CatalogImportBatch.objects.select_related('author').defer('payload', 'preview')
                        .filter(state=State.PUBLISHED, notify_pending=True).order_by('pk').first())
        if notification:
            with override(notification.language):
                sent = notify_direct_import(notification.author, notification.resource,
                                            notification.kind, notification.count)
            _update(notification, notify_pending=False, notify_failed=not sent)
            return True
        batch = (CatalogImportBatch.objects.select_related('author').defer('preview')
                 .filter(state__in=WORKING_STATES).order_by('pk').first())
        if not batch:
            return False
        _process_batch(batch)
        return True
    finally:
        with connection.cursor() as cursor:
            cursor.execute('SELECT RELEASE_LOCK(%s)', [lock_name])
