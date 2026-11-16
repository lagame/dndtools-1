"""Render approved complete PT-BR records while retaining source-language URLs."""

from django import template
from django.db import models
from django.utils.translation import gettext
from types import SimpleNamespace

from dnd.editorial import source_digest
from dnd.models import PublishedTranslation
from dnd.templatetags.catalog_html import safe_catalog_html
from dnd.utilities import update_html_cache_attributes

register = template.Library()


def _translation(context, obj):
    request = context.get('request')
    if (request is None or getattr(request, 'LANGUAGE_CODE', 'en-us') != 'pt-br'
            or not isinstance(obj, models.Model) or not obj.pk):
        return None
    resource = obj._meta.object_name
    cache = getattr(request, '_catalog_translations', None)
    if cache is None:
        cache = request._catalog_translations = {}
    if resource not in cache:
        cache[resource] = {row.target_pk: row for row in PublishedTranslation.objects.filter(
            resource=resource, locale='pt-br')}
    row = cache[resource].get(obj.pk)
    if row and row.source_digest == source_digest(obj, translation=True):
        return row.payload
    return None


@register.simple_tag(takes_context=True)
def localized(context, obj, field):
    values = _translation(context, obj)
    original = obj.get(field, '') if isinstance(obj, dict) else getattr(obj, field, '')
    value = values.get(field, original) if values else original
    if field == 'name' and value != original:
        return '%s (%s: %s)' % (value, gettext('Original EN'), original)
    return value


@register.simple_tag(takes_context=True)
def localized_html(context, obj, field):
    values = _translation(context, obj)
    if values and field in values:
        temporary = SimpleNamespace(**{field: values[field]})
        update_html_cache_attributes(temporary, field)
        return safe_catalog_html(getattr(temporary, field + '_html'))
    return safe_catalog_html(getattr(obj, field + '_html', ''))


@register.simple_tag(takes_context=True)
def translation_notice(context, obj):
    request = context.get('request')
    if request and getattr(request, 'LANGUAGE_CODE', 'en-us') == 'pt-br' and not _translation(context, obj):
        return gettext('This record is still available only in its original English version.')
    return ''
