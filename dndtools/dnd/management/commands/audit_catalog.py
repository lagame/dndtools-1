"""Exercise representative catalog URLs against the configured private database."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test import Client, override_settings
from django.urls import NoReverseMatch

from dnd.models import (
    CharacterClass, CharacterClassVariant, Deity, DndEdition, Domain,
    Feat, Item, Language, Monster, MonsterSubtype, MonsterType, Race, RaceType, Rule, RuleCondition,
    Rulebook, Skill, SkillVariant, Spell, SpellDescriptor, SpellSchool,
    SpellSubSchool,
)


MODELS = (
    DndEdition, Rulebook, CharacterClass, CharacterClassVariant,
    Spell, SpellSchool, SpellSubSchool, SpellDescriptor, Domain,
    Feat, Skill, SkillVariant, Race, RaceType, Monster, MonsterType,
    MonsterSubtype, Item, Language, Deity, Rule, RuleCondition,
)


class Command(BaseCommand):
    help = 'Read-only HTTP smoke checks for the first and last row of each catalog model.'

    def handle(self, *args, **options):
        client = Client(raise_request_exception=False)
        failed = []
        checked = 0
        with override_settings(ALLOWED_HOSTS=[*settings.ALLOWED_HOSTS, 'testserver']):
            for model in MODELS:
                rows = list(model.objects.order_by('pk')[:1]) + list(model.objects.order_by('-pk')[:1])
                seen = set()
                for row in rows:
                    if row.pk in seen:
                        continue
                    seen.add(row.pk)
                    try:
                        url = row.get_absolute_url()
                    except NoReverseMatch:
                        failed.append((model.__name__, row.pk, 'no reverse'))
                        checked += 1
                        continue
                    response = client.get(url, secure=not settings.DEBUG and settings.FORCE_HTTPS,
                                          follow=True)
                    checked += 1
                    if response.status_code != 200:
                        failed.append((model.__name__, row.pk, response.status_code))
                self.stdout.write('%s: %d sampled' % (model.__name__, len(seen)))
        if failed:
            raise CommandError('Failed %d of %d requests: %s' % (len(failed), checked, failed))
        self.stdout.write(self.style.SUCCESS('%d catalog detail requests returned 200.' % checked))
