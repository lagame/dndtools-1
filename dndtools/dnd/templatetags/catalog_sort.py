"""Accessible links for server-side catalog sorting."""

from django import template
from django.utils.html import format_html
from django.utils.translation import gettext

register = template.Library()


@register.simple_tag(takes_context=True)
def sortable_header(context, paginator, key, label, css_class=''):
    if key not in paginator_sort_columns(paginator):
        return format_html('<th scope="col" class="{}">{}</th>', css_class, gettext(label))
    current = paginator.sort_key
    selected = current.lstrip('-') == key
    descending = current == '-' + key
    params = context['request'].GET.copy()
    params.pop('page', None)
    params['order'] = key if descending or not selected else '-' + key
    direction = 'descending' if descending else 'ascending' if selected else 'none'
    indicator = ' ↓' if descending else ' ↑' if selected else ''
    return format_html(
        '<th scope="col" class="{}" aria-sort="{}"><a href="?{}">{}{}</a></th>',
        css_class, direction, params.urlencode(), gettext(label), indicator)


def paginator_sort_columns(paginator):
    from dnd.catalog_ordering import SORT_COLUMNS
    if paginator is None or not hasattr(paginator, 'qs'):
        return {}
    return SORT_COLUMNS.get(paginator.qs.model.__name__, {})


@register.simple_tag(takes_context=True)
def editorial_sort_header(context, key, label, current):
    params = context['request'].GET.copy()
    params.pop('page', None)
    selected = current.lstrip('-') == key
    descending = current == '-' + key
    params['order'] = key if descending or not selected else '-' + key
    direction = 'descending' if descending else 'ascending' if selected else 'none'
    indicator = ' ↓' if descending else ' ↑' if selected else ''
    return format_html('<th scope="col" aria-sort="{}"><a href="?{}">{}{}</a></th>',
                       direction, params.urlencode(), gettext(label), indicator)
