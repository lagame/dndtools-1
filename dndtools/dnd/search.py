"""First-party catalog search with category-level pagination."""

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from dnd.models import (
    CharacterClassVariant, Deity, Domain, Feat, Item, Language, Monster,
    Race, Rule, Rulebook, RuleCondition, Skill, Spell,
)


SOURCES = (
    ('spells', 'Spells', Spell, ('name', 'description'), ('rulebook',)),
    ('feats', 'Feats', Feat, ('name', 'description', 'benefit'), ('rulebook',)),
    ('classes', 'Classes', CharacterClassVariant, ('character_class__name', 'class_features'),
     ('character_class', 'rulebook')),
    ('skills', 'Skills', Skill, ('name',), ()),
    ('races', 'Races', Race, ('name', 'description'), ('rulebook',)),
    ('monsters', 'Monsters', Monster, ('name', 'description'), ('rulebook',)),
    ('items', 'Items', Item, ('name', 'description'), ('rulebook',)),
    ('rulebooks', 'Rulebooks', Rulebook, ('name', 'description'), ('dnd_edition',)),
    ('domains', 'Domains', Domain, ('name',), ()),
    ('languages', 'Languages', Language, ('name',), ()),
    ('deities', 'Deities', Deity, ('name', 'description'), ('rulebook',)),
    ('rules', 'Rules', Rule, ('name', 'body'), ('rulebook',)),
    ('conditions', 'Conditions', RuleCondition, ('name', 'description'), ()),
)


def search(request):
    query = request.GET.get('q', '').strip()[:100]
    selected = request.GET.get('category', '')
    if selected not in {item[0] for item in SOURCES}:
        selected = ''
    sections = []
    if query:
        for key, label, model, fields, related in SOURCES:
            if selected and selected != key:
                continue
            conditions = Q()
            for field in fields:
                conditions |= Q(**{field + '__icontains': query})
            matches = model.objects.filter(conditions).select_related(*related).order_by('pk')
            count = matches.count()
            if not count and not selected:
                continue
            page = Paginator(matches, 30).get_page(request.GET.get('page')) if selected else None
            objects = page.object_list if page else matches[:8]
            results = []
            for obj in objects:
                title = obj.character_class.name if key == 'classes' else obj.name
                source = obj.rulebook.name if hasattr(obj, 'rulebook') else ''
                results.append({'title': title, 'url': obj.get_absolute_url(), 'source': source})
            sections.append({'key': key, 'label': label, 'count': count,
                             'results': results, 'page': page})
    return render(request, 'dnd/search.html', {
        'request': request, 'query': query, 'selected': selected,
        'sections': sections, 'categories': SOURCES,
    })
