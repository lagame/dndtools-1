from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import csv
import json
import smtplib
from io import StringIO
from threading import Barrier

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from django.conf import settings
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission
from django.core import mail
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connections, transaction
from django.test import Client, TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.urls import reverse

from dnd.editorial import RESOURCES, RESOURCE_LABELS, FIELD_LABELS, editable_form, approve
from dnd.access import verified_email
from dnd.supplemental.catalog import detail_for
from dnd.models import (CatalogImportBatch, CharacterClass, CollaboratorInvite, CreatureTemplate, DndEdition, EditorialGrant,
                        EditorialProposal, Feat, FeatCategory, FeatRequiresFeat, Monster, MonsterType, MysteryDetail, PublishedTranslation,
                        RaceSize, Rulebook, Spell, SpellSchool, SupplementalEntry)


class EditorialFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_superuser(settings.ADMINS[0][0], settings.ADMINS[0][1], 'long-test-password-123')
        cls.editor = User.objects.create_user('geeksublime', 'geeksublime@example.test',
                                              'long-test-password-123', is_staff=True)
        cls.edition = DndEdition.objects.create(name='Core 3.5', slug='core-35', system='DnD 3.5', core=True)
        cls.book = Rulebook.objects.create(name='Test Source', slug='test-source', abbr='TS',
                                            dnd_edition=cls.edition)
        cls.old_edition = DndEdition.objects.create(name='Core 3.0', slug='core-30', system='DnD 3.0', core=True)
        cls.old_book = Rulebook.objects.create(name='Old Source', slug='old-source', abbr='OS',
                                                dnd_edition=cls.old_edition)
        cls.test_class = CharacterClass.objects.create(name='Test Class', slug='test-class', prestige=False)
        cls.category = FeatCategory.objects.create(name='Import category', slug='import-category')
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
        self.assertContains(dashboard, '<p class="editorial-group-label">Additional D&amp;D 3.5 mechanics</p>',
                            html=True)
        self.assertNotContains(dashboard, 'href="' + reverse('editorial_catalog', args=('SupplementalEntry',)) + '"')
        self.assertContains(dashboard, reverse('editorial_create', args=('SupplementalEntry',)) + '?kind=auras')
        self.assertNotContains(dashboard, '?kind=psionics')
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
        forum_language = self.client.get(reverse('switch_language'), {
            'language': 'pt-br', 'next': '/forum/viewtopic.php?t=3',
        })
        self.assertEqual(forum_language['Location'], '/forum/viewtopic.php?t=3')
        self.assertEqual(forum_language.cookies[settings.LANGUAGE_COOKIE_NAME].value, 'pt-br')
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

    def _import_file(self, records, fields=None):
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=fields or
                                ['source_reference', 'name', 'rulebook', 'feat_categories', 'description', 'benefit'])
        writer.writeheader()
        writer.writerows(records)
        return SimpleUploadedFile('catalog.csv', output.getvalue().encode('utf-8'),
                                  content_type='text/csv')

    def _activate_importer(self, resource='Feat'):
        from django.utils import timezone as django_timezone
        CollaboratorInvite.objects.create(
            user=self.editor, access_state='active',
            expires_at=django_timezone.now() + timedelta(days=7))
        EditorialGrant.objects.update_or_create(
            user=self.editor, resource=resource,
            defaults={'can_create': True, 'can_import': True})

    def test_workspace_shows_only_allowed_import_and_proposal_actions(self):
        self._activate_importer()
        EditorialGrant.objects.create(user=self.editor, resource='Spell', can_create=True)
        self.client.force_login(self.editor)
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = 'pt-br'
        dashboard_url = reverse('editorial_dashboard')
        feat_import_url = reverse('editorial_import', args=('Feat',))
        dashboard = self.client.get(dashboard_url)
        self.assertContains(dashboard, '<h1>Área editorial</h1>', count=1, html=True)
        self.assertNotContains(dashboard, 'Importar registros diretamente')
        self.assertNotContains(dashboard, f'href="{feat_import_url}"')
        self.assertContains(dashboard, f'href="{reverse("editorial_create", args=("Spell",))}"')
        self.assertNotContains(dashboard, reverse('editorial_import', args=('Spell',)))
        self.assertNotContains(dashboard, reverse('editorial_catalog', args=('Monster',)))
        self.assertNotContains(dashboard, reverse('editorial_invite'))
        catalog = self.client.get(reverse('editorial_catalog', args=('Feat',)))
        self.assertContains(catalog, '<h1>Talentos</h1>', count=1, html=True)
        self.assertContains(catalog, 'Propor inclusão')
        self.assertNotContains(catalog, f'href="{feat_import_url}"')
        self.assertEqual(self.client.get(feat_import_url).status_code, 403)

    def test_matching_email_does_not_make_another_superuser_the_owner(self):
        from dnd.editorial import can_import

        other = User.objects.create_superuser('another-admin', settings.ADMINS[0][1])
        self.assertFalse(can_import(other, 'Item'))
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse('editorial_import', args=('Item',))).status_code, 403)

    def test_editorial_navigation_and_switch_account_in_both_languages(self):
        url = reverse('editorial_dashboard')
        switch_url = reverse('editorial_switch_account')
        self.client.force_login(self.owner)
        for language, title, label in (
                ('en-us', 'Editorial workspace', 'Sign out / switch account'),
                ('pt-br', 'Área editorial', 'Sair / trocar de conta')):
            with self.subTest(language=language):
                self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = language
                page = self.client.get(url)
                self.assertContains(page, '<h1>%s</h1>' % title, count=1, html=True)
                self.assertNotContains(page, '<div class="breadcrumbs">')
                self.assertContains(page, label)
                self.assertContains(page, 'action="%s"' % switch_url)
                self.assertContains(page, 'href="%s"' % reverse('admin:password_change'))
                self.assertContains(self.client.get(reverse('editorial_invite')), '<h1>', count=1)
        self.assertEqual(self.client.get(switch_url).status_code, 405)
        self.assertRedirects(self.client.post(switch_url), reverse('admin:login'),
                             fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)

    @override_settings(ACCESS_REQUIRED=True)
    def test_switch_account_also_ends_cloudflare_access_session(self):
        self.client.force_login(self.owner)
        with patch('dnd.access.verified_email', return_value=self.owner.email):
            response = self.client.post(reverse('editorial_switch_account'),
                                        HTTP_CF_ACCESS_JWT_ASSERTION='test-token')
        self.assertRedirects(response, '/cdn-cgi/access/logout', fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_json_resource_mismatch_stops_before_preview_in_both_languages(self):
        self.client.force_login(self.owner)
        url = reverse('editorial_import', args=('Spell',))
        record = {'resource': 'Feat', 'source_reference': 'Test Source, p. 5',
                  'name': 'Wrong importer', 'rulebook': self.book.name,
                  'feat_categories': self.category.name, 'description': 'Example.',
                  'benefit': 'Example.'}
        for language, message in (
                ('en-us', 'This file declares Feat, but this form imports Spell.'),
                ('pt-br', 'Este arquivo declara Feat, mas este formulário importa Spell.')):
            with self.subTest(language=language):
                self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = language
                upload = SimpleUploadedFile('feats.json', json.dumps([record]).encode())
                response = self.client.post(url, {'file': upload})
                self.assertContains(response, message)
                self.assertNotIn('editorial_import_preview', self.client.session)
        record.pop('resource')
        upload = SimpleUploadedFile('untyped.json', json.dumps([record]).encode())
        self.assertContains(self.client.post(url, {'file': upload}), 'deve declarar resource')
        self.assertFalse(Spell.objects.filter(name='Wrong importer').exists())

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                       EDITORIAL_NOTIFY_EMAIL='owner@example.test')
    def test_owner_csv_import_previews_then_publishes_with_audit_and_alert(self):
        url = reverse('editorial_import', args=('Feat',))
        record = {'source_reference': 'Test Source, p. 12', 'name': 'Careful Focus',
                  'rulebook': 'Test Source', 'feat_categories': 'Import category',
                  'description': 'A focused approach.',
                  'benefit': 'Gain a small bonus.'}
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(url).status_code, 403)
        self._activate_importer()
        self.assertEqual(self.client.get(url).status_code, 403)
        from dnd.editorial_import import publish_rows
        with self.assertRaises(PermissionDenied):
            publish_rows('[]', 'Feat', '', self.editor, json_file=True, expected_digest='unused')
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(url).status_code, 200)
        template = self.client.get(url + '?template=csv')
        self.assertEqual(template.status_code, 200)
        self.assertIn('source_reference', template.content.decode())
        self.assertNotIn('verified_author', template.content.decode())
        preview = self.client.post(url, {'file': self._import_file([record])})
        self.assertContains(preview, 'Careful Focus')
        self.assertFalse(Feat.objects.filter(name='Careful Focus').exists())
        token = self.client.session['editorial_import_preview']['token']
        self.assertEqual(self.client.post(url, {'confirm': '1', 'token': 'wrong'}).status_code, 200)
        self.assertFalse(Feat.objects.filter(name='Careful Focus').exists())
        self.assertEqual(self.client.post(url, {'confirm': '1', 'token': token}).status_code, 302)
        entry = Feat.objects.get(name='Careful Focus')
        self.assertEqual(entry.rulebook, self.book)
        proposal = EditorialProposal.objects.get(resource='Feat', target_pk=entry.pk)
        self.assertEqual((proposal.status, proposal.author, proposal.reviewer),
                         ('approved', self.owner, self.owner))
        self.assertEqual(proposal.source_reference, record['source_reference'])
        self.assertEqual(mail.outbox[-1].to, ['owner@example.test'])
        self.assertEqual(self.client.post(url, {'confirm': '1', 'token': token}).status_code, 200)
        self.assertEqual(Feat.objects.filter(name='Careful Focus').count(), 1)
        self.assertContains(self.client.post(url, {'file': self._import_file([record])}),
                            'already exists')

    def test_csv_import_rejects_wrong_edition_bad_source_and_uninvited_staff(self):
        from dnd.editorial_import import validated_rows
        url = reverse('editorial_import', args=('Feat',))
        self.client.force_login(self.editor)
        EditorialGrant.objects.create(user=self.editor, resource='Feat',
                                      can_create=True, can_import=True)
        self.assertEqual(self.client.get(url).status_code, 403)
        self._activate_importer()
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.owner)
        record = {'source_reference': 'Old Source p. 5', 'name': 'Old Trick',
                  'rulebook': str(self.old_book.pk), 'feat_categories': str(self.category.pk),
                  'description': 'Old.', 'benefit': 'Old.'}
        response = self.client.post(url, {'file': self._import_file([record])})
        self.assertContains(response, 'confirmed D&amp;D 3.5 rulebook')
        self.assertFalse(Feat.objects.exists())
        record['rulebook'] = str(self.book.pk)
        record['source_reference'] = 'x' * 2001
        with self.assertRaises(forms.ValidationError):
            validated_rows(self._import_file([record]).read().decode(), 'Feat', '')
        record['source_reference'] = 'Test Source p. 5'
        record['verified'] = 'true'
        with self.assertRaises(forms.ValidationError):
            validated_rows(self._import_file([record], fields=[
                'source_reference', 'name', 'rulebook', 'feat_categories',
                'description', 'benefit', 'verified']).read().decode(),
                'Feat', '')

    def test_csv_import_batch_is_atomic_on_late_failure(self):
        from dnd import editorial_import
        self._activate_importer()
        records = [
            {'source_reference': 'Test Source p. 5', 'name': 'First Trick',
             'rulebook': str(self.book.pk), 'feat_categories': str(self.category.pk),
             'description': 'First.', 'benefit': 'First.'},
            {'source_reference': 'Test Source p. 6', 'name': 'Second Trick',
             'rulebook': str(self.book.pk), 'feat_categories': str(self.category.pk),
             'description': 'Second.', 'benefit': 'Second.'},
        ]
        content = self._import_file(records).read().decode()
        digest = editorial_import.preview_digest(editorial_import.validated_rows(content, 'Feat', ''))
        real_publish = editorial_import.save_catalog_entry
        calls = 0

        def fail_second(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise forms.ValidationError('Simulated later failure')
            return real_publish(*args, **kwargs)

        with patch('dnd.editorial_import.save_catalog_entry', side_effect=fail_second):
            with self.assertRaisesMessage(forms.ValidationError, 'Simulated later failure'):
                editorial_import.publish_rows(content, 'Feat', '', self.owner, expected_digest=digest)
        self.assertFalse(Feat.objects.exists())
        self.assertFalse(EditorialProposal.objects.filter(resource='Feat').exists())

    def test_csv_import_typed_supplemental_entry(self):
        from dnd.models import MysteryDetail
        self._activate_importer('SupplementalEntry')
        self.client.force_login(self.owner)
        url = reverse('editorial_import', args=('SupplementalEntry',)) + '?kind=mysteries'
        record = {'source_reference': 'Test Source p. 18', 'name': 'Ebon Whispers',
                  'rulebook': str(self.book.pk), 'mechanics': 'A shadow effect.',
                  'kind': '', 'detail_path': 'Ebon Whispers', 'detail_grade': 'apprentice',
                  'detail_mystery_level': '1'}
        upload = self._import_file([record], fields=list(record))
        self.assertEqual(self.client.post(url, {'file': upload}).status_code, 200)
        token = self.client.session['editorial_import_preview']['token']
        response = self.client.post(url, {'confirm': '1', 'token': token})
        self.assertRedirects(response, reverse('editorial_catalog', args=('SupplementalEntry',))
                             + '?kind=mysteries')
        entry = SupplementalEntry.objects.get(name='Ebon Whispers')
        self.assertEqual(entry.kind, 'mysteries')
        self.assertEqual(MysteryDetail.objects.get(entry=entry).grade, 'apprentice')

    def test_import_examples_and_submission_in_both_csv_formats_and_json(self):
        from dnd.editorial import IMPORT_RESOURCES, model_for
        from dnd.editorial_import import DOWNLOAD_FORMATS

        SpellSchool.objects.create(name='Example school', slug='example-school')
        RaceSize.objects.create(name='Example size', order=1)
        MonsterType.objects.create(name='Example creature type', slug='example-type')
        CharacterClass.objects.create(name='Example class', slug='example-class', prestige=False)
        self.client.force_login(self.owner)
        url = reverse('editorial_import', args=('Feat',))
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = 'pt-br'
        page = self.client.get(url)
        self.assertContains(page, 'Baixar exemplo de CSV com vírgula')
        self.assertContains(page, 'Baixar exemplo de CSV com ponto e vírgula')
        self.assertContains(page, 'Baixar exemplo em JSON')
        resources = [(resource, '') for resource in sorted(IMPORT_RESOURCES - {'SupplementalEntry'})]
        resources += [('SupplementalEntry', kind) for kind, _ in SupplementalEntry.KINDS]
        for resource, kind in resources:
            url = reverse('editorial_import', args=(resource,), query={'kind': kind} if kind else None)
            for file_format, separator in DOWNLOAD_FORMATS.items():
                with self.subTest(resource=resource, kind=kind, file_format=file_format):
                    example = self.client.get(reverse('editorial_import', args=(resource,)),
                                              {'kind': kind, 'template': file_format})
                    self.assertEqual(example['Cache-Control'], 'no-store')
                    content = example.content.decode('utf-8-sig')
                    self.assertNotIn(self.book.name, content)
                    if separator:
                        self.assertIn(separator, content.splitlines()[0])
                        content = content.replace('Example feat category', self.category.name)
                    else:
                        content = content.replace('"Example feat category"', str(self.category.pk))
                    name = 'Imported %s %s' % (kind or resource, file_format)
                    content = (content.replace('Example record', name)
                               .replace('Example D&D 3.5 rulebook', self.book.name)
                               .replace('Example monster', 'Imported Monster csv'))
                    extension = 'csv' if separator else 'json'
                    response = self.client.post(url, {'file': SimpleUploadedFile(
                        'example.' + extension, content.encode('utf-8'))})
                    self.assertContains(response, 'Publicar 1 registro agora')
                    entries = model_for(resource).objects.filter(name=name)
                    self.assertFalse(entries.exists())
                    token = self.client.session['editorial_import_preview']['token']
                    self.assertEqual(self.client.post(url, {'confirm': '1', 'token': token}).status_code, 302)
                    entry = entries.get()
                    self.assertEqual(entry.rulebook, self.book)
                    if resource == 'Feat':
                        self.assertEqual(entry.feat_categories.get(), self.category)
                    elif resource == 'Spell':
                        self.assertTrue(entry.verbal_component)
                        self.assertFalse(entry.somatic_component)
                    elif kind:
                        self.assertEqual(entry.kind, kind)
                        self.assertIsNotNone(detail_for(entry))

    def test_import_enforces_access_and_csrf_and_escapes_preview(self):
        self._activate_importer()
        client = Client(enforce_csrf_checks=True)
        url = reverse('editorial_import', args=('Feat',))
        self.assertEqual(client.get(url, {'template': 'json'}).status_code, 302)
        client.force_login(self.owner)
        with override_settings(ACCESS_REQUIRED=True):
            self.assertEqual(client.get(url, {'template': 'json'}).status_code, 403)
        self.assertEqual(client.get(reverse('editorial_import', args=('Item',))).status_code, 200)
        client.get(url)
        record = {'source_reference': 'Test Source p. 5', 'name': 'CSRF Preview',
                  'rulebook': self.book.name, 'feat_categories': self.category.name,
                  'description': '<mark>Visible markup</mark>', 'benefit': 'Example.'}
        self.assertEqual(client.post(url, {'file': self._import_file([record])}).status_code, 403)
        response = client.post(url, {'file': self._import_file([record]),
                                    'csrfmiddlewaretoken': client.cookies[settings.CSRF_COOKIE_NAME].value})
        self.assertContains(response, '&lt;mark&gt;Visible markup&lt;/mark&gt;')
        self.assertEqual(response['Cache-Control'], 'no-store')
        token = client.session['editorial_import_preview']['token']
        self.assertEqual(client.post(url, {'confirm': '1', 'token': token}).status_code, 403)
        self.assertFalse(Feat.objects.filter(name=record['name']).exists())

    def test_import_rejects_files_and_batches_above_the_limits(self):
        from dnd.editorial_import import MAX_BYTES, MAX_MIB, MAX_ROWS, validated_rows
        self.assertRaisesMessage(forms.ValidationError, f'exceeds the {MAX_MIB} MiB limit.',
                                 validated_rows, ' ' * (MAX_BYTES + 1), 'Feat', '')
        record = {'source_reference': 'Test Source p. 5',
                  'rulebook': self.book.pk, 'feat_categories': [self.category.pk],
                  'description': 'Example.', 'benefit': 'Example.'}
        records = [dict(record, name='Batch feat %s' % index) for index in range(MAX_ROWS + 1)]
        with self.assertRaisesMessage(forms.ValidationError, f'Import at most {MAX_ROWS} records per file.'):
            validated_rows(json.dumps(records), 'Feat', '', json_file=True)
        self.assertFalse(Feat.objects.exists())

    def test_import_accepts_and_audits_a_batch_at_both_limits(self):
        from dnd.editorial_import import INLINE_BYTES, INLINE_ROWS

        self._activate_importer()
        self.client.force_login(self.owner)
        url = reverse('editorial_import', args=('Feat',))
        records = [{
            'resource': 'Feat', 'name': f'Batch Feat {index}', 'rulebook': self.book.pk,
            'feat_categories': [self.category.pk], 'source_reference': 'Test Source p. 12',
            'description': 'Example rule. ' * 280, 'benefit': 'Example benefit.',
        } for index in range(INLINE_ROWS)]
        content = json.dumps(records).encode('utf-8')
        self.assertGreater(len(content), INLINE_BYTES * 0.9)
        self.assertLess(len(content), INLINE_BYTES)
        content = content.ljust(INLINE_BYTES, b' ')
        upload = SimpleUploadedFile('batch.json', content, content_type='application/json')
        self.assertContains(self.client.post(url, {'file': upload}), f'Review {INLINE_ROWS} records before publishing')
        self.assertFalse(Feat.objects.exists())
        token = self.client.session['editorial_import_preview']['token']
        self.assertRedirects(self.client.post(url, {'confirm': '1', 'token': token}),
                             reverse('editorial_catalog', args=('Feat',)))
        self.assertEqual(Feat.objects.filter(name__startswith='Batch Feat ').count(), INLINE_ROWS)
        self.assertEqual(EditorialProposal.objects.filter(resource='Feat', status='approved',
                                                        author=self.owner).count(), INLINE_ROWS)

    def _queue_feat_file(self, record, *, pad=True):
        from dnd.editorial_import import INLINE_BYTES

        content = json.dumps([record]).encode('utf-8')
        if pad:
            content = content.ljust(INLINE_BYTES + 1, b' ')
        url = reverse('editorial_import', args=('Feat',))
        return self.client.post(url, {'file': SimpleUploadedFile('queued.json', content)})

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                       EDITORIAL_NOTIFY_EMAIL='owner@example.test')
    def test_large_job_resumes_and_publishes_once_after_confirmation(self):
        from dnd.editorial_batches import process_next_batch

        self._activate_importer()
        self.client.force_login(self.owner)
        record = {'resource': 'Feat', 'name': 'Queued feat', 'rulebook': self.book.pk,
                  'feat_categories': [self.category.pk], 'source_reference': 'Test Source p. 6',
                  'description': 'Example.', 'benefit': 'Example.'}
        response = self._queue_feat_file(record)
        batch = CatalogImportBatch.objects.get()
        status_url = reverse('editorial_import_batch', args=(batch.pk,))
        self.assertRedirects(response, status_url)
        self.assertEqual(self.client.get(status_url + '?status=1').json()['state'], 'queued')
        self.assertRedirects(self._queue_feat_file(dict(record, name='Second job')), status_url)
        self.assertEqual(CatalogImportBatch.objects.count(), 1)
        peer = Client()
        peer.force_login(self.editor)
        self.assertEqual(peer.get(status_url + '?status=1').status_code, 404)
        self.assertEqual(peer.post(status_url, {'action': 'confirm'}).status_code, 404)

        CatalogImportBatch.objects.filter(pk=batch.pk).update(state='validating')
        self.client.logout()
        self.assertTrue(process_next_batch())
        self.assertFalse(Feat.objects.exists())
        self.client.force_login(self.owner)
        page = self.client.get(status_url)
        self.assertContains(page, 'Queued feat')
        self.assertContains(page, 'Publish 1 record now')
        self.assertIn('no-store', page['Cache-Control'])
        for _ in range(2):
            self.assertRedirects(self.client.post(status_url, {'action': 'confirm'}), status_url)
        CatalogImportBatch.objects.filter(pk=batch.pk).update(state='publishing')
        self.assertTrue(process_next_batch())
        self.assertTrue(process_next_batch())  # Email is processed after the transaction commits.
        self.assertFalse(process_next_batch())
        batch.refresh_from_db()
        self.assertEqual(batch.state, 'published')
        self.assertFalse(batch.payload)
        self.assertFalse(batch.preview)
        self.assertEqual(Feat.objects.filter(name='Queued feat').count(), 1)
        self.assertEqual(EditorialProposal.objects.filter(author=self.owner, status='approved').count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_queued_import_stops_if_permission_changes_or_batch_is_cancelled(self):
        from dnd.editorial_batches import process_next_batch

        self._activate_importer()
        self.client.force_login(self.owner)
        record = {'resource': 'Feat', 'name': 'Queued feat', 'rulebook': self.book.pk,
                  'feat_categories': [self.category.pk], 'source_reference': 'Test Source p. 6',
                  'description': 'Example.', 'benefit': 'Example.'}
        response = self._queue_feat_file(record)
        self.assertRedirects(self.client.post(response.url, {'action': 'cancel'}), response.url)
        self.assertFalse(process_next_batch())
        self.assertTrue(CatalogImportBatch.objects.filter(state='cancelled', payload='').exists())
        self.assertEqual(self._queue_feat_file(record).status_code, 302)
        self.assertTrue(process_next_batch())
        batch = CatalogImportBatch.objects.get(state='ready')
        status_url = reverse('editorial_import_batch', args=(batch.pk,))
        self.assertRedirects(self.client.post(status_url, {'action': 'confirm'}), status_url)
        self.owner.email = 'former-owner@example.test'
        self.owner.save(update_fields=('email',))
        self.assertEqual(self.client.get(status_url + '?status=1').status_code, 403)
        self.assertTrue(process_next_batch())
        batch.refresh_from_db()
        self.assertEqual(batch.state, 'failed')
        self.assertFalse(batch.payload)
        self.assertFalse(Feat.objects.exists())
        self.assertFalse(EditorialProposal.objects.exists())

    def test_import_rejects_bad_json_and_incomplete_csv(self):
        from dnd.editorial_import import validated_rows
        for content in ('{}', '[123]', '[{"name":"one","name":"two"}]', '[{"name":NaN}]'):
            with self.subTest(content=content), self.assertRaises(forms.ValidationError):
                validated_rows(content, 'Feat', '', json_file=True)
        with self.assertRaisesMessage(forms.ValidationError, 'does not match the CSV header'):
            validated_rows('source_reference;name;rulebook\nSource;Only name', 'Feat', '')
        psionic = [{'resource': 'SupplementalEntry', 'source_reference': 'Test Source p. 5', 'name': 'Bad Level',
                    'rulebook': self.book.pk, 'mechanics': 'Example effect.',
                    'detail_discipline': 'Clairsentience', 'detail_power_points': 1,
                    'detail_class_levels': 'Test Class | ²'}]
        with self.assertRaisesMessage(forms.ValidationError, 'Use one class per line'):
            validated_rows(json.dumps(psionic), 'SupplementalEntry', 'psionics', json_file=True)

    def test_approved_spell_correction_still_records_verifier(self):
        school = SpellSchool.objects.create(name='Test School', slug='test-school')
        form = editable_form('Spell')({'rulebook': self.book.pk, 'school': school.pk,
                                       'name': 'Test Spell', 'description': 'Original text.'})
        self.assertTrue(form.is_valid(), form.errors)
        spell = form.save(commit=False)
        spell.slug = 'test-spell'
        spell.save()
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(reverse('editorial_correct', args=('Spell', spell.pk)), {
            'rulebook': self.book.pk, 'school': school.pk, 'name': spell.name,
            'description': 'Corrected text.', 'source_reference': 'Test Source, p. 7',
        }).status_code, 302)
        proposal = EditorialProposal.objects.get(resource='Spell', action='correct')
        self.assertEqual(self.client.post(reverse('editorial_decide', args=(proposal.pk,)),
                                          {'decision': 'approve'}).status_code, 302)
        spell.refresh_from_db()
        self.assertEqual(spell.description, 'Corrected text.')
        self.assertTrue(spell.verified)
        self.assertEqual(spell.verified_author_id, self.owner.pk)
        self.assertIsNotNone(spell.verified_time)

    def test_import_requires_fresh_preview_when_relation_changes(self):
        self._activate_importer()
        self.client.force_login(self.owner)
        url = reverse('editorial_import', args=('Feat',))
        record = {'source_reference': 'Test Source p. 5', 'name': 'Stale Preview',
                  'rulebook': self.book.name, 'feat_categories': self.category.name,
                  'description': 'Example.', 'benefit': 'Example.'}
        self.assertContains(self.client.post(url, {'file': self._import_file([record])}), 'Publish 1 record now')
        token = self.client.session['editorial_import_preview']['token']
        self.category.name = 'Renamed category'
        self.category.save(update_fields=['name'])
        FeatCategory.objects.create(name=record['feat_categories'], slug='replacement')
        response = self.client.post(url, {'confirm': '1', 'token': token})
        self.assertContains(response, 'Catalog values changed after the preview')
        self.assertFalse(Feat.objects.filter(name=record['name']).exists())

    def test_import_permission_is_checked_again_at_confirmation(self):
        self._activate_importer()
        self.client.force_login(self.owner)
        url = reverse('editorial_import', args=('Feat',))
        record = {'source_reference': 'Test Source p. 5', 'name': 'Revoked Import',
                  'rulebook': self.book.name, 'feat_categories': self.category.name,
                  'description': 'Example.', 'benefit': 'Example.'}
        self.assertContains(self.client.post(url, {'file': self._import_file([record])}), 'Publish 1 record now')
        token = self.client.session['editorial_import_preview']['token']
        self.owner.email = 'former-owner@example.test'
        self.owner.save(update_fields=('email',))
        self.assertEqual(self.client.post(url, {'confirm': '1', 'token': token}).status_code, 403)
        self.assertFalse(Feat.objects.filter(name=record['name']).exists())


