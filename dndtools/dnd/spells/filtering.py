"""Spell filters whose class and level constraints share one catalog link."""

from django import forms
from django.utils.translation import gettext_lazy as _
from django.db.models import Exists, F, OuterRef, Q, Subquery
from django.db.models.functions import Collate, Coalesce

from dnd.models import (
    CharacterClass, DndEdition, Domain, Rulebook, SpellClassLevel,
    SpellDescriptor, SpellDomainLevel, SpellSchool, SpellSubSchool,
)
from dnd.search import COLLATION


MISSING = '__missing__'
LEVELS = [(str(level), str(level)) for level in range(10)]
YES_NO = (('', _('All')), ('true', _('Yes')), ('false', _('No')))


class SpellCatalogForm(forms.Form):
    name = forms.CharField(label=_('Spell name'), max_length=100, required=False)
    class_levels__slug = forms.ChoiceField(label=_('Class'), required=False)
    spellclasslevel__level = forms.MultipleChoiceField(
        label=_('Class level'), required=False, choices=[(MISSING, _('Not specified'))] + LEVELS,
        widget=forms.CheckboxSelectMultiple)
    school__slug = forms.ChoiceField(label=_('School'), required=False)
    sub_school__slug = forms.ChoiceField(label=_('Sub-school'), required=False)
    descriptors__slug = forms.MultipleChoiceField(
        label=_('Descriptors'), required=False, widget=forms.CheckboxSelectMultiple)
    casting_time = forms.CharField(label=_('Casting time contains'), max_length=100, required=False)
    casting_time_missing = forms.BooleanField(label=_('Casting time not specified'), required=False)
    rulebook__slug = forms.ChoiceField(label=_('Rulebook'), required=False)
    rulebook__dnd_edition__slug = forms.MultipleChoiceField(
        label=_('Edition / setting'), required=False, widget=forms.CheckboxSelectMultiple)
    edition_system = forms.ChoiceField(label=_('Ruleset'), required=False)
    publication_type = forms.ChoiceField(label=_('Publication type'), required=False,
                                          choices=(('', _('All')), ('core', _('Core')), ('other', _('Other'))))
    domain_levels__slug = forms.ChoiceField(label=_('Domain'), required=False)
    spelldomainlevel__level = forms.MultipleChoiceField(
        label=_('Domain level'), required=False, choices=[(MISSING, _('Not specified'))] + LEVELS,
        widget=forms.CheckboxSelectMultiple)
    range = forms.CharField(label=_('Range contains'), max_length=100, required=False)
    duration = forms.CharField(label=_('Duration contains'), max_length=100, required=False)
    description = forms.CharField(label=_('Description contains'), max_length=100, required=False)
    verbal_component = forms.ChoiceField(label=_('Verbal'), required=False, choices=YES_NO)
    somatic_component = forms.ChoiceField(label=_('Somatic'), required=False, choices=YES_NO)
    material_component = forms.ChoiceField(label=_('Material'), required=False, choices=YES_NO)
    arcane_focus_component = forms.ChoiceField(label=_('Arcane focus'), required=False, choices=YES_NO)
    divine_focus_component = forms.ChoiceField(label=_('Divine focus'), required=False, choices=YES_NO)
    xp_component = forms.ChoiceField(label=_('XP'), required=False, choices=YES_NO)
    sort = forms.ChoiceField(label=_('Sort by'), required=False, choices=(
        ('', _('Name A–Z')), ('-name', _('Name Z–A')), ('book', _('Rulebook')),
        ('school', _('School')), ('level', _('Class level')),
    ))

    def __init__(self, *args, is_staff=False, **kwargs):
        if args and args[0] is not None:
            data = args[0].copy()
            for field in ('verbal_component', 'somatic_component', 'material_component',
                          'arcane_focus_component', 'divine_focus_component', 'xp_component',
                          'verified'):
                value = data.get(field)
                if value in ('True', 'False'):
                    data[field] = value.lower()
            args = (data, *args[1:])
        super().__init__(*args, **kwargs)
        self.fields['class_levels__slug'].choices = [('', _('All')), (MISSING, _('Not specified'))] + [
            (item.slug, item.name) for item in CharacterClass.objects.order_by('name')
        ]
        self.fields['school__slug'].choices = [('', _('All'))] + [
            (item.slug, item.name) for item in SpellSchool.objects.order_by('name')
        ]
        self.fields['sub_school__slug'].choices = [('', _('All')), (MISSING, _('Not specified'))] + [
            (item.slug, item.name) for item in SpellSubSchool.objects.order_by('name')
        ]
        self.fields['descriptors__slug'].choices = [(MISSING, _('Not specified'))] + [
            (item.slug, item.name) for item in SpellDescriptor.objects.order_by('name')
        ]
        self.fields['domain_levels__slug'].choices = [('', _('All')), (MISSING, _('Not specified'))] + [
            (item.slug, item.name) for item in Domain.objects.order_by('name')
        ]
        editions = list(DndEdition.objects.order_by('name'))
        self.fields['rulebook__dnd_edition__slug'].choices = [
            (item.slug, item.name) for item in editions
        ]
        self.fields['edition_system'].choices = [('', _('All'))] + [
            (system, system.replace('DnD ', 'D&D ')) for system in sorted({item.system for item in editions})
        ]
        self.fields['rulebook__slug'].choices = [('', _('All'))] + [
            (item.slug, item.name) for item in Rulebook.objects.order_by('name')
        ]
        if is_staff:
            self.fields['verified'] = forms.ChoiceField(label=_('Verified'), required=False, choices=YES_NO)

    def clean(self):
        data = super().clean()
        for relation, level in (('class_levels__slug', 'spellclasslevel__level'),
                                ('domain_levels__slug', 'spelldomainlevel__level')):
            if data.get(relation) == MISSING and any(value != MISSING for value in data.get(level, [])):
                self.add_error(level, 'Select a class or domain before choosing a numeric level.')
        if data.get('casting_time') and data.get('casting_time_missing'):
            self.add_error('casting_time_missing', 'Choose a casting time or Not specified, not both.')
        return data


