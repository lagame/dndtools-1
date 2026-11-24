from django import template
from django.utils.translation import gettext_lazy as _

from dnd.editorial import RESOURCE_LABELS


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
