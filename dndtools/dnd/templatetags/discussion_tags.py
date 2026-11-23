"""Attach forum discussions only to real catalog detail pages."""

from django import template
from django.conf import settings

register = template.Library()

DETAILS = {
    'spell_detail': ('spell', 'spell'),
    'feat_detail': ('feat', 'feat'),
    'monster_detail': ('monster', 'monster'),
    'creature_template_detail': ('creature_template', 'entry'),
    'supplemental_detail': ('supplemental', 'entry'),
    'rulebook_detail': ('rulebook', 'rulebook'),
    'character_class_detail': ('character_class', 'character_class'),
    'character_class_variant_detail': ('character_class_variant', 'selected_variant'),
    'skill_detail': ('skill', 'skill'),
    'skill_variant_detail': ('skill_variant', 'selected_variant'),
    'race_detail': ('race', 'race'),
    'item_detail': ('item', 'item'),
    'rule_detail': ('rule', 'rule'),
    'deity_detail': ('deity', 'deity'),
    'language_detail': ('language', 'language'),
}


@register.inclusion_tag('dnd/discussions/widget.html', takes_context=True)
def record_discussions(context):
    if not settings.FORUM_ENABLED:
        return {}
    request = context.get('request')
    route = getattr(getattr(request, 'resolver_match', None), 'url_name', None)
    mapping = DETAILS.get(route)
    if not mapping:
        return {}
    kind, object_key = mapping
    record = context.get(object_key)
    if not record:
        return {}
    return {'discussion_kind': kind, 'discussion_id': record.pk}
