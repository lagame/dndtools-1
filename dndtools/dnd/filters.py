# -*- coding: utf-8 -*-

import django_filters2
from django.db.models import Exists, F, OuterRef, Q
from django.db.models.functions import Collate
from django.utils.translation import gettext_lazy as _
from django.utils.translation import get_language
from dnd.models import (
    Spell, DndEdition, SpellSchool, SpellSubSchool, SpellDescriptor, FeatCategory,
    CharacterClass, CharacterClassVariant, Rulebook, Domain, Feat, Skill, Item, Language, Race, Monster, RaceType, ItemSlot,
    ItemProperty, PublishedTranslation, Deity, Rule, CreatureTemplate)
from dnd.filters_fields import CatalogCharFilter, FeatMultiPrerequisiteFieldFilter


def rulebook_choices(unknown_entry=True):
    rulebook_choices = [
        (edition.name,
         [(rulebook.slug, rulebook.name)
          for rulebook in edition.rulebook_set.all()])
        for edition in DndEdition.objects.all()]
    if unknown_entry:
        rulebook_choices.insert(0, ('', 'All'))

    return rulebook_choices


def edition_choices(unknown_entry=True):
    edition_choices = [(edition.slug, edition.name) for edition in
                       DndEdition.objects.all()]
    if unknown_entry:
        edition_choices.insert(0, ('', 'All'))

    return edition_choices

def race_choices(unknown_entry=True):
    race_choices = [(race.id, race.name) for race in Race.objects.all()]
    if unknown_entry:
        race_choices.insert(0, ('', 'Any'))

    return race_choices

def skill_choices(unknown_entry=True):
    skill_choices = [(skill.id, skill.name) for skill in Skill.objects.all()]
    if unknown_entry:
        skill_choices.insert(0, ('', 'Any'))
    
    return skill_choices
    
def feat_choices(unknown_entry=True):
    feat_choices = [(feat.id, feat.name) for feat in Feat.objects.all()]
    if unknown_entry:
        feat_choices.insert(0, ('', 'Any'))
    
    return feat_choices


def spell_level_choices():
    spell_level_choices = [(i, i) for i in range(0, 10)]

    return spell_level_choices


def character_class_choices():
    character_class_choices = [
        (clazz.slug, clazz.name) for clazz in CharacterClass.objects.all()
    ]
    character_class_choices.insert(0, ('', 'All'))

    return character_class_choices


def character_class_casting_choices():
    character_class_choices = [
        (clazz.slug, clazz.name) for clazz in
        CharacterClass.objects.filter(spellclasslevel__id__isnull=False).distinct()
    ]
    character_class_choices.insert(0, ('', 'All'))

    return character_class_choices


def domain_choices():
    domain_choices = [
        (domain.slug, domain.name) for domain in Domain.objects.all()
    ]
    domain_choices.insert(0, ('', 'All'))

    return domain_choices


def school_choices():
    return [('', 'All')] + [(school.slug, school.name) for school in SpellSchool.objects.all()]


def sub_school_choices():
    return [('', 'All')] + [(school.slug, school.name) for school in SpellSubSchool.objects.all()]


def descriptor_choices():
    return [('', 'All')] + [(descriptor.slug, descriptor.name) for descriptor in SpellDescriptor.objects.all()]


def _localized_item_choices(objects):
    objects = list(objects)
    if get_language() != 'pt-br':
        return [(obj.slug, obj.name) for obj in objects]
    from dnd.editorial import source_digest

    translations = {row.target_pk: row for row in PublishedTranslation.objects.filter(
        resource=objects[0]._meta.object_name, locale='pt-br',
        target_pk__in=[obj.pk for obj in objects])} if objects else {}
    return [(obj.slug, translations[obj.pk].payload['name']
             if obj.pk in translations and
             translations[obj.pk].source_digest == source_digest(obj, translation=True)
             else obj.name) for obj in objects]


def item_slot_choices():
    return [('', _('All'))] + _localized_item_choices(ItemSlot.objects.all())


def property_choices():
    return _localized_item_choices(ItemProperty.objects.all())


class ItemNameFilter(CatalogCharFilter):
    def filter(self, qs, value):
        if not value or get_language() != 'pt-br':
            return super().filter(qs, value)
        from dnd.search import COLLATION, _translated_results

        translated_ids = [pk for (resource, pk) in _translated_results(value, names_only=True)
                          if resource == 'Item']
        alias = f'_catalog_ci_{self.creation_counter}'
        return qs.alias(**{alias: Collate(F(self.name), COLLATION)}).filter(
            Q(**{f'{alias}__contains': value}) | Q(pk__in=translated_ids))


def feat_category_choices():
    return [(category.slug, category.name) for category in FeatCategory.objects.all()]


