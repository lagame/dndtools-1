"""Whitelisted ordering for public catalog lists, applied before pagination."""

from django.db.models import Case, CharField, F, IntegerField, Q, Value, When
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Collate, Concat, NullIf

from dnd.editorial import source_digest
from dnd.models import PublishedTranslation


# Keys are the visible data columns, never arbitrary request-supplied ORM paths.
SORT_COLUMNS = {
    'Item': {'name': 'name', 'level': 'item_level', 'cost': 'cost',
             'slot': 'slot', 'book': 'rulebook__name',
             'edition': 'rulebook__dnd_edition__name'},
    'Spell': {'name': 'name', 'school': 'school__name', 'book': 'rulebook__abbr',
              'effect': 'effect', 'duration': 'duration', 'range': 'range',
              'components': 'components', 'casting': 'casting_time'},
    'Feat': {'name': 'name', 'description': 'description', 'book': 'rulebook__name'},
    'Monster': {'name': 'name', 'book': 'rulebook__name',
                'edition': 'rulebook__dnd_edition__name'},
    'Race': {'name': 'name', 'book': 'rulebook__name',
             'edition': 'rulebook__dnd_edition__name'},
    'CharacterClassVariant': {'name': 'character_class__name',
                              'prestige': 'character_class__prestige',
                              'book': 'rulebook__name'},
    'CharacterClass': {'name': 'name', 'prestige': 'prestige'},
    'Skill': {'name': 'name', 'ability': 'base_skill',
              'trained': 'trained_only', 'armor': 'armor_check_penalty'},
    'Rulebook': {'name': 'name', 'edition': 'dnd_edition__name'},
    'DndEdition': {'name': 'name'},
    'FeatCategory': {'name': 'name'},
    'Language': {'name': 'name'},
    'Deity': {'name': 'name'},
    'Rule': {'name': 'name'},
    'RaceType': {'name': 'name', 'hit_die': 'hit_die_size',
                 'attack': 'base_attack_type', 'fort': 'base_fort_save_type',
                 'reflex': 'base_reflex_save_type', 'will': 'base_will_save_type'},
    'SpellDescriptor': {'name': 'name'},
    'Domain': {'name': 'name'},
    'CreatureTemplate': {'name': 'name', 'book': 'rulebook__name', 'type': 'kind'},
    'SupplementalEntry': {'name': 'name', 'details': 'category', 'book': 'rulebook__name'},
}


def _approved_names(model):
    rows = PublishedTranslation.objects.filter(resource=model.__name__, locale='pt-br')
    objects = model.objects.in_bulk([row.target_pk for row in rows])
    return {row.target_pk: row.payload['name'] for row in rows
            if row.target_pk in objects and 'name' in row.payload
            and row.source_digest == source_digest(objects[row.target_pk], translation=True)}


def _display_name(queryset, path):
    parts = path.split('__')
    model = queryset.model
    for part in parts[:-1]:
        model = model._meta.get_field(part).related_model
    names = _approved_names(model)
    pk_path = '__'.join(parts[:-1] + ['pk']) if len(parts) > 1 else 'pk'
    return Case(*(When(**{pk_path: pk}, then=Value(value)) for pk, value in names.items()),
                default=F(path), output_field=CharField())


def order_catalog(queryset, request):
    key = request.GET.get('order', '')
    descending = key.startswith('-')
    column = key.lstrip('-')
    path = SORT_COLUMNS.get(queryset.model.__name__, {}).get(column)
    if not path:
        return queryset, ''
    if path == 'cost':
        queryset = queryset.alias(
            _cost_group=Case(When(price_gp__isnull=False, then=Value(0)),
                             When(price_bonus__isnull=False, then=Value(1)),
                             default=Value(2), output_field=IntegerField()),
            _cost_value=Case(When(price_gp__isnull=False, then=F('price_gp')),
                             When(price_bonus__isnull=False, then=F('price_bonus')),
                             default=Value(0), output_field=IntegerField()))
        return queryset.order_by('_cost_group', '-_cost_value' if descending else '_cost_value', 'pk'), key
    if path == 'slot':
        slot = (_display_name(queryset, 'body_slot__name') if getattr(request, 'LANGUAGE_CODE', '') == 'pt-br'
                else F('body_slot__name'))
        prop = (_display_name(queryset, 'property__name') if getattr(request, 'LANGUAGE_CODE', '') == 'pt-br'
                else F('property__name'))
        expression = Case(
            When(body_slot__isnull=False, property__isnull=False,
                 then=Concat(slot, Value('/'), prop)),
            When(body_slot__isnull=False, then=slot),
            When(property__isnull=False, then=prop),
            default=Value(None), output_field=CharField())
    elif path == 'components':
        expression = NullIf(Case(
            When(corrupt_component=True, then=Concat(Value('Corrupt, '), F('extra_components'))),
            default=F('extra_components'), output_field=CharField()), Value(''))
    else:
        expression = (_display_name(queryset, path) if path.endswith('name')
                      and getattr(request, 'LANGUAGE_CODE', '') == 'pt-br' else F(path))
    queryset = queryset.alias(_display_sort=expression)
    return queryset.order_by(F('_display_sort').desc(nulls_last=True) if descending
                             else F('_display_sort').asc(nulls_last=True), 'pk'), key


def search_book_names(queryset, request, name_path='name'):
    """Search only names in the already book-scoped queryset."""
    query = request.GET.get('q', '').strip()[:100]
    if not query:
        return queryset
    translated_ids = []
    if getattr(request, 'LANGUAGE_CODE', '') == 'pt-br':
        model = queryset.model if name_path == 'name' else queryset.model._meta.get_field(
            name_path.split('__')[0]).related_model
        candidates = PublishedTranslation.objects.filter(resource=model.__name__, locale='pt-br').alias(
            _translated_name=Collate(Cast(KeyTextTransform('name', 'payload'), CharField()),
                                     'utf8mb4_0900_ai_ci')).filter(_translated_name__contains=query)
        objects = model.objects.in_bulk([row.target_pk for row in candidates])
        translated_ids = [row.target_pk for row in candidates
                          if row.target_pk in objects and
                          row.source_digest == source_digest(objects[row.target_pk], translation=True)]
        if name_path != 'name':
            return queryset.alias(_book_search=Collate(F(name_path), 'utf8mb4_0900_ai_ci')).filter(
                Q(_book_search__contains=query) |
                Q(**{name_path.split('__')[0] + '_id__in': translated_ids}))
    return queryset.alias(_book_search=Collate(F(name_path), 'utf8mb4_0900_ai_ci')).filter(
        Q(_book_search__contains=query) | Q(pk__in=translated_ids))
