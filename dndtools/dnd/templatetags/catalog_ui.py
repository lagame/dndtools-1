"""Shared controls for removing an individual GET filter."""

from django import template


register = template.Library()
IGNORED = {'page', 'page_size', '_filter'}


def _choice_label(field, value):
    if field is None:
        return value
    for option_value, label in field.choices if hasattr(field, 'choices') else ():
        if isinstance(label, (list, tuple)):
            for nested_value, nested_label in label:
                if str(nested_value) == value:
                    return str(nested_label)
        elif str(option_value) == value:
            return str(label)
    return value


@register.simple_tag(takes_context=True)
def filter_chips(context):
    request = context['request']
    form = context.get('spell_filter_form')
    if form is None and context.get('filter') is not None:
        form = context['filter'].form
    if form is None:
        return []
    chips = []
    for key, values in request.GET.lists():
        if key in IGNORED or key not in form.fields:
            continue
        field = form.fields[key]
        for value in values:
            if not value or value.lower() == 'false' and field.__class__.__name__ == 'BooleanField':
                continue
            remaining = request.GET.copy()
            other_values = remaining.getlist(key)
            other_values.remove(value)
            if other_values:
                remaining.setlist(key, other_values)
            else:
                del remaining[key]
            remaining.pop('page', None)
            query = remaining.urlencode()
            chips.append({
                'label': '%s: %s' % (field.label or key, _choice_label(field, value)),
                'url': request.path + ('?' + query if query else ''),
            })
    return chips