class SpellFilter(django_filters2.FilterSet):
    name = CatalogCharFilter(
        lookup_type='icontains', label=_('Spell name')
    )
    # noinspection PyShadowingBuiltins
    range = CatalogCharFilter(
        lookup_type='icontains',
    )
    casting_time = CatalogCharFilter(
        lookup_type='icontains',
    )
    spell_resistance = CatalogCharFilter(
        lookup_type='icontains',
    )
    area = CatalogCharFilter(
        lookup_type='icontains'
    )
    duration = CatalogCharFilter(
        lookup_type='icontains'
    )
    saving_throw = CatalogCharFilter(
        lookup_type='icontains'
    )

    school__slug = django_filters2.ChoiceFilter(
        choices=school_choices, label=_('School')
    )
    sub_school__slug = django_filters2.ChoiceFilter(
        choices=sub_school_choices, label=_('Sub-school')
    )
    descriptors__slug = django_filters2.ChoiceFilter(
        choices=descriptor_choices, label=_('Descriptor')
    )
    verbal_component = django_filters2.BooleanFilter()
    somatic_component = django_filters2.BooleanFilter()
    material_component = django_filters2.BooleanFilter()
    arcane_focus_component = django_filters2.BooleanFilter()
    divine_focus_component = django_filters2.BooleanFilter()
    xp_component = django_filters2.BooleanFilter()

    rulebook__dnd_edition__slug = django_filters2.MultipleChoiceFilter(
        choices=lambda: edition_choices(unknown_entry=False),
        label=_('Edition'),
    )
    rulebook__slug = django_filters2.ChoiceFilter(
        label=_('Rulebook'), choices=rulebook_choices
    )
    description = CatalogCharFilter(
        lookup_type='icontains',
    )
    class_levels__slug = django_filters2.ChoiceFilter(
        choices=character_class_casting_choices,
        help_text='Shows only classes with own spell lists',
        label=_('Class'),
        grouped=True,
    )
    spellclasslevel__level = django_filters2.MultipleChoiceFilter(
        choices=spell_level_choices(),
        label=_('Level for class'),
        help_text='Use ctrl to select more levels!',
        grouped=True,
    )
    domain_levels__slug = django_filters2.ChoiceFilter(
        choices=domain_choices,
        label=_('Domain'),
        grouped=True,
    )
    spelldomainlevel__level = django_filters2.MultipleChoiceFilter(
        choices=spell_level_choices(),
        label=_('Level for domain'),
        help_text='Use ctrl to select more levels!',
        grouped=True,
    )

    class Meta:
        model = Spell
        fields = [
            'name', 'range', 'spell_resistance', 'area', 'duration', 'saving_throw', 'casting_time',
            'school__slug', 'sub_school__slug', 'descriptors__slug',
            'verbal_component', 'somatic_component', 'material_component',
            'arcane_focus_component', 'divine_focus_component',
            'xp_component', 'rulebook__slug', 'rulebook__dnd_edition__slug', 'description',
            'class_levels__slug', 'spellclasslevel__level',
            'domain_levels__slug', 'spelldomainlevel__level', ]


class SpellFilterAdmin(SpellFilter):
    verified = django_filters2.BooleanFilter(
    )

    class Meta:
        model = SpellFilter.Meta.model
        fields = ['verified', ] + SpellFilter.Meta.fields


class ItemFilter(django_filters2.FilterSet):
    type_choices = [('', _('All'))] + [(code, _(label)) for code, label in Item.ITEM_TYPE]

    name = ItemNameFilter(
        lookup_type='icontains', label=_('Item name')
    )
    rulebook__dnd_edition__slug = django_filters2.MultipleChoiceFilter(
        choices=lambda: edition_choices(unknown_entry=False),
        label=_('Edition'),
    )
    rulebook__slug = django_filters2.ChoiceFilter(
        label=_('Rulebook'), choices=rulebook_choices
    )
    type = django_filters2.ChoiceFilter(
        label=_('Item Type'), choices=type_choices
    )
    body_slot__slug = django_filters2.ChoiceFilter(
        label=_('Body Slot'), choices=item_slot_choices
    )
    price_bonus = django_filters2.NumberFilter(
        label=_('Price bonus')
    )
    price_gp = django_filters2.RangeFilter(
        label=_('Price in GP (range)'),
    )
    property__slug = django_filters2.MultipleChoiceFilter(
        label=_('Property'), choices=property_choices
    )

    class Meta:
        model = Item
        fields = ['name', 'rulebook__dnd_edition__slug', 'rulebook__slug',

                  'price_bonus', 'price_gp',
                  'type', 'body_slot__slug', 'property__slug']


class LanguageFilter(django_filters2.FilterSet):
    name = CatalogCharFilter(
        lookup_type='icontains', label=_('Language name')
    )

    class Meta:
        model = Language
        fields = ['name', ]


