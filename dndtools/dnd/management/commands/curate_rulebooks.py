"""Classify the recovered rulebooks without changing later editorial records."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from dnd.models import Rulebook


LEGACY_FINGERPRINT = '0e6236d6fd6c00d5436e57b6bd3a877874f2c67289bdb0e0b952ace5e974c66e'
LEGACY_COVERS = {
    int(book_id): name for book_id, name in json.loads(
        (Path(__file__).resolve().parents[2] / 'legacy_rulebook_covers.json').read_text(
            encoding='utf-8')).items()
}
ADVENTURES = {99, 102, 103, 104, 113, 114, 115}
PERIODICALS = {108, 116, 117}
SETTINGS = {19, 94, 96, 98, 12}
CORE = {4, 5, 6, 106, 107}
SETTING_GUIDES = {11, 13, 14, 15, 16, 24, 25, 30, 33, 34, 97, 100, 101, 105}

# Original editorial summaries for the 53 blank descriptions in the recovered
# rules catalog. Existing descriptions and later editor contributions are kept.
LEGACY_SUMMARIES = {
    6: 'The revised D&D 3.5 player rules cover character creation, classes, skills, feats, equipment, combat, and spells.',
    8: 'A guide to Eberron\'s religions and faiths, with divine character options, feats, and spells.',
    9: 'Expands magic in Eberron with new spells, feats, and options for magical characters.',
    11: 'A guide to Sharn, the City of Towers, covering its districts, factions, and adventure possibilities in Eberron.',
    12: 'The core guide to Eberron introduces its nations, peoples, religions, and D&D 3.5 campaign rules.',
    13: 'A player-facing introduction to Eberron, with setting information and character options for its regions and cultures.',
    15: 'Explores the lost civilizations, ruins, and dangers of Xen\'drik for Eberron adventures.',
    17: 'A collection of ready-to-use allies and adversaries for D&D 3.0 campaigns.',
    18: 'Details the gods and religious traditions of the Forgotten Realms, alongside divine game options.',
    19: 'The core Forgotten Realms setting guide describes Faerûn\'s regions, peoples, gods, and campaign rules.',
    20: 'A Forgotten Realms magic supplement with spells, feats, and other options for spellcasters.',
    21: 'A creature reference for the Forgotten Realms, presenting monsters and their place in Faerûn.',
    22: 'Player options for D&D 3.5 campaigns in the Forgotten Realms, including regional material, feats, and spells.',
    23: 'Expands the playable peoples of Faerûn with racial lore and character options.',
    25: 'Explores the southern lands of Faerûn with regional lore, spells, and character options.',
    26: 'A guide to the dragons of Faerûn, including draconic lore and game material.',
    27: 'Presents villains and darker character options for Forgotten Realms campaigns.',
    28: 'Presents heroic organizations and character options for Forgotten Realms campaigns.',
    30: 'Explores ancient civilizations and their surviving ruins in the Forgotten Realms.',
    31: 'A Forgotten Realms guide to political power, leadership, and high-stakes campaigns.',
    34: 'Explores the realms beneath Faerûn, their inhabitants, and the hazards of Underdark adventures.',
    35: 'A D&D 3.0 equipment reference covering weapons, armor, vehicles, and magic items.',
    40: 'Additional tools and options for Dungeon Masters running D&D 3.5 campaigns.',
    42: 'A monster reference featuring fiends and other creatures for D&D 3.0 adventures.',
    46: 'Introduces the D&D 3.0 psionics system, including psionic classes, powers, and feats.',
    50: 'Character options and combat material focused on fighters and monks in D&D 3.0.',
    59: 'Expands D&D 3.5 psionics with new feats, powers, and character options.',
    62: 'Draconic-themed magic and character options, including spells and feats.',
    66: 'Explores the Abyss and its demons, with lore and character options for D&D 3.5.',
    73: 'A D&D 3.5 reference for magic items and their use in character equipment.',
    82: 'Character options and lore for dwarves, gnomes, goliaths, and other peoples associated with stone.',
    86: 'Collects spells from D&D 3.5 supplements, Dragon magazine, and other published sources into one reference.',
    87: 'Rules and character options for nautical adventures, ships, and aquatic environments.',
    91: 'Rules for magic weapons that develop with their wielders, together with example legacy items.',
    92: 'A D&D 3.5 guide to dragons, with creature lore, spells, and character options.',
    93: 'Explores drow society and game options for Underdark campaigns.',
    95: 'A Forgotten Realms guide to villainous organizations, their leaders, and their schemes.',
    97: 'A regional guide to the Silver Marches and adventure in the northern Forgotten Realms.',
    98: 'The Dragonlance campaign setting introduces Krynn and its D&D 3.5 character options.',
    99: 'A D&D 3.5 adventure that takes characters into the Demonweb Pits and the schemes of Lolth.',
    100: 'An Eberron guide to travel and exploration across Khorvaire and beyond.',
    101: 'Details the Five Nations of Khorvaire and their role in Eberron campaigns.',
    102: 'A D&D 3.5 horror adventure centered on Castle Ravenloft and Count Strahd.',
    103: 'A D&D 3.0 adventure returning to the Temple of Elemental Evil and its cults.',
    104: 'A D&D 3.5 adventure through the ruins and threats surrounding Slaughtergarde.',
    105: 'Explores Eberron\'s Last War and its consequences for characters and campaigns.',
    106: 'The original D&D 3.0 player rules cover character creation, classes, skills, feats, combat, and spells.',
    107: 'A core D&D creature reference with monster statistics and encounter material.',
    109: 'Collects character and campaign material from Dragon magazine, including feats and spells.',
    116: 'Dragon magazine issue 326, with D&D 3.5 articles and spells indexed in this catalog.',
    117: 'Dragon magazine issue 324, with D&D 3.5 articles and spells indexed in this catalog.',
    118: 'A game supplement on the pirates of Tellene and seafaring campaigns.',
    119: 'A Dragonlance guide to the Towers of High Sorcery and arcane traditions of Krynn.',
}


def category_for(book):
    if book.pk in ADVENTURES:
        return 'adventure'
    if book.pk in PERIODICALS:
        return 'periodical'
    if book.pk in SETTINGS:
        return 'setting'
    if book.pk in CORE:
        return 'core'
    if book.pk in SETTING_GUIDES:
        return 'setting_guide'
    return 'sourcebook'


class Command(BaseCommand):
    help = 'Preview or apply editorial categories to the 114 recovered rulebooks.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        books = list(Rulebook.objects.filter(id__lte=119).select_related('dnd_edition').order_by('id'))
        fingerprint = hashlib.sha256('\n'.join('%d:%s' % (book.pk, book.name)
                                                for book in books).encode()).hexdigest()
        if fingerprint != LEGACY_FINGERPRINT:
            raise CommandError('Legacy rulebook identity differs; review the catalog before applying categories.')
        counts = Counter(category_for(book) for book in books)
        missing = [book.pk for book in books
                   if not (book.description or '').strip() and book.pk not in LEGACY_SUMMARIES]
        if missing:
            raise CommandError('Blank legacy descriptions need editorial summaries: %s' % missing)
        self.stdout.write('Recovered rulebooks: %d; categories: %s' % (len(books), dict(counts)))
        self.stdout.write('Descriptions to add: %d.' % sum(
            not (book.description or '').strip() for book in books))
        self.stdout.write('Covers to link: %d.' % sum(
            not book.image and book.pk in LEGACY_COVERS for book in books))
        if not options['apply']:
            self.stdout.write('Dry run only. Pass --apply after a verified database backup.')
            return

        with transaction.atomic():
            changed = 0
            described = 0
            covered = 0
            for book in books:
                fields = []
                if not book.publication_type:
                    book.publication_type = category_for(book)
                    fields.append('publication_type')
                    changed += 1
                if not (book.description or '').strip() and book.pk in LEGACY_SUMMARIES:
                    book.description = LEGACY_SUMMARIES[book.pk]
                    fields.append('description')
                    described += 1
                if not book.image and book.pk in LEGACY_COVERS:
                    book.image.name = 'rulebook/' + LEGACY_COVERS[book.pk]
                    fields.append('image')
                    covered += 1
                if fields:
                    book.save(update_fields=fields)
            bad = Rulebook.objects.filter(pk=67, year='psvo').update(
                year=None, official_url='')
        self.stdout.write(self.style.SUCCESS(
            'Classified %d rulebooks; added %d descriptions and %d cover references; '
            'removed %d invalid URL/year pair.' % (changed, described, covered, bad)))
