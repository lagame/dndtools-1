from django import template
from django.contrib.admin.templatetags.admin_list import result_list
from django.utils.translation import gettext_lazy as _

from dnd.editorial import FIELD_LABELS, RESOURCE_LABELS


register = template.Library()

OTHER_LABELS = {
    'NewsEntry': _('News entries'),
    'StaticPage': _('Static pages'),
    'EditorialGrant': _('Editorial grants'),
    'AccessAttempt': _('Access attempts'),
    'AccessFailureLog': _('Access failures'),
    'AccessLog': _('Access logs'),
}


@register.filter
def admin_model_label(model):
    if isinstance(model, dict):
        name = model.get('object_name')
        fallback = model.get('name', '')
    else:
        name = model.object_name
        fallback = model.verbose_name_plural
    return RESOURCE_LABELS.get(name, OTHER_LABELS.get(name, fallback))


@register.filter
def editorial_preview_label(field, form):
    if field == 'resource':
        return _('Resource')
    if field == 'source_reference':
        return _('Source')
    if field in FIELD_LABELS:
        return FIELD_LABELS[field]
    form_field = form.fields.get(field)
    return form_field.label if form_field and form_field.label else field.replace('_', ' ').capitalize()


@register.filter
def editorial_preview_value(value, field):
    if field == 'resource' and isinstance(value, str):
        return RESOURCE_LABELS.get(value, value)
    if isinstance(value, bool):
        return _('Yes') if value else _('No')
    if isinstance(value, (list, tuple)):
        return ', '.join(str(part) for part in value)
    return value


@register.inclusion_tag('admin/change_list_results.html')
def localized_result_list(changelist):
    context = result_list(changelist)
    for field, header in zip(changelist.list_display, context['result_headers']):
        if isinstance(field, str) and field in FIELD_LABELS:
            header['text'] = FIELD_LABELS[field]
    return context