def _linked_levels(queryset, model, relation, levels, prefix):
    links = model.objects.filter(spell_id=OuterRef('pk'))
    if relation and relation != MISSING:
        links = links.filter(**{prefix + '__slug': relation})
    if relation == MISSING:
        return queryset.annotate(**{prefix + '_present': Exists(links)}).filter(
            **{prefix + '_present': False})
    if not relation and not levels:
        return queryset
    numbers = [int(value) for value in levels if value != MISSING]
    matching = links.filter(level__in=numbers) if numbers else links
    queryset = queryset.annotate(**{prefix + '_match': Exists(matching)})
    if MISSING in levels:
        queryset = queryset.annotate(**{prefix + '_present': Exists(links)})
        return queryset.filter(Q(**{prefix + '_match': True}) | Q(**{prefix + '_present': False}))
    return queryset.filter(**{prefix + '_match': True})


def filter_spells(queryset, data):
    for field in ('name', 'casting_time', 'range', 'duration', 'description'):
        if data.get(field):
            queryset = queryset.alias(**{f'_filter_{field}': Collate(F(field), COLLATION)}).filter(
                **{f'_filter_{field}__contains': data[field]})
    if data.get('casting_time_missing'):
        queryset = queryset.filter(Q(casting_time__isnull=True) | Q(casting_time=''))
    if data.get('school__slug'):
        queryset = queryset.filter(school__slug=data['school__slug'])
    if data.get('sub_school__slug'):
        value = data['sub_school__slug']
        queryset = queryset.filter(sub_school__isnull=True) if value == MISSING else queryset.filter(sub_school__slug=value)
    descriptors = data.get('descriptors__slug', [])
    if descriptors:
        selected = [value for value in descriptors if value != MISSING]
        descriptor_match = Q(descriptors__slug__in=selected) if selected else Q()
        if MISSING in descriptors:
            descriptor_match |= Q(descriptors__isnull=True)
        queryset = queryset.filter(descriptor_match).distinct()
    if data.get('rulebook__slug'):
        queryset = queryset.filter(rulebook__slug=data['rulebook__slug'])
    if data.get('rulebook__dnd_edition__slug'):
        queryset = queryset.filter(rulebook__dnd_edition__slug__in=data['rulebook__dnd_edition__slug'])
    if data.get('edition_system'):
        queryset = queryset.filter(rulebook__dnd_edition__system=data['edition_system'])
    if data.get('publication_type'):
        queryset = queryset.filter(rulebook__dnd_edition__core=data['publication_type'] == 'core')
    queryset = _linked_levels(queryset, SpellClassLevel, data.get('class_levels__slug'),
                              data.get('spellclasslevel__level', []), 'character_class')
    queryset = _linked_levels(queryset, SpellDomainLevel, data.get('domain_levels__slug'),
                              data.get('spelldomainlevel__level', []), 'domain')
    for field in ('verbal_component', 'somatic_component', 'material_component',
                  'arcane_focus_component', 'divine_focus_component', 'xp_component', 'verified'):
        if data.get(field):
            queryset = queryset.filter(**{field: data[field] == 'true'})
    sort = data.get('sort')
    if sort == '-name':
        return queryset.order_by('-name', 'pk')
    if sort == 'book':
        return queryset.order_by('rulebook__name', 'name', 'pk')
    if sort == 'school':
        return queryset.order_by('school__name', 'name', 'pk')
    if sort == 'level':
        levels = SpellClassLevel.objects.filter(spell_id=OuterRef('pk'))
        if data.get('class_levels__slug') not in ('', None, MISSING):
            levels = levels.filter(character_class__slug=data['class_levels__slug'])
        return queryset.annotate(_sort_level=Coalesce(Subquery(
            levels.order_by('level').values('level')[:1]), 99)).order_by('_sort_level', 'name', 'pk')
    return queryset.order_by('name', 'pk')
