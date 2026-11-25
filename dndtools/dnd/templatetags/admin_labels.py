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


@register.inclusion_tag('admin/change_list_results.html')
def localized_result_list(changelist):
    context = result_list(changelist)
    for field, header in zip(changelist.list_display, context['result_headers']):
        if isinstance(field, str) and field in FIELD_LABELS:
            header['text'] = FIELD_LABELS[field]
    return context