class EditorialImportConcurrencyTests(TransactionTestCase):
    def test_inline_write_reports_contention_without_waiting_for_a_large_batch(self):
        from dnd.editorial import lock_creation_books

        edition = DndEdition.objects.create(name='Core 3.5', slug='core-35', system='DnD 3.5', core=True)
        book = Rulebook.objects.create(name='Example Source', slug='example-source', abbr='ES', dnd_edition=edition)

        def try_inline():
            try:
                with transaction.atomic():
                    lock_creation_books([book.pk], wait=False)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                lock_creation_books([book.pk])
                result = pool.submit(try_inline)
                with self.assertRaisesMessage(forms.ValidationError, 'Another batch is publishing'):
                    result.result(timeout=5)

    def test_two_confirmations_of_the_same_record_publish_only_once(self):
        from dnd import editorial_import

        editor = User.objects.create_superuser(settings.ADMINS[0][0], settings.ADMINS[0][1])
        edition = DndEdition.objects.create(name='Core 3.5', slug='core-35', system='DnD 3.5', core=True)
        book = Rulebook.objects.create(name='Example Source', slug='example-source', abbr='ES', dnd_edition=edition)
        category = FeatCategory.objects.create(name='Example category', slug='example-category')
        content = json.dumps([{'resource': 'Feat', 'source_reference': 'Example Source, p. 5', 'name': 'Concurrent Feat',
                               'rulebook': book.pk, 'feat_categories': [category.pk],
                               'description': 'Example.', 'benefit': 'Example.'}])
        rows = editorial_import.validated_rows(content, 'Feat', '', json_file=True)
        digest = editorial_import.preview_digest(rows)
        barrier = Barrier(2)
        lock_books = editorial_import.lock_creation_books

        def lock_after_both_validated(ids, *, wait=True):
            barrier.wait(timeout=10)
            lock_books(ids, wait=wait)

        def confirm():
            try:
                return editorial_import.publish_rows(content, 'Feat', '', editor,
                                                     json_file=True, expected_digest=digest)
            except forms.ValidationError as error:
                return '; '.join(error.messages)
            finally:
                connections.close_all()

        with patch.object(editorial_import, 'lock_creation_books', side_effect=lock_after_both_validated):
            with ThreadPoolExecutor(max_workers=2) as pool:
                pending = [pool.submit(confirm), pool.submit(confirm)]
                outcomes = [result.result(timeout=20) for result in pending]
        self.assertCountEqual(outcomes, [1, 'A catalog record with this original name already exists.'])
        self.assertEqual(Feat.objects.filter(name='Concurrent Feat').count(), 1)
        self.assertEqual(EditorialProposal.objects.filter(resource='Feat', status='approved').count(), 1)
