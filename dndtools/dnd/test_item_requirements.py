from copy import deepcopy

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from dnd.editorial import source_digest
from dnd.item_requirements import RESOURCE, current_state, decode_submission, publish_requirements, validate_submission
from dnd.models import DndEdition, EditorialProposal, Feat, Item, PublishedTranslation, Rulebook, Spell, SpellSchool


class ItemRequirementsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        edition = DndEdition.objects.create(name='D&D 3.5', system='DnD 3.5', slug='35', core=True)
        cls.book = Rulebook.objects.create(name='Test Guide', abbr='TG', slug='test-guide', dnd_edition=edition)
        cls.item = Item.objects.create(name='Example Shield', page=13, rulebook=cls.book, slug='example-shield',
                                      type=Item.ItemType.ENHANCEMENT, description='A shield property.',
                                      required_extra='Originate it with one of two methods.')
        cls.feat = Feat.objects.create(name='Test Craft', page=18, rulebook=cls.book, slug='test-craft',
                                      description='A crafting feat.', benefit='Craft equipment.')
        school = SpellSchool.objects.create(name='Evocation', slug='evocation')
        cls.spell = Spell.objects.create(name='Test Spark', page=20, rulebook=cls.book, slug='test-spark',
                                        description='A tiny spark.', school=school, verbal_component=True,
                                        somatic_component=False, material_component=False, arcane_focus_component=False,
                                        divine_focus_component=False, xp_component=False, meta_breath_component=False,
                                        true_name_component=False)
        cls.reviewer = User.objects.create(username='item_reviewer')
        PublishedTranslation.objects.create(
            resource='Spell', target_pk=cls.spell.pk, locale='pt-br', payload={'name': 'Faísca de teste'},
            source_digest=source_digest(cls.spell, translation=True), author=cls.reviewer, reviewer=cls.reviewer,
        )

    def envelope(self):
        def ref(kind, record):
            return {'kind': kind, 'original_name': record.name, 'target_id': record.pk,
                    'reference': {'rulebook_id': self.book.pk, 'page': record.page}}
        return {'resource': RESOURCE, 'version': 1, 'items': [{
            'item_id': self.item.pk, 'original_name': self.item.name,
            'rulebook_id': self.book.pk, 'page': self.item.page,
            'source': {'rulebook_id': self.book.pk, 'pages': [13, 14]},
            'requirements': {'op': 'all', 'children': [ref('feat', self.feat), {'op': 'any', 'children': [
                ref('spell', self.spell), {'kind': 'psionic_power', 'original_name': 'An Unlisted Power',
                                         'reference': {'rulebook_id': self.book.pk, 'page': 25}},
            ]}]},
        }]}

    def publish(self, raw):
        envelope, _ = validate_submission(raw, lock=True)
        proposal = EditorialProposal.objects.create(resource='Item', action='item_reqs', status='approved',
                                                   author=self.reviewer, reviewer=self.reviewer, payload=envelope)
        publish_requirements(envelope, proposal)

    def test_same_tree_in_both_languages_and_legacy_after_source_edit(self):
        digest_before = source_digest(self.item, translation=True)
        self.publish(self.envelope())
        path = self.item.get_absolute_url()
        english = self.client.get(path)
        self.assertContains(english, 'All of these are required')
        self.assertContains(english, 'At least one of these options is enough')
        self.assertContains(english, self.spell.get_absolute_url())
        portuguese = self.client.get('/pt-br' + path)
        self.assertContains(portuguese, 'Cumpra todos os requisitos abaixo')
        self.assertContains(portuguese, 'Uma destas opções já basta')
        self.assertContains(portuguese, 'Faísca de teste')
        self.assertContains(portuguese, '(Test Spark)')
        self.assertContains(portuguese, 'Poder psiônico')
        self.assertContains(portuguese, 'p. 25')
        self.assertNotContains(portuguese, 'Originate it with one of two methods')
        self.item.refresh_from_db()
        self.assertEqual(source_digest(self.item, translation=True), digest_before)
        self.item.required_extra = 'Source was corrected.'
        self.item.save(update_fields=['required_extra'])
        self.assertEqual(current_state(self.item), 'stale')
        changed = self.client.get(path)
        self.assertContains(changed, 'Source was corrected.')
        self.assertNotContains(changed, 'All of these are required')

    def test_link_removal_keeps_the_printed_reference(self):
        self.publish(self.envelope())
        spell_path = self.spell.get_absolute_url()
        self.spell.delete()
        response = self.client.get(self.item.get_absolute_url())
        self.assertContains(response, 'Test Spark')
        self.assertContains(response, 'p. 20')
        self.assertNotContains(response, f'href="{spell_path}"')

    def test_rejects_mismatched_links_and_invalid_groups(self):
        source = self.envelope()
        alternative = source['items'][0]['requirements']['children'][1]
        alternative['children'][0]['original_name'] = self.spell.name.lower()
        normalized, _ = validate_submission(source)
        children = normalized['items'][0]['requirements']['children'][1]['children']
        self.assertEqual(children[0]['original_name'], self.spell.name)
        self.assertEqual(children[0]['target_id'], self.spell.pk)
        wrong_page = deepcopy(source)
        wrong_page['items'][0]['requirements']['children'][0]['reference']['page'] += 1
        invalid_group = deepcopy(source)
        invalid_group['items'][0]['requirements']['children'].pop()
        wrong_source = deepcopy(source)
        other_edition = DndEdition.objects.create(name='D&D 3.0', system='DnD 3.0', slug='30', core=True)
        other_book = Rulebook.objects.create(name='Older Guide', abbr='OG', slug='older-guide', dnd_edition=other_edition)
        wrong_source['items'][0]['source']['rulebook_id'] = other_book.pk
        for raw, error in ((wrong_page, 'Check the confirmed reference'),
                           (wrong_source, 'different rules edition'),
                           (invalid_group, 'at least two requirements')):
            with self.subTest(error=error), self.assertRaisesMessage(ValidationError, error):
                validate_submission(raw)
        with self.assertRaisesMessage(ValidationError, 'duplicate keys'):
            decode_submission(b'{"op":"all","op":"any"}')

    def test_confirmed_none_differs_from_missing_data(self):
        self.item.required_extra = ''
        self.item.save(update_fields=['required_extra'])
        path = self.item.get_absolute_url()
        self.assertNotContains(self.client.get(path), 'Creation prerequisites')
        raw = self.envelope()
        raw['items'][0]['requirements'] = {'op': 'none'}
        self.publish(raw)
        self.assertContains(self.client.get(path), 'The reviewed source specifies no creation prerequisites.')