class CharacterClassFilter(django_filters2.FilterSet):
    character_class__name = CatalogCharFilter(
        lookup_type='icontains', label=_('Class name')
    )
    character_class__prestige = django_filters2.BooleanFilter()
    rulebook__slug = django_filters2.ChoiceFilter(
        label=_('Rulebook'), choices=rulebook_choices
    )
    rulebook__dnd_edition__slug = django_filters2.MultipleChoiceFilter(
        choices=lambda: edition_choices(unknown_entry=False),
        label=_('Edition'),
    )
    required_bab = django_filters2.RangeFilter(
        label=_('Required Base Attack (range)'),
    )
    skill_points = django_filters2.RangeFilter(
        label=_('Skill points/level (range)'),
    )
    class_features = CatalogCharFilter(
        label=_('Class feature'),
        lookup_type='icontains',
    )
    hit_die = django_filters2.RangeFilter(
        label=_('Hit die (range)'),
    )
    required_races__race = django_filters2.ChoiceFilter(
        label=_('Race'), choices=race_choices
    )
    required_skills__skill = django_filters2.MultipleChoiceFilter(
        label=_('Skills'), choices=skill_choices
    )
    required_feats__feat = django_filters2.MultipleChoiceFilter(
        label=_('Feats'), choices=feat_choices
    )
    requirements = CatalogCharFilter(
        label=_('Requirement'), lookup_type='icontains',
    )

    class Meta:
        model = CharacterClassVariant
        fields = ['character_class__name', 'rulebook__slug', 'rulebook__dnd_edition__slug',
                  'character_class__prestige',
                  'required_bab', 'skill_points',
                  'class_features', 'hit_die', 'required_races__race', 'required_skills__skill', 'required_feats__feat', 'requirements',]


def rulebook_year_choices():
    years = set(Rulebook.objects.exclude(year__isnull=True).values_list('year', flat=True))
    years.update(str(value.year) for value in Rulebook.objects.exclude(
        published__isnull=True).values_list('published', flat=True))
    return [('', _('All'))] + [(year, year) for year in sorted(
        (year for year in years if year.isdigit() and len(year) == 4), reverse=True)]


RULEBOOK_CONTENT = {
    'spells': Spell,
    'feats': Feat,
    'classes': CharacterClassVariant,
    'items': Item,
    'races': Race,
    'monsters': Monster,
    'templates': CreatureTemplate,
}


def rulebook_year_filter(qs, year):
    if year:
        return qs.filter(Q(year=year) | (
            (Q(year__isnull=True) | Q(year='')) & Q(published__year=year)))
    return qs


def rulebook_content_filter(qs, content):
    if content:
        model = RULEBOOK_CONTENT[content]
        return qs.alias(_has_catalog_entries=Exists(
            model.objects.filter(rulebook_id=OuterRef('pk')))).filter(
                _has_catalog_entries=True)
    return qs


class RulebookFilter(django_filters2.FilterSet):
    name = CatalogCharFilter(
        lookup_type='icontains', label=_('Title contains')
    )
    description = CatalogCharFilter(
        lookup_type='icontains', label=_('Description contains')
    )
    dnd_edition__slug = django_filters2.ChoiceFilter(
        label=_('Edition'), choices=edition_choices
    )
    publication_type = django_filters2.ChoiceFilter(
        label=_('Type of book'), choices=Rulebook.PUBLICATION_TYPES,
    )
    publication_year = django_filters2.ChoiceFilter(
        label=_('Publication year'), choices=rulebook_year_choices,
        action=rulebook_year_filter,
    )
    content = django_filters2.ChoiceFilter(
        label=_('Includes'), choices=[
            ('', _('All content')),
            ('spells', _('Spells')), ('feats', _('Feats')),
            ('classes', _('Classes')), ('items', _('Items')),
            ('races', _('Races')), ('monsters', _('Monsters')),
            ('templates', _('Creature templates')),
        ], action=rulebook_content_filter,
    )

    class Meta:
        model = Rulebook
        fields = ['name', 'description', 'dnd_edition__slug', 'publication_type',
                  'publication_year', 'content']


