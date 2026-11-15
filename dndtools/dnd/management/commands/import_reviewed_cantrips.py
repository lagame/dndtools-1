"""Import source-reviewed 3.5 cantrips into an existing D&D Tools database."""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max
from django.utils.text import slugify

from dnd.models import (
    CharacterClass, DndEdition, Rulebook, Spell, SpellClassLevel,
    SpellDescriptor, SpellSchool, SpellSubSchool,
)


DATA_FILE = Path(__file__).resolve().parents[2] / 'data' / 'reviewed_cantrips_35.json'
BOOK_ABBREVIATIONS = {
    'Dragon Magazine #324': 'Dr324',
    'Dragon Magazine #326': 'Dr326',
    'Salt and Sea Dogs: The Pirates of Tellene': 'SSDT',
    'Towers of High Sorcery': 'THS',
}
COMPONENT_FIELDS = {
    'V': 'verbal_component',
    'S': 'somatic_component',
    'M': 'material_component',
    'AF': 'arcane_focus_component',
    'DF': 'divine_focus_component',
    'XP': 'xp_component',
}
ALL_COMPONENT_FIELDS = tuple(COMPONENT_FIELDS.values()) + ('meta_breath_component', 'true_name_component')
OPTIONAL_FIELDS = (
    'casting_time', 'range', 'target', 'effect', 'area', 'duration',
    'saving_throw', 'spell_resistance',
)


class Command(BaseCommand):
    help = 'Review or apply the seven source-checked 3.5 cantrips; dry run by default.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Write reviewed records to the configured database.')

    def handle(self, *args, **options):
        entries = json.loads(DATA_FILE.read_text(encoding='utf-8'))
        seen = set()
        plans = []
        for entry in entries:
            key = (entry['name'].casefold(), entry['book'].casefold())
            if key in seen:
                raise CommandError('Repeated entry in data file: %s' % (key,))
            seen.add(key)
            if 'Wizard' not in entry['levels'] or entry['levels']['Wizard'] != 0:
                raise CommandError('Not a Wizard level 0 spell: %s' % entry['name'])
            if entry['edition'] not in ('supplementals-35', 'dragonlance'):
                raise CommandError('Unreviewed edition: %s' % entry['edition'])
            if entry['book'] not in BOOK_ABBREVIATIONS:
                raise CommandError('Unreviewed book: %s' % entry['book'])
            if not set(entry['components']) <= set(COMPONENT_FIELDS):
                raise CommandError('Unknown component: %s' % entry['name'])
            if not SpellSchool.objects.filter(name=entry['school']).exists():
                raise CommandError('Unknown school: %s' % entry['school'])
            if entry.get('sub_school') and not SpellSubSchool.objects.filter(name=entry['sub_school']).exists():
                raise CommandError('Unknown subschool: %s' % entry['sub_school'])
            for name in entry['levels']:
                if not CharacterClass.objects.filter(name=name).exists():
                    raise CommandError('Unknown class: %s' % name)
            for name in entry.get('descriptors', []):
                if not SpellDescriptor.objects.filter(name=name).exists():
                    raise CommandError('Unknown descriptor: %s' % name)
            edition = DndEdition.objects.get(slug=entry['edition'])
            books = list(Rulebook.objects.filter(name__iexact=entry['book']))
            if books and (len(books) != 1 or books[0].dnd_edition_id != edition.id):
                raise CommandError('Conflicting rulebook: %s' % entry['book'])
            book = books[0] if books else None
            slug = slugify(entry['name'])
            matches = list(Spell.objects.filter(name__iexact=entry['name']).select_related('rulebook'))
            if any(spell.rulebook_id != (book.id if book else None) for spell in matches):
                raise CommandError('Same name already exists in another book; review manually: %s' % entry['name'])
            if len(matches) > 1:
                raise CommandError('Ambiguous spell: %s' % entry['name'])
            spell = matches[0] if matches else None
            if spell:
                if spell.slug != slug or spell.page != entry['page'] or spell.school.name != entry['school']:
                    raise CommandError('Existing spell differs from reviewed record: %s' % entry['name'])
                current = dict(SpellClassLevel.objects.filter(spell=spell).values_list('character_class__name', 'level'))
                if current != entry['levels']:
                    raise CommandError('Existing class levels differ: %s' % entry['name'])
            plans.append((entry, edition, book, spell, slug))

        pending = sum(spell is None for _, _, _, spell, _ in plans)
        for entry, _, _, spell, _ in plans:
            self.stdout.write('%s: %s' % (entry['name'], 'already present' if spell else 'create'))
        self.stdout.write('Reviewed: %d; to create: %d' % (len(plans), pending))
        if not options['apply']:
            self.stdout.write('Dry run only. Pass --apply to write.')
            return

        with transaction.atomic():
            through = Spell.descriptors.through
            models = (Rulebook, Spell, SpellClassLevel, through)
            next_ids = {model: (model.objects.aggregate(max_id=Max('id'))['max_id'] or 0) + 1
                        for model in models}

            def next_id(model):
                value = next_ids[model]
                next_ids[model] += 1
                return value

            created_books = {}
            for entry, edition, book, spell, slug in plans:
                if spell:
                    continue
                if book is None:
                    book = created_books.get(entry['book'])
                    if book is None:
                        book = Rulebook.objects.create(
                            id=next_id(Rulebook), name=entry['book'], dnd_edition=edition,
                            slug=slugify(entry['book']), abbr=BOOK_ABBREVIATIONS[entry['book']],
                        )
                        created_books[entry['book']] = book
                kwargs = {
                    'id': next_id(Spell), 'name': entry['name'], 'slug': slug, 'rulebook': book,
                    'page': entry['page'], 'school': SpellSchool.objects.get(name=entry['school']),
                    'sub_school': SpellSubSchool.objects.get(name=entry['sub_school']) if entry.get('sub_school') else None,
                    'description': entry['description'],
                }
                present_components = {COMPONENT_FIELDS[c] for c in entry['components']}
                kwargs.update({field: field in present_components for field in ALL_COMPONENT_FIELDS})
                kwargs.update({field: entry.get(field) for field in OPTIONAL_FIELDS})
                spell = Spell.objects.create(**kwargs)
                for class_name, level in entry['levels'].items():
                    SpellClassLevel.objects.create(
                        id=next_id(SpellClassLevel), spell=spell,
                        character_class=CharacterClass.objects.get(name=class_name), level=level,
                    )
                for descriptor in SpellDescriptor.objects.filter(name__in=entry.get('descriptors', [])):
                    through.objects.create(
                        id=next_id(through), spell_id=spell.id, spelldescriptor_id=descriptor.id,
                    )
                self.stdout.write('Created %s: %s' % (entry['name'], spell.get_absolute_url()))
