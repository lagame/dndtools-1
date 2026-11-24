"""Editorial forms for each source-backed 3.5 mechanics family."""

from django import forms
from django.forms import modelform_factory
from django.utils.translation import gettext_lazy as _

from dnd.models import CharacterClass, SupplementalEntry
from dnd.supplemental.catalog import DETAILS, DISPLAY, detail_for


COMMON_FIELDS = ('kind', 'rulebook', 'page', 'name', 'mechanics', 'description')
REQUIRED_DETAILS = {
    'mysteries': ('path', 'grade', 'mystery_level'),
    'invocations': ('grade', 'invocation_type', 'equivalent_level'),
    'psionics': ('discipline', 'power_points', 'class_levels'),
    'auras': ('radius',),
    'maneuvers': ('discipline', 'maneuver_level', 'maneuver_type'),
    'monstrous-traits': ('ability_type', 'role', 'monsters'),
}


def parse_class_levels(value):
    """Validate a human-readable class/level list before storing relational rows."""
    result = []
    seen = set()
    for line in value.splitlines():
        if not line.strip():
            continue
        name, separator, level_text = line.partition('|')
        if not separator:
            raise forms.ValidationError(_('Use one class per line: Class name | Level.'))
        try:
            level = int(level_text.strip())
        except ValueError as error:
            raise forms.ValidationError(_('Use one class per line: Class name | Level.')) from error
        matches = list(CharacterClass.objects.filter(name__iexact=name.strip())[:2])
        if len(matches) != 1 or not 0 <= level <= 9 or matches[0].pk in seen:
            raise forms.ValidationError(_('Choose an existing class and a unique level from 0 to 9.'))
        seen.add(matches[0].pk)
        result.append((matches[0], level))
    if len(result) > 20:
        raise forms.ValidationError(_('Too many class levels.'))
    return result


def typed_form(kind):
    if kind not in DETAILS:
        raise ValueError('Unknown mechanics family.')
    relation, detail_model = DETAILS[kind]
    parent_form = modelform_factory(SupplementalEntry, fields=COMMON_FIELDS)
    detail_form = modelform_factory(detail_model, exclude=('entry',))
    attributes = {'__module__': __name__}
    labels = dict(DISPLAY[kind])
    for name, field in detail_form.base_fields.items():
        if name in labels:
            field.label = labels[name]
        attributes['detail_' + name] = field
    if kind == 'psionics':
        attributes['detail_class_levels'] = forms.CharField(
            required=False, widget=forms.Textarea(attrs={'rows': 3}),
            label=_('Class levels'),
            help_text=_('One class per line: Class name | Level. Use the printed class and level.'),
        )

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        if instance and instance.pk:
            detail = detail_for(instance)
            if detail:
                initial = dict(kwargs.pop('initial', {}) or {})
                for field in detail_model._meta.fields:
                    if field.name not in ('id', 'entry'):
                        initial['detail_' + field.name] = getattr(detail, field.name)
                if kind == 'monstrous-traits':
                    initial['detail_monsters'] = list(detail.monsters.values_list('pk', flat=True))
                if kind == 'psionics':
                    initial['detail_class_levels'] = '\n'.join(
                        '%s | %s' % (row.character_class.name, row.level)
                        for row in detail.class_levels.select_related('character_class').all())
                kwargs['initial'] = initial
        super(type(self), self).__init__(*args, **kwargs)
        self.fields['kind'].widget = forms.HiddenInput()
        self.fields['kind'].initial = kind

    def clean(self):
        values = super(type(self), self).clean()
        if values.get('kind') != kind:
            raise forms.ValidationError(_('The selected catalog type changed. Reload the form.'))
        for name in REQUIRED_DETAILS[kind]:
            value = values.get('detail_' + name)
            if value is None or value == '' or (name in ('monsters', 'class_levels') and not value):
                self.add_error('detail_' + name, _('Required for this catalog type.'))
        if kind == 'auras' and not (values.get('detail_character_class') or values.get('detail_monster')):
            self.add_error('detail_character_class', _('Choose a class or monster source.'))
        linked_monsters = []
        if kind == 'auras' and values.get('detail_monster'):
            linked_monsters = [values['detail_monster']]
        elif kind == 'monstrous-traits':
            linked_monsters = values.get('detail_monsters', [])
        if any(monster.rulebook.dnd_edition.system != 'DnD 3.5' for monster in linked_monsters):
            self.add_error('detail_monster' if kind == 'auras' else 'detail_monsters',
                           _('Linked monsters must come from confirmed D&D 3.5 rulebooks.'))
        if kind == 'psionics' and values.get('detail_class_levels'):
            try:
                parse_class_levels(values['detail_class_levels'])
            except forms.ValidationError as error:
                self.add_error('detail_class_levels', error)
        return values

    def save_details(self, entry):
        detail, _ = detail_model.objects.get_or_create(entry=entry)
        for field in detail_model._meta.fields:
            if field.name not in ('id', 'entry'):
                setattr(detail, field.name, self.cleaned_data['detail_' + field.name])
        detail.full_clean()
        detail.save()
        if kind == 'monstrous-traits':
            detail.monsters.set(self.cleaned_data['detail_monsters'])
        if kind == 'psionics':
            levels = parse_class_levels(self.cleaned_data['detail_class_levels'])
            detail.class_levels.all().delete()
            detail.class_levels.bulk_create([
                detail.class_levels.model(power=detail, character_class=character_class, level=level)
                for character_class, level in levels
            ])
        return detail

    attributes.update({'__init__': __init__, 'clean': clean, 'save_details': save_details})
    return type('%sEditorialForm' % detail_model.__name__, (parent_form,), attributes)
