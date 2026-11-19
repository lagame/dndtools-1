"""Ranked, accent-insensitive search over the published catalog."""

from django.core.paginator import Paginator
from django.db.models import Case, CharField, F, IntegerField, Q, Value, When
from django.db.models.functions import Cast, Collate
from django.db.models.fields.json import KeyTextTransform
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from dnd.models import (
    CharacterClassVariant, Deity, DndEdition, Domain, Feat, FeatCategory,
    Item, Language, Monster, MonsterSubtype, MonsterType, Race, RaceType,
    Rule, Rulebook, RuleCondition, Skill, Spell, SpellDescriptor, SpellSchool,
    SpellSubSchool,
    CreatureTemplate, SupplementalEntry,
    PublishedTranslation,
)
from dnd.editorial import source_digest


COLLATION = 'utf8mb4_0900_ai_ci'
SOURCES = (
    ('spells', _('Spells'), Spell, 'name', ('description',), ('rulebook__dnd_edition',)),
    ('feats', _('Feats'), Feat, 'name', ('description', 'benefit'), ('rulebook__dnd_edition',)),
    ('classes', _('Classes'), CharacterClassVariant, 'character_class__name',
     ('class_features',), ('character_class', 'rulebook__dnd_edition')),
    ('skills', _('Skills'), Skill, 'name', (), ()),
    ('races', _('Races'), Race, 'name', ('description',), ('rulebook__dnd_edition',)),
    ('monsters', _('Monsters'), Monster, 'name', ('description',), ('rulebook__dnd_edition',)),
    ('templates', _('Creature templates'), CreatureTemplate, 'name', ('description', 'mechanical_changes'),
     ('rulebook__dnd_edition',)),
    ('reference', _('Additional mechanics'), SupplementalEntry, 'name', ('description', 'mechanics'),
     ('rulebook__dnd_edition',)),
    ('items', _('Items'), Item, 'name', ('description',), ('rulebook__dnd_edition',)),
    ('rulebooks', _('Rulebooks'), Rulebook, 'name', ('description',), ('dnd_edition',)),
    ('editions', _('Editions'), DndEdition, 'name', (), ()),
    ('domains', _('Domains'), Domain, 'name', (), ()),
    ('languages', _('Languages'), Language, 'name', (), ()),
    ('deities', _('Deities'), Deity, 'name', ('description',), ()),
    ('rules', _('Rules'), Rule, 'name', ('body',), ('rulebook__dnd_edition',)),
    ('conditions', _('Conditions'), RuleCondition, 'name', ('description',), ()),
    ('schools', _('Spell schools'), SpellSchool, 'name', (), ()),
    ('subschools', _('Spell sub-schools'), SpellSubSchool, 'name', (), ()),
    ('descriptors', _('Descriptors'), SpellDescriptor, 'name', (), ()),
    ('feat_categories', _('Feat categories'), FeatCategory, 'name', (), ()),
    ('race_types', _('Race types'), RaceType, 'name', (), ()),
    ('monster_types', _('Monster types'), MonsterType, 'name', (), ()),
    ('monster_subtypes', _('Monster subtypes'), MonsterSubtype, 'name', (), ()),
)


def _translated_results(query, names_only=False):
    """Find only current approved translations; one query per matching model."""
    expression = KeyTextTransform('name', 'payload') if names_only else F('payload')
    rows = PublishedTranslation.objects.filter(locale='pt-br').alias(
        _text=Collate(Cast(expression, CharField()), COLLATION)).filter(_text__contains=query)
    grouped = {}
    for row in rows:
        grouped.setdefault(row.resource, []).append(row)
    approved = {}
    models_by_name = {source[2].__name__: source[2] for source in SOURCES}
    for resource, candidate_rows in grouped.items():
        model = models_by_name.get(resource)
        if not model:
            continue
        objects = model.objects.in_bulk([row.target_pk for row in candidate_rows])
        for row in candidate_rows:
            obj = objects.get(row.target_pk)
            if obj and source_digest(obj, translation=True) == row.source_digest:
                approved[(resource, row.target_pk)] = row.payload
    return approved


def _matches(source, query, names_only=False, translated_ids=()):
    _, _, model, name, fields, related = source
    aliases = {'_search_name': Collate(F(name), COLLATION)}
    if not names_only:
        aliases.update({f'_search_field_{index}': Collate(F(field), COLLATION)
                        for index, field in enumerate(fields)})
    matches = Q(_search_name__contains=query)
    if not names_only:
        for index in range(len(fields)):
            matches |= Q(**{f'_search_field_{index}__contains': query})
    if translated_ids:
        matches |= Q(pk__in=translated_ids)
    return (model.objects.select_related(*related).alias(**aliases).filter(matches)
            .annotate(_rank=Case(
                When(_search_name__exact=query, then=Value(0)),
                When(_search_name__startswith=query, then=Value(1)),
                When(_search_name__contains=query, then=Value(2)),
                default=Value(3), output_field=IntegerField(),
            )).order_by('_rank', name, 'pk'))


def _result(source, obj, translated=None):
    key, label = source[:2]
    if key == 'reference':
        label = dict(SupplementalEntry.KINDS).get(obj.kind, label)
    title = obj.character_class.name if key == 'classes' else obj.name
    original_title = title
    payload = (translated or {}).get((obj._meta.object_name, obj.pk))
    if payload and payload.get('name'):
        title = payload['name']
    book = getattr(obj, 'rulebook', None)
    edition = book.dnd_edition if book else getattr(obj, 'dnd_edition', None)
    return {
        'title': title, 'original_title': original_title if title != original_title else '',
        'url': obj.get_absolute_url(), 'category': label,
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
    translated = (_translated_results(query) if query and request.LANGUAGE_CODE == 'pt-br'
                  else {})
    if query and not error:
        for source in SOURCES:
            key, label = source[:2]
            if selected and selected != key:
                continue
            ids = [pk for (resource, pk) in translated if resource == source[2].__name__]
            matches = _matches(source, query, translated_ids=ids)
            count = matches.count()
            if not count and not selected:
                continue
            page = Paginator(matches, 30).get_page(request.GET.get('page')) if selected else None
            objects = page.object_list if page else matches[:8]
            sections.append({
                'key': key, 'label': label, 'count': count,
                'results': [_result(source, obj, translated) for obj in objects], 'page': page,
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
        response = JsonResponse({'results': []})
        response['Cache-Control'] = 'private, no-store'
        return response
    candidates = []
    translated = _translated_results(query, names_only=True) if request.LANGUAGE_CODE == 'pt-br' else {}
    for source in SOURCES:
        ids = [pk for (resource, pk) in translated if resource == source[2].__name__]
        candidates.extend(_result(source, obj, translated) for obj in
                          _matches(source, query, names_only=True, translated_ids=ids)[:3])
    candidates.sort(key=lambda result: (result['rank'], result['title'].casefold(), result['category']))
    response = JsonResponse({'results': [{key: value for key, value in item.items() if key != 'rank'}
                                        for item in candidates[:8]]})
    response['Cache-Control'] = 'private, no-store'
    return response
