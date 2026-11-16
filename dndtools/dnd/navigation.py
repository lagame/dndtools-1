"""Catalog navigation shared by desktop and compact layouts."""

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from dnd.models import DndEdition

LABELS = {
    'Rulebooks': _('Rulebooks'), 'All rulebooks': _('All rulebooks'),
    'Editions': _('Editions'), 'Rules': _('Rules'), 'Conditions': _('Conditions'),
    'Character Options': _('Character Options'), 'Classes': _('Classes'),
    'Feats': _('Feats'), 'Feat categories': _('Feat categories'),
    'Traits': _('Traits'), 'Flaws': _('Flaws'), 'Skill tricks': _('Skill tricks'),
    'Skills': _('Skills'), 'Skills by rulebook': _('Skills by rulebook'),
    'Deities': _('Deities'), 'Languages': _('Languages'), 'Magic': _('Magic'),
    'Spells': _('Spells'), 'Spells by rulebook': _('Spells by rulebook'),
    'Spell schools': _('Spell schools'), 'Descriptors': _('Descriptors'),
    'Domains': _('Domains'), 'Shadow casting': _('Shadow casting'),
    'Invocations': _('Invocations'), 'Psionics': _('Psionics'),
    'Auras': _('Auras'), 'Maneuvers': _('Maneuvers'),
    'Bestiary': _('Bestiary'), 'Races': _('Races'),
    'Race types': _('Race types'), 'Races by rulebook': _('Races by rulebook'),
    'Monsters': _('Monsters'), 'Monsters by rulebook': _('Monsters by rulebook'),
    'Monster types': _('Monster types'), 'Monster subtypes': _('Monster subtypes'),
    'Monstrous traits': _('Monstrous traits'), 'Templates': _('Templates'),
    'Items': _('Items'), 'Magical items': _('Magical items'),
    'Items by rulebook': _('Items by rulebook'),
    'Mundane / alchemical': _('Mundane / alchemical'),
    'Contacts': _('Contacts'), 'News': _('News'), 'Contact us': _('Contact us'),
    'Maintainer': _('Maintainer'), 'Android': _('Android'), 'My D&D': _('My D&D'),
}


def _link(label, route=None, *, children=(), kwargs=None, url=None, planned=False):
    return {
        'label': LABELS.get(label, label),
        'url': url if url is not None else reverse(route, kwargs=kwargs) if route else '',
        'children': list(children),
        'planned': planned,
    }


def catalog_navigation(request):
    editions = list(DndEdition.objects.order_by('name'))
    edition_groups = []
    for system in ('DnD 3.5', 'DnD 3.0'):
        matches = [edition for edition in editions if edition.system == system]
        if matches:
            edition_groups.append(_link(system.replace('DnD ', 'D&D '), children=[
                _link(edition.name, url=edition.get_absolute_url()) for edition in matches
            ]))

    items = [
        _link('Rulebooks', 'rulebook_list', children=[
            _link('All rulebooks', 'rulebook_list'),
            _link('Editions', 'edition_list', children=edition_groups),
            _link('Rules', 'rule_list', children=[
                _link('Conditions', 'rule_condition_list'),
            ]),
        ]),
        _link('Character Options', 'character_class_list', children=[
            _link('Classes', 'character_class_list'),
            _link('Feats', 'feat_index', children=[
                _link('Feat categories', 'feat_category_list', children=[
                    _link('Traits', 'feat_category_detail', kwargs={'category_slug': 'trait'}),
                    _link('Flaws', 'feat_category_detail', kwargs={'category_slug': 'flaw'}),
                    _link('Skill tricks', 'feat_category_detail', kwargs={'category_slug': 'skill-trick'}),
                ]),
            ]),
            _link('Skills', 'skill_list', children=[
                _link('Skills by rulebook', 'skills_list_by_rulebook'),
            ]),
            _link('Deities', 'deity_list'),
            _link('Languages', 'language_index'),
        ]),
        _link('Magic', 'spell_index', children=[
            _link('Spells', 'spell_index', children=[
                _link('Spells by rulebook', 'spell_list_by_rulebook'),
            ]),
            _link('Spell schools', 'spell_school_list'),
            _link('Descriptors', 'spell_descriptor_list'),
            _link('Domains', 'spell_domain_list'),
            _link('Shadow casting', 'supplemental_index', kwargs={'kind': 'mysteries'}),
            _link('Invocations', 'supplemental_index', kwargs={'kind': 'invocations'}),
            _link('Psionics', 'supplemental_index', kwargs={'kind': 'psionics'}),
            _link('Auras', 'supplemental_index', kwargs={'kind': 'auras'}),
            _link('Maneuvers', 'supplemental_index', kwargs={'kind': 'maneuvers'}),
        ]),
        _link('Bestiary', 'race_index', children=[
            _link('Races', 'race_index', children=[
                _link('Race types', 'race_type_index'),
                _link('Races by rulebook', 'race_list_by_rulebook'),
            ]),
            _link('Monsters', 'monster_index', children=[
                _link('Monsters by rulebook', 'monster_list_by_rulebook'),
                _link('Monster types', 'monster_type_list'),
                _link('Monster subtypes', 'monster_subtype_list'),
            ]),
            _link('Monstrous traits', 'supplemental_index', kwargs={'kind': 'monstrous-traits'}),
            _link('Templates', 'creature_template_index'),
        ]),
        _link('Items', 'item_index', children=[
            _link('Magical items', 'item_index'),
            _link('Items by rulebook', 'item_list_by_rulebook'),
            _link('Mundane / alchemical', url=reverse('item_index') + '?type=MUN&_filter=1'),
        ]),
        _link('Contacts', 'contact', children=[
            _link('News', 'index'),
            _link('Contact us', 'contact'),
            _link('Maintainer', 'staff'),
            _link('Android', 'android'),
        ]),
        _link('My D&D', planned=True),
    ]

    path = request.path
    next_id = 0

    def mark(nodes):
        nonlocal next_id
        for node in nodes:
            next_id += 1
            node['id'] = 'catalog-nav-%d' % next_id
            mark(node['children'])
            node['current'] = bool(node['url'] and path == node['url'])
            node['active'] = node['current'] or any(child['active'] for child in node['children'])
            if node['url'] and node['children'] and path.startswith(node['url']):
                node['active'] = True

    mark(items)
    return items