class FeatFilter(django_filters2.FilterSet):
    name = CatalogCharFilter(
        lookup_type='icontains', label=_('Feat name')
    )
    feat_categories__slug = django_filters2.MultipleChoiceFilter(
        choices=feat_category_choices,
        label=_('Feat category')
    )
    rulebook__slug = django_filters2.MultipleChoiceFilter(
        choices=lambda: rulebook_choices(unknown_entry=False),
        label=_('Rulebook'),
    )
    rulebook__dnd_edition__slug = django_filters2.MultipleChoiceFilter(
        choices=lambda: edition_choices(unknown_entry=False),
        label=_('Edition'),
    )
    description = CatalogCharFilter(
        lookup_type='icontains',
    )
    benefit = CatalogCharFilter(
        lookup_type='icontains',
    )
    special = CatalogCharFilter(
        lookup_type='icontains',
    )
    normal = CatalogCharFilter(
        lookup_type='icontains',
    )
    prerequisite = FeatMultiPrerequisiteFieldFilter(
        label=_('Prerequisites'),
    )

    class Meta:
        model = Feat
        fields = ['name', 'feat_categories__slug', 'rulebook__slug', 'rulebook__dnd_edition__slug', 'description',
                  'benefit', 'special',
                  'normal', ]


class SpellDomainFilter(django_filters2.FilterSet):
    name = CatalogCharFilter(
        lookup_type='icontains', label=_('Domain name')
    )

    class Meta:
        model = Domain
        fields = ['name', ]


class SpellDescriptorFilter(django_filters2.FilterSet):
    name = CatalogCharFilter(
        lookup_type='icontains', label=_('Descriptor name')
    )

    class Meta:
        model = SpellDescriptor
        fields = ['name', ]


class SkillFilter(django_filters2.FilterSet):
    name = CatalogCharFilter(
        lookup_type='icontains'
    )
    trained_only = django_filters2.BooleanFilter()
    armor_check_penalty = django_filters2.BooleanFilter()
    base_skill = django_filters2.ChoiceFilter(
        choices=(
            ('', 'All'),
            ('STR', 'STR'),
            ('CON', 'CON'),
            ('DEX', 'DEX'),
            ('INT', 'INT'),
            ('WIS', 'WIS'),
            ('CHA', 'CHA'),
            ('None', 'None'),
        )
    )

    class Meta:
        model = Skill
        fields = ['name', 'trained_only', 'armor_check_penalty', 'base_skill']


class RuleFilter(django_filters2.FilterSet):
    name = CatalogCharFilter(
        lookup_type='icontains'
    )

    class Meta:
        model = Rule
        fields = ['name', ]


class DeityFilter(django_filters2.FilterSet):
    name = CatalogCharFilter(
        lookup_type='icontains'
    )

    class Meta:
        model = Deity
        fields = ['name']


class MonsterFilter(django_filters2.FilterSet):
    name = CatalogCharFilter(
        lookup_type='icontains', label=_('Monster name')
    )
    rulebook__slug = django_filters2.ChoiceFilter(
        label=_('Rulebook'), choices=rulebook_choices
    )
    rulebook__dnd_edition__slug = django_filters2.MultipleChoiceFilter(
        choices=lambda: edition_choices(unknown_entry=False),
        label=_('Edition'),
    )

    class Meta:
        model = Monster
        fields = [
            'name', 'rulebook__slug', 'rulebook__dnd_edition__slug', ]


class RaceFilter(django_filters2.FilterSet):
    name = CatalogCharFilter(
        lookup_type='icontains', label=_('Race name')
    )
    rulebook__slug = django_filters2.ChoiceFilter(
        label=_('Rulebook'), choices=rulebook_choices
    )
    rulebook__dnd_edition__slug = django_filters2.MultipleChoiceFilter(
        choices=lambda: edition_choices(unknown_entry=False),
        label=_('Edition'),
    )

    class Meta:
        model = Race
        fields = [
            'name', 'rulebook__slug', 'rulebook__dnd_edition__slug', ]


class RaceTypeFilter(django_filters2.FilterSet):
    save_type_choices = [raceTypePair for raceTypePair in RaceType.BASE_SAVE_TYPE_CHOICES]
    save_type_choices.insert(0, ('', 'All'))

    base_attack_type_choices = [raceTypePair for raceTypePair in RaceType.BASE_ATTACK_TYPE_CHOICES]
    base_attack_type_choices.insert(0, ('', 'All'))

    name = CatalogCharFilter(
        lookup_type='icontains', label=_('Race type name')
    )
    hit_die_size = django_filters2.RangeFilter(
        label=_('Hit Die Size'),
        help_text='(range from-to)',
    )
    base_attack_type = django_filters2.ChoiceFilter(
        label=_('Base Attack Type'), choices=base_attack_type_choices
    )
    base_fort_save_type = django_filters2.ChoiceFilter(
        label=_('Fort Save Type'), choices=save_type_choices
    )
    base_reflex_save_type = django_filters2.ChoiceFilter(
        label=_('Reflex Save Type'), choices=save_type_choices
    )
    base_will_save_type = django_filters2.ChoiceFilter(
        label=_('Will Save Type'), choices=save_type_choices
    )

    class Meta:
        model = RaceType
        fields = ['name', 'hit_die_size', 'base_fort_save_type', 'base_reflex_save_type', 'base_will_save_type']
