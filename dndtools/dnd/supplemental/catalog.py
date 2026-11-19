"""Typed catalog details; SupplementalEntry remains the stable public identity."""

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from dnd.models import (AuraDetail, InvocationDetail, ManeuverDetail,
                        MonstrousTraitDetail, MysteryDetail, PsionicPowerDetail)


DETAILS = {
    'mysteries': ('mystery_detail', MysteryDetail),
    'invocations': ('invocation_detail', InvocationDetail),
    'psionics': ('psionic_detail', PsionicPowerDetail),
    'auras': ('aura_detail', AuraDetail),
    'maneuvers': ('maneuver_detail', ManeuverDetail),
    'monstrous-traits': ('trait_detail', MonstrousTraitDetail),
}

DISPLAY = {
    'mysteries': (('path', _('Path')), ('grade', _('Grade')),
                  ('mystery_level', _('Mystery level')), ('casting_time', _('Casting time')),
                  ('range', _('Range')), ('duration', _('Duration')),
                  ('saving_throw', _('Saving throw')), ('spell_resistance', _('Spell resistance'))),
    'invocations': (('grade', _('Grade')), ('invocation_type', _('Invocation type')),
                    ('equivalent_level', _('Equivalent spell level')),
                    ('character_class', _('Class')), ('activation', _('Activation')),
                    ('range', _('Range')), ('duration', _('Duration'))),
    'psionics': (('discipline', _('Discipline')), ('class_levels', _('Class levels')),
                 ('power_points', _('Power points')), ('manifestation_time', _('Manifestation time')),
                 ('range', _('Range')), ('duration', _('Duration')),
                 ('saving_throw', _('Saving throw')), ('power_resistance', _('Power resistance')),
                 ('augment', _('Augment'))),
    'auras': (('character_class', _('Class')), ('monster', _('Monster')),
              ('radius', _('Radius')), ('activation', _('Activation')),
              ('targets', _('Targets')), ('duration', _('Duration'))),
    'maneuvers': (('discipline', _('Discipline')), ('maneuver_level', _('Maneuver level')),
                  ('maneuver_type', _('Maneuver type')), ('initiation_action', _('Initiation action')),
                  ('range', _('Range')), ('target', _('Target')), ('duration', _('Duration'))),
    'monstrous-traits': (('ability_type', _('Ability type')), ('role', _('Role')),
                         ('monsters', _('Monsters')), ('activation', _('Activation')),
                         ('uses', _('Uses')), ('save_dc', _('Save DC'))),
}

FACETS = {
    'mysteries': ('grade', 'mystery_level'),
    'invocations': ('grade', 'invocation_type', 'character_class'),
    'psionics': ('discipline', 'power_points', 'class_levels'),
    'auras': ('character_class', 'monster'),
    'maneuvers': ('discipline', 'maneuver_level', 'maneuver_type'),
    'monstrous-traits': ('ability_type', 'role', 'monsters'),
}


def detail_for(entry):
    relation = DETAILS.get(entry.kind)
    if relation is None:
        return None
    try:
        return getattr(entry, relation[0])
    except ObjectDoesNotExist:
        return None


def displayed_details(entry):
    detail = detail_for(entry)
    if detail is None:
        return []
    values = []
    for name, label in DISPLAY[entry.kind]:
        if name == 'class_levels':
            value = ', '.join('%s %s' % (row.character_class.name, row.level)
                              for row in detail.class_levels.all())
        elif name == 'monsters':
            value = ', '.join(monster.name for monster in detail.monsters.all())
        else:
            value = getattr(detail, 'get_%s_display' % name)() if detail._meta.get_field(name).choices else getattr(detail, name)
        if value:
            values.append((label, value))
    return values
