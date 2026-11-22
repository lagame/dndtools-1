# -*- coding: utf-8 -*-
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from dnd.models import (
    Spell, DndEdition, Rulebook, CharacterClass, Domain, SpellDescriptor,
    SpellSchool, SpellSubSchool, FeatCategory, Feat,
    Skill, Monster, Item, Race, CreatureTemplate, SupplementalEntry)



class CatalogSitemap(Sitemap):
    protocol = 'https'


class IndexSitemap(CatalogSitemap):
    def items(self):
        return ('index', 'rulebook_list', 'spell_index', 'feat_index',
                'character_class_list', 'skill_list', 'race_index',
                'monster_index', 'item_index', 'rule_list')

    def location(self, item):
        return reverse(item)


class DndEditionSitemap(CatalogSitemap):
    def items(self):
        return DndEdition.objects.all()


class RulebookSitemap(CatalogSitemap):
    def items(self):
        return Rulebook.objects.select_related('dnd_edition').all()


class CharacterClassSitemap(CatalogSitemap):
    def items(self):
        return CharacterClass.objects.all()


class DomainSitemap(CatalogSitemap):
    def items(self):
        return Domain.objects.all()


class SpellDescriptorSitemap(CatalogSitemap):
    def items(self):
        return SpellDescriptor.objects.all()


class SpellSchoolSitemap(CatalogSitemap):
    def items(self):
        return SpellSchool.objects.all()


class SpellSubSchoolSitemap(CatalogSitemap):
    def items(self):
        return SpellSubSchool.objects.all()


class SpellSitemap(CatalogSitemap):
    def items(self):
        return Spell.objects.select_related('rulebook').all()


class FeatCategorySitemap(CatalogSitemap):
    def items(self):
        return FeatCategory.objects.all()


class SkillSitemap(CatalogSitemap):
    def items(self):
        return Skill.objects.all()


class FeatSitemap(CatalogSitemap):
    def items(self):
        return Feat.objects.select_related('rulebook',
                                           'rulebook__dnd_edition').all()


class MonsterSitemap(CatalogSitemap):
    def items(self):
        return Monster.objects.select_related('rulebook').all()


class ItemSitemap(CatalogSitemap):
    def items(self):
        return Item.objects.select_related('rulebook').all()


class RaceSitemap(CatalogSitemap):
    def items(self):
        return Race.objects.select_related('rulebook').all()


class CreatureTemplateSitemap(CatalogSitemap):
    def items(self):
        return CreatureTemplate.objects.select_related('rulebook').all()


class SupplementalEntrySitemap(CatalogSitemap):
    def items(self):
        return SupplementalEntry.objects.all()


sitemaps = {
    'Index': IndexSitemap,
    'DndEdition': DndEditionSitemap,
    'Rulebook': RulebookSitemap,
    'CharacterClass': CharacterClassSitemap,
    'Domain': DomainSitemap,
    'SpellDescriptor': SpellDescriptorSitemap,
    'SpellSchool': SpellSchoolSitemap,
    'SpellSubSchool': SpellSubSchoolSitemap,
    'Spell': SpellSitemap,
    'FeatCategory': FeatCategorySitemap,
    'Feat': FeatSitemap,
    'Skill': SkillSitemap,
    'Monster': MonsterSitemap,
    'Item': ItemSitemap,
    'Race': RaceSitemap,
    'CreatureTemplate': CreatureTemplateSitemap,
    'SupplementalEntry': SupplementalEntrySitemap,
    }
