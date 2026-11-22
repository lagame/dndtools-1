"""Structured data for public catalog pages."""

import json

from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _


register = template.Library()


def _json_ld(data):
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    payload = payload.replace('&', r'\u0026').replace('<', r'\u003C').replace('>', r'\u003E')
    return mark_safe('<script type="application/ld+json">' + payload + '</script>')


_INDEXES = {
    'rulebook_list': 'Rulebooks', 'spell_index': 'Spells', 'feat_index': 'Feats',
    'character_class_list': 'Classes', 'skill_list': 'Skills',
    'race_index': 'Races', 'monster_index': 'Monsters',
    'item_index': 'Items', 'rule_list': 'Rules',
    'creature_template_index': 'Creature templates',
}
_DETAILS = {
    'rulebook_detail': ('rulebook_list', 'rulebook'),
    'spell_detail': ('spell_index', 'spell'),
    'feat_detail': ('feat_index', 'feat'),
    'character_class_detail': ('character_class_list', 'character_class'),
    'skill_detail': ('skill_list', 'skill'),
    'race_detail': ('race_index', 'race'),
    'monster_detail': ('monster_index', 'monster'),
    'item_detail': ('item_index', 'item'),
    'creature_template_detail': ('creature_template_index', 'entry'),
}


@register.simple_tag(takes_context=True)
def catalog_breadcrumb_json_ld(context):
    request = context.get('request')
    if not request or request.GET or context.get('translation_fallback'):
        return ''
    route = getattr(request.resolver_match, 'url_name', None)
    if route in _INDEXES:
        category_route = route
        name = _(str(_INDEXES[route]))
    elif route in _DETAILS and not context.get('use_canonical_link'):
        category_route, object_key = _DETAILS[route]
        obj = context.get(object_key)
        if obj is None:
            return ''
        name = obj.name
    else:
        return ''
    origin = context['seo_origin']
    category_url = origin + reverse(category_route)
    entries = [
        {'@type': 'ListItem', 'position': 1, 'name': _('Home'), 'item': origin + reverse('index')},
        {'@type': 'ListItem', 'position': 2, 'name': _(str(_INDEXES[category_route])),
         'item': category_url},
    ]
    if route in _DETAILS:
        entries.append({'@type': 'ListItem', 'position': 3, 'name': name,
                        'item': context['seo_canonical_url']})
    return _json_ld({'@context': 'https://schema.org', '@type': 'BreadcrumbList',
                     'itemListElement': entries})


@register.simple_tag
def catalog_book_json_ld(rulebook, canonical_url):
    if rulebook.publication_type == 'periodical' or rulebook.slug == 'web':
        return ''
    data = {'@context': 'https://schema.org', '@type': 'Book',
            'name': rulebook.name, 'url': canonical_url}
    if rulebook.publication_year:
        data['datePublished'] = str(rulebook.publication_year)
    return _json_ld(data)
