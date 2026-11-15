"""Ranked, accent-insensitive search over the published catalog."""

from django.core.paginator import Paginator
from django.db.models import Case, F, IntegerField, Q, Value, When
from django.db.models.functions import Collate
from django.http import JsonResponse
from django.shortcuts import render

from dnd.models import (
    CharacterClassVariant, Deity, DndEdition, Domain, Feat, FeatCategory,
    Item, Language, Monster, MonsterSubtype, MonsterType, Race, RaceType,
    Rule, Rulebook, RuleCondition, Skill, Spell, SpellDescriptor, SpellSchool,
    SpellSubSchool,
)


COLLATION = 'utf8mb4_0900_ai_ci'
SOURCES = (
    ('spells', 'Spells', Spell, 'name', ('description',), ('rulebook__dnd_edition',)),
    ('feats', 'Feats', Feat, 'name', ('description', 'benefit'), ('rulebook__dnd_edition',)),
    ('classes', 'Classes', CharacterClassVariant, 'character_class__name',
     ('class_features',), ('character_class', 'rulebook__dnd_edition')),
    ('skills', 'Skills', Skill, 'name', (), ()),
    ('races', 'Races', Race, 'name', ('description',), ('rulebook__dnd_edition',)),
    ('monsters', 'Monsters', Monster, 'name', ('description',), ('rulebook__dnd_edition',)),
    ('items', 'Items', Item, 'name', ('description',), ('rulebook__dnd_edition',)),
    ('rulebooks', 'Rulebooks', Rulebook, 'name', ('description',), ('dnd_edition',)),
    ('editions', 'Editions', DndEdition, 'name', (), ()),
    ('domains', 'Domains', Domain, 'name', (), ()),
    ('languages', 'Languages', Language, 'name', (), ()),
    ('deities', 'Deities', Deity, 'name', ('description',), ()),
    ('rules', 'Rules', Rule, 'name', ('body',), ('rulebook__dnd_edition',)),
    ('conditions', 'Conditions', RuleCondition, 'name', ('description',), ()),
    ('schools', 'Spell schools', SpellSchool, 'name', (), ()),
    ('subschools', 'Spell sub-schools', SpellSubSchool, 'name', (), ()),
    ('descriptors', 'Descriptors', SpellDescriptor, 'name', (), ()),
    ('feat_categories', 'Feat categories', FeatCategory, 'name', (), ()),
    ('race_types', 'Race types', RaceType, 'name', (), ()),
    ('monster_types', 'Monster types', MonsterType, 'name', (), ()),
    ('monster_subtypes', 'Monster subtypes', MonsterSubtype, 'name', (), ()),
)


def _matches(source, query, names_only=False):
    _, _, model, name, fields, related = source
    aliases = {'_search_name': Collate(F(name), COLLATION)}
    if not names_only:
        aliases.update({f'_search_field_{index}': Collate(F(field), COLLATION)
                        for index, field in enumerate(fields)})
    matches = Q(_search_name__contains=query)
    if not names_only:
        for index in range(len(fields)):
            matches |= Q(**{f'_search_field_{index}__contains': query})
    return (model.objects.select_related(*related).alias(**aliases).filter(matches)
            .annotate(_rank=Case(
                When(_search_name__exact=query, then=Value(0)),
                When(_search_name__startswith=query, then=Value(1)),
                When(_search_name__contains=query, then=Value(2)),
                default=Value(3), output_field=IntegerField(),
            )).order_by('_rank', name, 'pk'))


def _result(source, obj):
    key, label = source[:2]
    title = obj.character_class.name if key == 'classes' else obj.name
    book = getattr(obj, 'rulebook', None)
    edition = book.dnd_edition if book else getattr(obj, 'dnd_edition', None)
    return {
        'title': title, 'url': obj.get_absolute_url(), 'category': label,
        'book': book.name if book else '',
        'edition': edition.name if edition else '',
        'rank': obj._rank,
    }


def search(request):
    query = request.GET.get('q', '').strip()[:100]
    selected = request.GET.get('category', '')
    error = ''
    if selected and selected not in {source[0] for source in SOURCES}:
        error = 'Unknown search category. Select a category from the list.'
    sections = []
    if query and not error:
        for source in SOURCES:
            key, label = source[:2]
            if selected and selected != key:
                continue
            matches = _matches(source, query)
            count = matches.count()
            if not count and not selected:
                continue
            page = Paginator(matches, 30).get_page(request.GET.get('page')) if selected else None
            objects = page.object_list if page else matches[:8]
            sections.append({
                'key': key, 'label': label, 'count': count,
                'results': [_result(source, obj) for obj in objects], 'page': page,
            })
        if not selected:
            sections.sort(key=lambda section: section['results'][0]['rank'])
    return render(request, 'dnd/search.html', {
        'query': query, 'selected': selected, 'sections': sections,
        'categories': SOURCES, 'search_error': error,
    }, status=400 if error else 200)


def search_suggest(request):
    query = request.GET.get('q', '').strip()[:100]
    if len(query) < 2:
        return JsonResponse({'results': []})
    candidates = []
    for source in SOURCES:
        candidates.extend(_result(source, obj) for obj in _matches(source, query, names_only=True)[:3])
    candidates.sort(key=lambda result: (result['rank'], result['title'].casefold(), result['category']))
    return JsonResponse({'results': [{key: value for key, value in item.items() if key != 'rank'}
                                   for item in candidates[:8]]})
