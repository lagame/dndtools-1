"""Apply an approved full-record translation to a response-local model instance."""

from dnd.editorial import source_digest, translatable_fields
from dnd.models import PublishedTranslation
from dnd.models import SupplementalEntry
from dnd.utilities import update_html_cache_attributes


def localize_record(request, obj):
    """Return whether PT-BR fell back to original English for this record."""
    if getattr(request, 'LANGUAGE_CODE', 'en-us') != 'pt-br':
        return False
    if hasattr(obj, '_dnd_locale_fallback'):
        return obj._dnd_locale_fallback
    row = PublishedTranslation.objects.filter(
        resource=obj._meta.object_name, target_pk=obj.pk, locale='pt-br').first()
    if row is None or row.source_digest != source_digest(obj, translation=True):
        obj._dnd_locale_fallback = True
        return True
    if 'name' in row.payload and row.payload['name'] != getattr(obj, 'name', None):
        obj.original_english_name = obj.name
    allowed = translatable_fields(obj)
    for field, value in row.payload.items():
        if field in allowed:
            if field.startswith('detail_') and isinstance(obj, SupplementalEntry):
                from dnd.supplemental.catalog import detail_for
                setattr(detail_for(obj), field[7:], value)
            else:
                setattr(obj, field, value)
                if hasattr(obj, field + '_html'):
                    update_html_cache_attributes(obj, field)
    obj._dnd_locale_fallback = False
    return False
