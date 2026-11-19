from unittest.mock import patch
from datetime import datetime, timedelta, timezone
import json
import smtplib
from io import StringIO

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission
from django.core import mail
from django.core.management import call_command
from django.test import Client, TestCase
from django.test.utils import override_settings
from django.urls import reverse

from dnd.editorial import RESOURCES, RESOURCE_LABELS, FIELD_LABELS, editable_form, approve
from dnd.access import verified_email
from dnd.supplemental.catalog import detail_for
from dnd.models import (CharacterClass, CollaboratorInvite, CreatureTemplate, DndEdition, EditorialGrant,
                        EditorialProposal, Feat, FeatCategory, FeatRequiresFeat, Monster, MonsterType, MysteryDetail, PublishedTranslation,
                        RaceSize, Rulebook, Spell, SpellSchool, SupplementalEntry)


class EditorialFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_superuser('ronassic', settings.ADMINS[0][1], 'long-test-password-123')
        cls.editor = User.objects.create_user('geeksublime', 'geeksublime@example.test',
                                              'long-test-password-123', is_staff=True)
        cls.edition = DndEdition.objects.create(name='Core 3.5', slug='core-35', system='DnD 3.5', core=True)
        cls.book = Rulebook.objects.create(name='Test Source', slug='test-source', abbr='TS',
                                            dnd_edition=cls.edition)
        cls.old_edition = DndEdition.objects.create(name='Core 3.0', slug='core-30', system='DnD 3.0', core=True)
        cls.old_book = Rulebook.objects.create(name='Old Source', slug='old-source', abbr='OS',
                                                dnd_edition=cls.old_edition)
        cls.test_class = CharacterClass.objects.create(name='Test Class', slug='test-class', prestige=False)
        EditorialGrant.objects.create(user=cls.editor, resource='SupplementalEntry',
                                      can_create=True, can_correct=True, can_translate=True)

    def _typed_data(self, kind):
        values = {
            'mysteries': {'detail_path': 'Ebon Whispers', 'detail_grade': 'apprentice',
                          'detail_mystery_level': 1},
            'invocations': {'detail_grade': 'least', 'detail_invocation_type': 'other',
                            'detail_equivalent_level': 1, 'detail_character_class': self.test_class.pk},
            'psionics': {'detail_discipline': 'Clairsentience', 'detail_power_points': 1,
                         'detail_class_levels': 'Test Class | 1'},
            'auras': {'detail_character_class': self.test_class.pk, 'detail_radius': '30 ft.'},
            'maneuvers': {'detail_discipline': 'Desert Wind', 'detail_maneuver_level': 1,
                          'detail_maneuver_type': 'strike'},
            'monstrous-traits': {'detail_ability_type': 'Ex', 'detail_role': 'attack'},
        }[kind]
        if kind == 'monstrous-traits':
            monster = Monster.objects.filter(name='Typed Test Monster').first()
            if monster is None:
                monster_type = MonsterType.objects.create(name='Test type', slug='test-type')
                monster = Monster.objects.create(
                    rulebook=self.book, name='Typed Test Monster', slug='typed-test-monster',
                    type=monster_type, hit_dice='1d8 (4 hp)', initiative=0,
                    armor_class='10', base_attack=0, grapple=0, attack='Claw +0 (1d4)',
                    full_attack='Claw +0 (1d4)', space=5, reach=5,
                    fort_save=0, reflex_save=0, will_save=0, str=10, dex=10, con=10,
                    int=10, wis=10, cha=10, challenge_rating=1)
            values['detail_monsters'] = [monster.pk]
        return values

    def test_permission_and_review_gate_for_missing_crud(self):
        url = reverse('editorial_create', args=('SupplementalEntry',))
        self.assertEqual(self.client.get(url).status_code, 302)
        other = User.objects.create_user('other', 'other@example.test', 'long-test-password-123', is_staff=True)
        self.client.force_login(other)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(url).status_code, 200)
        data = {'kind': 'invocations', 'rulebook': self.book.pk, 'page': 42,
                'name': 'Test Invocation', 'category': 'Least', 'level': '1',
                'prerequisites': '', 'mechanics': 'A verified test effect.',
                'description': '', 'source_reference': 'Test Source p. 42, D&D 3.5',
                **self._typed_data('invocations')}
        self.assertEqual(self.client.post(url, data).status_code, 302)
        proposal = EditorialProposal.objects.get()
        self.assertEqual(proposal.status, 'pending')
        self.assertFalse(SupplementalEntry.objects.exists())
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(reverse('editorial_dashboard')), 'Pending collaborations: 1')
        response = self.client.post(reverse('editorial_decide', args=(proposal.pk,)), {'decision': 'approve'})
        self.assertEqual(response.status_code, 302)
        entry = SupplementalEntry.objects.get()
        self.assertEqual(entry.slug, 'test-invocation')
        self.assertEqual(self.client.get(entry.get_absolute_url()).status_code, 200)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, 'approved')

    def test_django_admin_permissions_cannot_bypass_editorial_review(self):
        entry = SupplementalEntry.objects.create(kind='auras', rulebook=self.book,
                                                 name='Guarded Aura', slug='guarded-aura',
                                                 mechanics='Published effect')
        self.editor.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='dnd', content_type__model='supplementalentry'))
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(reverse('admin:dnd_supplementalentry_add')).status_code, 403)
        self.assertEqual(self.client.get(reverse('admin:dnd_supplementalentry_change', args=(entry.pk,))).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:dnd_supplementalentry_changelist')).status_code, 200)
        self.assertEqual(self.client.post(reverse('admin:dnd_supplementalentry_change', args=(entry.pk,)),
                                          {'name': 'Bypassed'}).status_code, 403)
        entry.refresh_from_db()
        self.assertEqual(entry.name, 'Guarded Aura')
        self.assertEqual(self.client.get(reverse('editorial_create', args=('SupplementalEntry',)) +
                                         '?kind=auras').status_code, 200)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse('admin:dnd_supplementalentry_change',
                                                     args=(entry.pk,))).status_code, 200)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                       EDITORIAL_NOTIFY_EMAIL='owner@example.test',
                       DEFAULT_FROM_EMAIL='alerts@example.test')
    def test_owner_receives_alert_for_every_submitted_collaboration(self):
        self.client.force_login(self.editor)
        response = self.client.post(reverse('editorial_create', args=('SupplementalEntry',)), {
            'kind': 'auras', 'rulebook': self.book.pk, 'name': 'Test Aura',
            'mechanics': 'A verified effect',
            'source_reference': 'Test Source p. 15, D&D 3.5',
            **self._typed_data('auras'),
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['owner@example.test'])
        self.assertIn('new collaboration #', mail.outbox[0].subject)
        self.assertNotIn('A verified effect', mail.outbox[0].body)

    def test_new_30_record_is_rejected_before_submission(self):
        self.client.force_login(self.editor)
        response = self.client.post(reverse('editorial_create', args=('SupplementalEntry',)), {
            'kind': 'psionics', 'rulebook': self.old_book.pk, 'name': 'Old Power',
            'mechanics': 'Old rules', 'source_reference': 'Old Source p. 1',
            **self._typed_data('psionics'),
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'confirmed D&amp;D 3.5 rulebook')
        self.assertFalse(EditorialProposal.objects.exists())

    def test_complete_translation_requires_review_and_current_source(self):
        entry = SupplementalEntry.objects.create(kind='mysteries', rulebook=self.book,
                                                  name='Mystery', slug='mystery', mechanics='Original effect')
        self.client.force_login(self.editor)
        url = reverse('editorial_translate', args=('SupplementalEntry', entry.pk))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        from dnd.editorial import translation_form
        fields = translation_form(entry)().fields
        data = {name: 'PT ' + str(getattr(entry, name)) for name in fields}
        data['source_reference'] = 'Manual translation from Test Source p. 42'
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertFalse(PublishedTranslation.objects.exists())
        proposal = EditorialProposal.objects.get()
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(reverse('editorial_decide', args=(proposal.pk,)),
                                          {'decision': 'approve'}).status_code, 302)
        self.assertEqual(PublishedTranslation.objects.get().payload['name'], 'PT Mystery')

        self.client.force_login(self.editor)
        self.client.post(url, data)
        stale = EditorialProposal.objects.filter(status='pending').first()
        entry.mechanics = 'Changed after submission'
        entry.save()
        self.client.force_login(self.owner)
        self.client.post(reverse('editorial_decide', args=(stale.pk,)), {'decision': 'approve'})
        stale.refresh_from_db()
        self.assertEqual(stale.status, 'pending')

    def test_creature_template_public_empty_page(self):
        self.assertEqual(self.client.get(reverse('creature_template_index')).status_code, 200)
        self.assertEqual(self.client.get(reverse('supplemental_index', args=('auras',))).status_code, 200)
        self.assertEqual(self.client.get(reverse('supplemental_index', args=('unknown',))).status_code, 404)

    def test_editorial_catalog_search_ignores_case(self):
        entry = SupplementalEntry.objects.create(kind='auras', rulebook=self.book,
                                                 name='Arcane Aura', slug='arcane-aura',
                                                 mechanics='A verified effect')
        self.client.force_login(self.editor)
        response = self.client.get(reverse('editorial_catalog', args=('SupplementalEntry',)),
                                   {'kind': 'auras', 'q': 'ARCANE'})
        self.assertContains(response, entry.name)

    def test_relation_catalog_searches_related_names_and_shows_them(self):
        required = Feat.objects.create(rulebook=self.book, name='Power Attack',
                                       slug='power-attack', description='Rule', benefit='Benefit')
        dependent = Feat.objects.create(rulebook=self.book, name='Cleave',
                                        slug='cleave', description='Rule', benefit='Benefit')
        link = FeatRequiresFeat.objects.create(source_feat=dependent, required_feat=required)
        self.assertEqual(str(link), 'Cleave → Power Attack')
        self.client.force_login(self.owner)
        url = reverse('editorial_catalog', args=('FeatRequiresFeat',))
        self.assertContains(self.client.get(url, {'q': 'power attack'}), 'Cleave → Power Attack')
        self.assertContains(self.client.get(url, {'q': 'CLEAVE'}), 'Cleave → Power Attack')
        self.assertContains(self.client.get(url, {'q': str(link.pk)}), 'Cleave → Power Attack')
        self.assertContains(self.client.get(url, {'q': 'missing'}), 'No matching records.')

    def test_each_missing_mechanic_has_moderated_create_and_public_read(self):
        self.client.force_login(self.owner)
        dashboard = self.client.get(reverse('editorial_dashboard'))
        for kind, label in SupplementalEntry.KINDS:
            with self.subTest(kind=kind):
                self.assertContains(dashboard, label)
                catalog_url = reverse('editorial_catalog', args=('SupplementalEntry',)) + '?kind=' + kind
                create_url = reverse('editorial_create', args=('SupplementalEntry',)) + '?kind=' + kind
                self.assertEqual(self.client.get(catalog_url).status_code, 200)
                form_page = self.client.get(create_url)
                self.assertContains(form_page, 'name="kind"')
                self.assertContains(form_page, 'value="' + kind + '"')
                response = self.client.post(create_url, {
                    'kind': kind, 'rulebook': self.book.pk, 'page': 12,
                    'name': 'Sample ' + kind, 'category': 'Published category',
                    'level': '1', 'mechanics': 'Verified 3.5 mechanics',
                    'source_reference': 'Test Source p. 12, D&D 3.5',
                    **self._typed_data(kind),
                })
                self.assertEqual(response.status_code, 302)
                self.assertFalse(SupplementalEntry.objects.filter(kind=kind).exists())
                proposal = EditorialProposal.objects.filter(resource='SupplementalEntry').latest('pk')
                self.assertEqual(self.client.post(reverse('editorial_decide', args=(proposal.pk,)),
                                                  {'decision': 'approve'}).status_code, 302)
                entry = SupplementalEntry.objects.get(kind=kind)
                self.assertIsNotNone(detail_for(entry))
                self.assertContains(self.client.get(entry.get_absolute_url()), entry.name)
                facet = {
                    'mysteries': ('grade', 'apprentice'),
                    'invocations': ('grade', 'least'),
                    'psionics': ('discipline', 'Clairsentience'),
                    'auras': ('character_class', self.test_class.pk),
                    'maneuvers': ('maneuver_type', 'strike'),
                    'monstrous-traits': ('ability_type', 'Ex'),
                }[kind]
                self.assertContains(self.client.get(reverse('supplemental_index', args=(kind,)),
                                                    {facet[0]: facet[1]}), entry.name)
                if kind == 'psionics':
                    self.assertContains(self.client.get(reverse('supplemental_index', args=(kind,)),
                                                        {'power_points': '1'}),
                                        '<option value="1" selected>1</option>', html=True)
                self.assertNotContains(self.client.get(reverse('supplemental_index', args=(kind,)),
                                                       {'q': 'No such record'}), entry.name)

        self.assertContains(self.client.get('/search/?q=Sample+psionics'), 'Psionic powers')

        tampered = self.client.post(reverse('editorial_create', args=('SupplementalEntry',)) +
                                    '?kind=maneuvers', {
            'kind': 'auras', 'rulebook': self.book.pk, 'name': 'Wrong section',
            'mechanics': 'Effect', 'source_reference': 'Test Source p. 12, D&D 3.5',
        })
        self.assertEqual(tampered.status_code, 200)
        self.assertContains(tampered, 'selected catalog type changed')
        self.assertFalse(EditorialProposal.objects.filter(payload__name='Wrong section').exists())

    def test_typed_form_requires_source_specific_fields_before_proposal(self):
        self.client.force_login(self.editor)
        for kind, _ in SupplementalEntry.KINDS:
            with self.subTest(kind=kind):
                response = self.client.post(reverse('editorial_create', args=('SupplementalEntry',)) +
                                            '?kind=' + kind, {
                    'kind': kind, 'rulebook': self.book.pk, 'name': 'Incomplete ' + kind,
                    'mechanics': 'Rule text', 'source_reference': 'Test Source p. 1, D&D 3.5',
                })
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Required for this catalog type')
                self.assertFalse(EditorialProposal.objects.filter(payload__name='Incomplete ' + kind).exists())

    def test_typed_links_require_confirmed_35_monsters(self):
        from dnd.supplemental.forms import typed_form
        monster_pk = self._typed_data('monstrous-traits')['detail_monsters'][0]
        monster = Monster.objects.get(pk=monster_pk)
        monster.pk = None
        monster.name = 'Old Monster'
        monster.slug = 'old-monster'
        monster.rulebook = self.old_book
        monster.save()
        common = {'rulebook': self.book.pk, 'name': 'Invalid source', 'mechanics': 'Effect'}
        for kind, linked in (('auras', {'detail_monster': monster.pk}),
                             ('monstrous-traits', {'detail_monsters': [monster.pk]})):
            with self.subTest(kind=kind):
                data = common | {'kind': kind} | self._typed_data(kind) | linked
                form = typed_form(kind)(data)
                self.assertFalse(form.is_valid())
                self.assertIn('Linked monsters must come from confirmed D&D 3.5 rulebooks.',
                              [message for errors in form.errors.as_data().values()
                               for error in errors for message in error.messages])

    def test_typed_correction_staleness_and_reviewed_removal(self):
        self.client.force_login(self.editor)
        base = {'kind': 'maneuvers', 'rulebook': self.book.pk, 'name': 'Steel Step',
                'mechanics': 'Original maneuver', 'source_reference': 'Test Source p. 10, D&D 3.5',
                **self._typed_data('maneuvers')}
        create_url = reverse('editorial_create', args=('SupplementalEntry',)) + '?kind=maneuvers'
        self.assertEqual(self.client.post(create_url, base).status_code, 302)
        self.client.force_login(self.owner)
        self.client.post(reverse('editorial_decide', args=(EditorialProposal.objects.get().pk,)),
                         {'decision': 'approve'})
        entry = SupplementalEntry.objects.get()
        original_url = entry.get_absolute_url()
        correction_url = reverse('editorial_correct', args=('SupplementalEntry', entry.pk))
        self.client.force_login(self.editor)
        changed = base | {'mechanics': 'Revised maneuver', 'detail_maneuver_level': 2}
        self.assertEqual(self.client.post(correction_url, changed).status_code, 302)
        correction = EditorialProposal.objects.get(action='correct')
        self.assertEqual(entry.maneuver_detail.maneuver_level, 1)
        self.client.force_login(self.owner)
        self.client.post(reverse('editorial_decide', args=(correction.pk,)), {'decision': 'approve'})
        entry.refresh_from_db()
        self.assertEqual(entry.maneuver_detail.maneuver_level, 2)
        self.assertEqual(entry.get_absolute_url(), original_url)
        self.assertContains(self.client.get(original_url), 'Revised maneuver')
        self.client.force_login(self.editor)
        self.client.post(correction_url, changed | {'detail_maneuver_level': 3})
        stale = EditorialProposal.objects.filter(action='correct', status='pending').get()
        entry.maneuver_detail.maneuver_level = 4
        entry.maneuver_detail.save()
        self.client.force_login(self.owner)
        self.client.post(reverse('editorial_decide', args=(stale.pk,)), {'decision': 'approve'})
        stale.refresh_from_db()
        self.assertEqual(stale.status, 'pending')
        self.client.post(reverse('editorial_delete', args=('SupplementalEntry', entry.pk)),
                         {'source_reference': 'Test Source p. 10, retraction'})
        removal = EditorialProposal.objects.get(action='delete')
        self.assertTrue(SupplementalEntry.objects.filter(pk=entry.pk).exists())
        result = self.client.post(reverse('editorial_decide', args=(removal.pk,)), {'decision': 'approve'})
        self.assertFalse(SupplementalEntry.objects.filter(pk=entry.pk).exists(),
                         [str(message) for message in result.wsgi_request._messages])
        self.assertEqual(self.client.get(original_url).status_code, 404)

    def test_legacy_entry_can_gain_reviewed_structured_details(self):
        entry = SupplementalEntry.objects.create(
            kind='mysteries', rulebook=self.book, name='Old Mystery',
            slug='old-mystery', category='Old category', mechanics='Existing rule')
        original_url = entry.get_absolute_url()
        self.client.force_login(self.editor)
        correction_url = reverse('editorial_correct', args=('SupplementalEntry', entry.pk))
        self.assertContains(self.client.get(correction_url), 'Add source-specific details')
        structured_url = correction_url + '?kind=mysteries&structured=1'
        self.assertContains(self.client.get(structured_url), 'name="detail_mystery_level"')
        response = self.client.post(structured_url, {
            'kind': 'mysteries', 'rulebook': self.book.pk, 'name': entry.name,
            'mechanics': entry.mechanics, 'source_reference': 'Test Source p. 12, D&D 3.5',
            **self._typed_data('mysteries'),
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(MysteryDetail.objects.filter(entry=entry).exists())
        proposal = EditorialProposal.objects.get(action='correct')
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(reverse('editorial_review', args=(proposal.pk,))),
                            'Mystery level')
        self.client.post(reverse('editorial_decide', args=(proposal.pk,)), {'decision': 'approve'})
        entry.refresh_from_db()
        self.assertEqual(entry.get_absolute_url(), original_url)
        self.assertEqual(entry.category, 'Old category')
        self.assertEqual(entry.mystery_detail.mystery_level, 1)

    def test_psionic_class_levels_filter_review_and_translation(self):
        self.client.force_login(self.editor)
        url = reverse('editorial_create', args=('SupplementalEntry',)) + '?kind=psionics'
        data = {'kind': 'psionics', 'rulebook': self.book.pk, 'name': 'Mind Eye',
                'mechanics': 'A verified effect', 'detail_range': 'Close',
                'source_reference': 'Test Source p. 10, D&D 3.5',
                **self._typed_data('psionics')}
        self.assertEqual(self.client.post(url, data).status_code, 302)
        proposal = EditorialProposal.objects.get()
        self.assertEqual(proposal.status, 'pending')
        self.assertFalse(SupplementalEntry.objects.exists())
        self.client.force_login(self.owner)
        review = self.client.get(reverse('editorial_review', args=(proposal.pk,)))
        self.assertContains(review, 'Discipline')
        self.assertContains(review, 'Test Class | 1')
        self.client.post(reverse('editorial_decide', args=(proposal.pk,)), {'decision': 'approve'})
        entry = SupplementalEntry.objects.get()
        self.assertEqual(list(entry.psionic_detail.class_levels.values_list('character_class_id', 'level')),
                         [(self.test_class.pk, 1)])
        self.assertContains(self.client.get(entry.get_absolute_url()), 'Clairsentience')
        self.assertContains(self.client.get(reverse('supplemental_index', args=('psionics',)),
                                            {'discipline': 'Clairsentience'}), 'Mind Eye')
        self.assertNotContains(self.client.get(reverse('supplemental_index', args=('psionics',)),
                                               {'discipline': 'Telepathy'}), 'Mind Eye')
        self.assertContains(self.client.get(reverse('supplemental_index', args=('psionics',)),
                                            {'class_levels': self.test_class.pk, 'page_size': 5000}), 'Mind Eye')
        self.assertContains(self.client.get('/pt-br' + entry.get_absolute_url()),
                            'Este registro ainda está disponível apenas na versão original em inglês.')
        from dnd.editorial import source_digest, translatable_fields
        translations = {name: 'PT ' + str(value) for name, value in translatable_fields(entry).items()}
        self.client.force_login(self.editor)
        self.assertEqual(self.client.post(reverse('editorial_translate', args=('SupplementalEntry', entry.pk)),
                                          translations | {'source_reference': 'Reviewed translation'}).status_code, 302)
        translation_proposal = EditorialProposal.objects.get(action='translate')
        self.client.force_login(self.owner)
        self.client.post(reverse('editorial_decide', args=(translation_proposal.pk,)),
                         {'decision': 'approve'})
        self.assertContains(self.client.get('/pt-br' + entry.get_absolute_url()), 'PT Close')
        digest = source_digest(entry)
        entry.psionic_detail.range = 'Medium'
        entry.psionic_detail.save()
        self.assertNotEqual(source_digest(entry), digest)
        self.assertContains(self.client.get('/pt-br' + entry.get_absolute_url()),
                            'Este registro ainda está disponível apenas na versão original em inglês.')

    def test_core_spell_feat_and_monster_can_be_added_through_review(self):
        school = SpellSchool.objects.create(name='Evocation', slug='evocation')
        category = FeatCategory.objects.create(name='General', slug='general')
        monster_type = MonsterType.objects.create(name='Aberration', slug='aberration')
        size = RaceSize.objects.create(name='Medium', order=5)
        for resource, values, model in (
            ('Spell', {'name': 'Reviewed Spell', 'school': school.pk,
                       'description': 'A verified spell effect.'}, Spell),
            ('Feat', {'name': 'Reviewed Feat', 'feat_categories': [category.pk],
                      'description': 'A verified feat.', 'benefit': 'A useful benefit.'}, Feat),
            ('Monster', {'name': 'Reviewed Monster', 'size': size.pk, 'type': monster_type.pk,
                         'hit_dice': '1d8 (4 hp)', 'initiative': 0,
                         'armor_class': '10', 'base_attack': 0, 'grapple': 0,
                         'attack': 'Claw +0 (1d4)', 'full_attack': 'Claw +0 (1d4)',
                         'space': 5, 'reach': 5, 'fort_save': 0, 'reflex_save': 0,
                         'will_save': 0, 'str': 10, 'dex': 10, 'con': 10,
                         'int': 10, 'wis': 10, 'cha': 10, 'challenge_rating': 1}, Monster),
        ):
            with self.subTest(resource=resource):
                self.client.force_login(self.owner)
                response = self.client.post(reverse('editorial_create', args=(resource,)), {
                    'rulebook': self.book.pk, 'source_reference': 'Test Source p. 42, D&D 3.5',
                    **values,
                })
                self.assertEqual(response.status_code, 302, response.context and response.context['form'].errors)
                self.assertFalse(model.objects.exists())
                proposal = EditorialProposal.objects.filter(resource=resource).latest('pk')
                self.client.post(reverse('editorial_decide', args=(proposal.pk,)),
                                 {'decision': 'approve'})
                self.assertEqual(model.objects.count(), 1)
                self.assertContains(self.client.get(model.objects.get().get_absolute_url()), values['name'])

    def test_creature_template_can_be_proposed_and_approved(self):
        EditorialGrant.objects.create(user=self.editor, resource='CreatureTemplate', can_create=True)
        self.client.force_login(self.editor)
        response = self.client.post(reverse('editorial_create', args=('CreatureTemplate',)), {
            'rulebook': self.book.pk, 'page': 31, 'name': 'Sample Creature Template',
            'kind': 'acquired', 'applicable_creatures': 'Living creatures',
            'challenge_rating_adjustment': '+1', 'level_adjustment': '+2',
            'mechanical_changes': 'Verified 3.5 rules',
            'source_reference': 'Test Source p. 31, D&D 3.5',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CreatureTemplate.objects.exists())
        self.client.force_login(self.owner)
        proposal = EditorialProposal.objects.get(resource='CreatureTemplate')
        self.client.post(reverse('editorial_decide', args=(proposal.pk,)), {'decision': 'approve'})
        entry = CreatureTemplate.objects.get()
        self.assertContains(self.client.get(entry.get_absolute_url()), entry.name)

    def test_correction_stays_private_until_approved(self):
        entry = SupplementalEntry.objects.create(kind='invocations', rulebook=self.book,
                                                 name='Original Invocation', slug='original-invocation',
                                                 mechanics='Original mechanics')
        self.client.force_login(self.editor)
        response = self.client.post(reverse('editorial_correct', args=('SupplementalEntry', entry.pk)) +
                                    '?kind=invocations', {
            'kind': 'invocations', 'rulebook': self.book.pk,
            'name': entry.name, 'mechanics': 'Corrected mechanics',
            'source_reference': 'Test Source p. 42, erratum',
        })
        self.assertEqual(response.status_code, 302)
        entry.refresh_from_db()
        self.assertEqual(entry.mechanics, 'Original mechanics')
        self.client.force_login(self.owner)
        proposal = EditorialProposal.objects.get(action='correct')
        self.assertEqual(self.client.post(reverse('editorial_decide', args=(proposal.pk,)),
                                          {'decision': 'approve'}).status_code, 302)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, 'approved')
        entry.refresh_from_db()
        self.assertEqual(entry.mechanics, 'Corrected mechanics')
        self.assertContains(self.client.get(entry.get_absolute_url()), 'Corrected mechanics')

        self.client.force_login(self.editor)
        self.assertEqual(self.client.post(reverse('editorial_correct', args=('SupplementalEntry', entry.pk)) +
                                          '?kind=invocations', {
            'kind': 'invocations', 'rulebook': self.book.pk,
            'name': entry.name, 'mechanics': 'Stale proposal',
            'source_reference': 'Test Source p. 42, later erratum',
        }).status_code, 302)
        stale = EditorialProposal.objects.filter(status='pending').get()
        entry.mechanics = 'Newer correction'
        entry.save()
        self.client.force_login(self.owner)
        self.client.post(reverse('editorial_decide', args=(stale.pk,)), {'decision': 'approve'})
        stale.refresh_from_db()
        entry.refresh_from_db()
        self.assertEqual(stale.status, 'pending')
        self.assertEqual(entry.mechanics, 'Newer correction')

    def test_removal_requires_grant_and_owner_review(self):
        entry = SupplementalEntry.objects.create(kind='auras', rulebook=self.book,
                                                 name='Incorrect Aura', slug='incorrect-aura',
                                                 mechanics='Incorrect effect')
        url = reverse('editorial_delete', args=('SupplementalEntry', entry.pk)) + '?kind=auras'
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(url).status_code, 403)
        grant = EditorialGrant.objects.get(user=self.editor, resource='SupplementalEntry')
        grant.can_delete = True
        grant.save(update_fields=('can_delete',))
        self.assertContains(self.client.get(url), 'The record will stay public')
        self.assertEqual(self.client.post(url, {'source_reference': 'Test Source p. 1, erratum'}).status_code, 302)
        proposal = EditorialProposal.objects.get(action='delete')
        from dnd.editorial import source_digest
        PublishedTranslation.objects.create(
            resource='SupplementalEntry', target_pk=entry.pk, locale='pt-br',
            payload={'name': 'Aura Incorreta'}, source_digest=source_digest(entry, translation=True),
            author=self.editor, reviewer=self.owner)
        self.assertEqual(proposal.payload, {})
        self.assertTrue(SupplementalEntry.objects.filter(pk=entry.pk).exists())
        self.assertEqual(self.client.post(reverse('editorial_decide', args=(proposal.pk,)),
                                          {'decision': 'approve'}).status_code, 403)
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(reverse('editorial_review', args=(proposal.pk,))),
                            'Approve and remove')
        self.assertEqual(self.client.post(reverse('editorial_decide', args=(proposal.pk,)),
                                          {'decision': 'approve'}).status_code, 302)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, 'approved')
        self.assertFalse(SupplementalEntry.objects.filter(pk=entry.pk).exists())
        self.assertFalse(PublishedTranslation.objects.filter(
            resource='SupplementalEntry', target_pk=entry.pk).exists())

    def test_removal_blocks_cascading_prerequisite_links(self):
        required = Feat.objects.create(rulebook=self.book, name='Required Feat',
                                       slug='required-feat', description='Rule', benefit='Benefit')
        dependent = Feat.objects.create(rulebook=self.book, name='Dependent Feat',
                                        slug='dependent-feat', description='Rule', benefit='Benefit')
        link = FeatRequiresFeat.objects.create(source_feat=dependent, required_feat=required)
        self.client.force_login(self.owner)
        self.client.post(reverse('editorial_delete', args=('Feat', required.pk)),
                         {'source_reference': 'Test Source p. 3, erratum'})
        proposal = EditorialProposal.objects.get(action='delete')
        self.client.post(reverse('editorial_decide', args=(proposal.pk,)), {'decision': 'approve'})
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, 'pending')
        self.assertTrue(Feat.objects.filter(pk=required.pk).exists())
        self.assertTrue(FeatRequiresFeat.objects.filter(pk=link.pk).exists())

    def test_removal_rejects_stale_and_linked_records(self):
        entry = SupplementalEntry.objects.create(kind='auras', rulebook=self.book,
                                                 name='Linked Aura', slug='linked-aura',
                                                 mechanics='Original effect')
        self.client.force_login(self.owner)
        url = reverse('editorial_delete', args=('SupplementalEntry', entry.pk))
        self.client.post(url, {'source_reference': 'Test Source p. 2, erratum'})
        proposal = EditorialProposal.objects.get(action='delete')
        entry.mechanics = 'Corrected after proposal'
        entry.save()
        self.client.post(reverse('editorial_decide', args=(proposal.pk,)), {'decision': 'approve'})
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, 'pending')
        self.assertTrue(SupplementalEntry.objects.filter(pk=entry.pk).exists())

        book_url = reverse('editorial_delete', args=('Rulebook', self.book.pk))
        self.client.post(book_url, {'source_reference': 'Test Source p. 2, erratum'})
        book_proposal = EditorialProposal.objects.get(action='delete', resource='Rulebook')
        self.client.post(reverse('editorial_decide', args=(book_proposal.pk,)), {'decision': 'approve'})
        book_proposal.refresh_from_db()
        self.assertEqual(book_proposal.status, 'pending')
        self.assertTrue(Rulebook.objects.filter(pk=self.book.pk).exists())

    def test_additional_mechanic_grant_is_limited_to_selected_kind(self):
        limited = User.objects.create_user('aura-editor', 'aura@example.test',
                                           'long-test-password-123', is_staff=True)
        EditorialGrant.objects.create(user=limited, resource='SupplementalEntry:auras',
                                      can_create=True)
        self.client.force_login(limited)
        dashboard = self.client.get(reverse('editorial_dashboard'))
        self.assertContains(dashboard, 'Additional D&D 3.5 mechanics')
        self.assertNotContains(dashboard, 'href="' + reverse('editorial_catalog', args=('SupplementalEntry',)) + '"')
        self.assertEqual(self.client.get(reverse('editorial_catalog', args=('SupplementalEntry',)) +
                                         '?kind=auras').status_code, 200)
        self.assertEqual(self.client.get(reverse('editorial_catalog', args=('SupplementalEntry',)) +
                                         '?kind=psionics').status_code, 403)
        self.assertEqual(self.client.get(reverse('editorial_create', args=('SupplementalEntry',)) +
                                         '?kind=psionics').status_code, 403)
        self.assertEqual(self.client.get(reverse('editorial_create', args=('SupplementalEntry',))
                                         ).status_code, 403)
        response = self.client.post(reverse('editorial_create', args=('SupplementalEntry',)) +
                                    '?kind=auras', {
            'kind': 'auras', 'rulebook': self.book.pk, 'name': 'Granted Aura',
            'mechanics': 'Official 3.5 effect',
            'source_reference': 'Test Source p. 18, D&D 3.5',
            **self._typed_data('auras'),
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(EditorialProposal.objects.get().payload['kind'], 'auras')

    def test_same_name_in_different_mechanic_types_gets_distinct_slugs(self):
        self.client.force_login(self.owner)
        for kind in ('auras', 'mysteries'):
            response = self.client.post(reverse('editorial_create', args=('SupplementalEntry',)) +
                                        '?kind=' + kind, {
                'kind': kind, 'rulebook': self.book.pk, 'name': 'Shared Effect',
                'mechanics': 'Official 3.5 effect',
                'source_reference': 'Test Source p. 18, D&D 3.5',
                **self._typed_data(kind),
            })
            self.assertEqual(response.status_code, 302)
            proposal = EditorialProposal.objects.latest('pk')
            self.assertEqual(self.client.post(reverse('editorial_decide', args=(proposal.pk,)),
                                              {'decision': 'approve'}).status_code, 302)
        self.assertEqual(set(SupplementalEntry.objects.values_list('slug', flat=True)),
                         {'shared-effect', 'shared-effect-2'})

    def test_every_editorial_resource_has_a_renderable_create_form(self):
        self.client.force_login(self.owner)
        self.assertEqual(set(RESOURCE_LABELS), RESOURCES)
        for resource in sorted(RESOURCES):
            with self.subTest(resource=resource):
                self.assertFalse(set(editable_form(resource)().fields) - set(FIELD_LABELS))
                self.assertEqual(self.client.get(reverse('editorial_catalog', args=(resource,))).status_code, 200)
                self.assertEqual(self.client.get(reverse('editorial_create', args=(resource,))).status_code, 200)

    def test_portuguese_editorial_navigation_forms_and_login(self):
        self.client.force_login(self.owner)
        dashboard_url = reverse('editorial_dashboard')
        response = self.client.get(reverse('switch_language'), {
            'language': 'pt-br', 'next': dashboard_url,
        })
        self.assertEqual(response['Location'], dashboard_url)
        dashboard = self.client.get(dashboard_url)
        self.assertEqual(dashboard['Content-Language'], 'pt-br')
        self.assertContains(dashboard, 'Área editorial')
        self.assertContains(dashboard, 'Colaborações pendentes: 0')
        self.assertContains(dashboard, 'Talentos dos monstros')
        self.assertContains(self.client.get(reverse('editorial_create', args=('CreatureTemplate',))),
                            'Alterações mecânicas')
        self.client.logout()
        self.client.get(reverse('switch_language'), {
            'language': 'pt-br', 'next': reverse('admin:login'),
        })
        login_page = self.client.get(reverse('admin:login'))
        self.assertEqual(login_page.status_code, 200)
        self.assertEqual(login_page['Content-Language'], 'pt-br')
        self.assertContains(login_page, 'Administração do catálogo')
        self.assertContains(login_page, 'Entrar')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_invitation_activation_and_revocation(self):
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(reverse('editorial_invite')).status_code, 403)
        self.client.force_login(self.owner)
        response = self.client.post(reverse('editorial_invite'), {
            'email': 'friend@example.test', 'resources': ['Spell', 'CreatureTemplate'],
            'permissions': ['create', 'correct', 'translate'],
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['friend@example.test'])
        code = mail.outbox[0].body.split('Código do convite (válido por 7 dias): ')[1].splitlines()[0]
        self.assertNotIn(code, response.content.decode())
        record = CollaboratorInvite.objects.get()
        self.assertFalse(record.user.is_active)
        self.assertFalse(record.user.has_usable_password())
        self.assertEqual(EditorialGrant.objects.filter(user=record.user).count(), 2)

        self.client.logout()
        with override_settings(ACCESS_REQUIRED=True), patch(
                'dnd.access.verified_email', return_value='friend@example.test'):
            self.assertRedirects(self.client.get(reverse('admin:index')),
                                 reverse('editorial_activate'), fetch_redirect_response=False)
            self.assertEqual(self.client.get(reverse('editorial_activate')).status_code, 200)
            self.assertEqual(self.client.post(reverse('editorial_activate'),
                                              {'code': 'incorrect'}).status_code, 200)
            self.assertNotIn('_auth_user_id', self.client.session)
            self.assertEqual(self.client.post(reverse('editorial_activate'), {'code': code}).status_code, 302)
            self.assertEqual(self.client.get(reverse('editorial_dashboard')).status_code, 200)
        record.refresh_from_db()
        record.user.refresh_from_db()
        self.assertEqual(record.access_state, 'active')
        self.assertEqual(record.token_hash, '')
        self.assertTrue(record.user.is_active)
        self.assertFalse(record.user.has_usable_password())

        self.client.logout()
        with override_settings(ACCESS_REQUIRED=True), patch(
                'dnd.access.verified_email', return_value='friend@example.test'):
            self.assertEqual(self.client.get(reverse('editorial_dashboard')).status_code, 200)
            self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)

        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(reverse('editorial_revoke', args=(record.pk,))).status_code, 302)
        record.refresh_from_db()
        record.user.refresh_from_db()
        self.assertEqual(record.access_state, 'revoked')
        self.assertFalse(record.user.is_active)
        self.client.logout()
        with override_settings(ACCESS_REQUIRED=True), patch(
                'dnd.access.verified_email', return_value='friend@example.test'):
            self.assertEqual(self.client.get(reverse('editorial_dashboard')).status_code, 403)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_invitation_send_failure_rolls_back_and_pending_can_be_resent(self):
        self.client.force_login(self.owner)
        data = {'email': 'friend@example.test', 'resources': ['Spell'],
                'permissions': ['create']}
        with patch('dnd.editorial_views.send_mail', side_effect=smtplib.SMTPException('offline')):
            response = self.client.post(reverse('editorial_invite'), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email='friend@example.test').exists())
        self.assertFalse(CollaboratorInvite.objects.exists())

        self.assertEqual(self.client.post(reverse('editorial_invite'), data).status_code, 302)
        original = mail.outbox[-1].body
        before = CollaboratorInvite.objects.get(user__email='friend@example.test')
        digest = before.token_hash
        data['resources'] = ['Feat']
        with patch('dnd.editorial_views.send_mail', side_effect=smtplib.SMTPException('offline')):
            self.assertEqual(self.client.post(reverse('editorial_invite'), data).status_code, 200)
        before.refresh_from_db()
        self.assertEqual(before.token_hash, digest)
        self.assertEqual(list(EditorialGrant.objects.filter(user=before.user).values_list('resource', flat=True)),
                         ['Spell'])
        self.assertEqual(self.client.post(reverse('editorial_invite'), data).status_code, 302)
        self.assertNotEqual(original, mail.outbox[-1].body)
        record = CollaboratorInvite.objects.get(user__email='friend@example.test')
        self.assertEqual(list(EditorialGrant.objects.filter(user=record.user).values_list('resource', flat=True)),
                         ['Feat'])

    def test_access_members_omit_expired_and_revoked_invitations(self):
        from django.utils import timezone as django_timezone
        person = User.objects.create_user('pending-editor', 'pending@example.test', is_staff=True,
                                          is_active=False)
        record = CollaboratorInvite.objects.create(
            user=person, expires_at=django_timezone.now() - timedelta(seconds=1))
        output = StringIO()
        call_command('access_group_members', stdout=output)
        self.assertNotIn(person.email, json.loads(output.getvalue())['emails'])
        record.expires_at = django_timezone.now() + timedelta(days=1)
        record.save(update_fields=('expires_at',))
        output = StringIO()
        call_command('access_group_members', stdout=output)
        self.assertIn(person.email, json.loads(output.getvalue())['emails'])
        record.access_state = 'revoked'
        record.save(update_fields=('access_state',))
        output = StringIO()
        call_command('access_group_members', stdout=output)
        self.assertNotIn(person.email, json.loads(output.getvalue())['emails'])

    def test_expired_invitation_shows_recovery_instead_of_password_login(self):
        from django.utils import timezone as django_timezone

        person = User.objects.create_user('pending-editor', 'pending@example.test', is_staff=True,
                                          is_active=False)
        CollaboratorInvite.objects.create(user=person,
                                          expires_at=django_timezone.now() - timedelta(seconds=1))
        with override_settings(ACCESS_REQUIRED=True), patch(
                'dnd.access.verified_email', return_value=person.email):
            self.assertRedirects(self.client.get(reverse('admin:index')),
                                 reverse('editorial_activate'), fetch_redirect_response=False)
            response = self.client.get(reverse('editorial_activate'))
        self.assertContains(response, 'This invitation has expired')
        self.assertNotContains(response, 'name="code"')

    def test_access_identity_does_not_sign_in_uninvited_staff(self):
        with override_settings(ACCESS_REQUIRED=True), patch(
                'dnd.access.verified_email', return_value=self.editor.email):
            self.assertEqual(self.client.get(reverse('editorial_dashboard')).status_code, 403)

    def test_access_identity_does_not_sign_in_ambiguous_email(self):
        from django.utils import timezone as django_timezone

        person = User.objects.create_user('invited-editor', 'shared@example.test', is_staff=True)
        CollaboratorInvite.objects.create(user=person, access_state='active',
                                          expires_at=django_timezone.now() + timedelta(days=1))
        User.objects.create_user('other-editor', 'shared@example.test', is_staff=True)
        with override_settings(ACCESS_REQUIRED=True), patch(
                'dnd.access.verified_email', return_value='shared@example.test'):
            self.assertEqual(self.client.get(reverse('editorial_dashboard')).status_code, 403)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_owner_still_uses_django_password_after_cloudflare_access(self):
        with override_settings(ACCESS_REQUIRED=True), patch(
                'dnd.access.verified_email', return_value=self.owner.email):
            response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin:login'), response['Location'])

    def test_admin_session_must_match_signed_access_identity(self):
        self.client.force_login(self.owner)
        with override_settings(ACCESS_REQUIRED=True), patch(
                'dnd.access.verified_email', return_value='somebody@example.test'):
            response = self.client.get(reverse('editorial_dashboard'))
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_access_identity_requires_valid_signature_issuer_audience_and_expiry(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        issuer = 'https://test.cloudflareaccess.com'
        audience = 'test-application-aud'
        claims = {'email': 'Editor@Example.Test', 'iss': issuer, 'aud': audience,
                  'exp': datetime.now(timezone.utc) + timedelta(minutes=5)}
        with override_settings(ACCESS_TEAM_DOMAIN=issuer, ACCESS_AUD=[audience, 'second-host-aud']), patch(
                'dnd.access._jwk_client') as client:
            client.return_value.get_signing_key_from_jwt.return_value.key = private_key.public_key()
            token = jwt.encode(claims, private_key, algorithm='RS256')
            self.assertEqual(verified_email(token), 'editor@example.test')
            self.assertEqual(verified_email(jwt.encode(
                claims | {'aud': 'second-host-aud'}, private_key, algorithm='RS256')),
                'editor@example.test')
            for changes in ({'aud': 'different-app'}, {'iss': 'https://other.cloudflareaccess.com'},
                            {'exp': datetime.now(timezone.utc) - timedelta(minutes=1)}):
                self.assertIsNone(verified_email(jwt.encode(
                    claims | changes, private_key, algorithm='RS256')))
            other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            self.assertIsNone(verified_email(jwt.encode(claims, other_key, algorithm='RS256')))

    def test_portuguese_route_switch_translation_and_bilingual_search(self):
        self.assertEqual(self.client.get('/', HTTP_ACCEPT_LANGUAGE='pt-BR,pt;q=0.9')['Location'], '/pt-br/')
        home = self.client.get('/pt-br/')
        self.assertEqual(home.content.decode().count(
            'Explore magias, talentos, classes e livros em um catálogo pesquisável para aventureiros de mesa.'), 1)
        self.assertEqual(home.content.decode().count(
            'Uma referência mantida pela comunidade para aventureiros de RPG de mesa.'), 1)
        self.assertContains(home, 'Explore os mundos da 3.5')
        self.assertContains(self.client.get('/pt-br' + reverse('rule_condition_list')),
                            'Nenhuma condição disponível.')
        self.assertContains(self.client.get('/pt-br/contacts/'), 'Entre em contato com o projeto')
        self.assertContains(self.client.get('/pt-br/contacts/staff/'), 'Ronassic mantém este fork')
        response = self.client.get(reverse('switch_language'), {
            'language': 'pt-br', 'next': '/reference/mysteries/?q=arcane',
        })
        self.assertEqual(response['Location'], '/pt-br/reference/mysteries/?q=arcane')
        self.assertEqual(response.cookies[settings.LANGUAGE_COOKIE_NAME].value, 'pt-br')
        self.assertEqual(self.client.get(reverse('switch_language'), {
            'language': 'en-us', 'next': 'https://evil.example/',
        })['Location'], '/')

        entry = SupplementalEntry.objects.create(kind='mysteries', rulebook=self.book,
                                                  name='Shadow Gift', slug='shadow-gift',
                                                  mechanics='Original effect')
        from dnd.editorial import source_digest
        PublishedTranslation.objects.create(
            resource='SupplementalEntry', target_pk=entry.pk, locale='pt-br',
            payload={'name': 'Dom da Sombra', 'mechanics': 'Efeito traduzido'},
            source_digest=source_digest(entry, translation=True), author=self.editor, reviewer=self.owner)
        english = self.client.get(entry.get_absolute_url())
        self.assertContains(english, 'Shadow Gift')
        self.assertNotContains(english, 'Dom da Sombra')
        portuguese = self.client.get('/pt-br' + entry.get_absolute_url())
        self.assertContains(portuguese, 'Dom da Sombra')
        self.assertContains(portuguese, 'Efeito traduzido')
        self.assertContains(portuguese, 'Shadow Gift')
        self.assertNotContains(portuguese, 'still available only')
        search = self.client.get('/pt-br/search/?q=dom+da+sombra')
        self.assertContains(search, 'Dom da Sombra')
        self.assertContains(search, 'Shadow Gift')

        entry.mechanics = 'New original effect'
        entry.save()
        fallback = self.client.get('/pt-br' + entry.get_absolute_url())
        self.assertContains(fallback, 'Este registro ainda está disponível')
        self.assertEqual(fallback.content.decode().count(
            'Este registro ainda está disponível apenas na versão original em inglês.'), 1)
        self.assertNotContains(fallback, 'Efeito traduzido')
