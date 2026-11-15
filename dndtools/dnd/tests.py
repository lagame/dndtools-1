from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from dnd.models import DndEdition, RuleCondition, Rulebook, Spell, SpellSchool


class CatalogSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        edition = DndEdition.objects.create(
            name='3.5 Core', system='DnD 3.5', slug='core-35', core=True)
        book = Rulebook.objects.create(
            dnd_edition=edition, name='Test Handbook', abbr='TH', slug='test-handbook')
        school = SpellSchool.objects.create(name='Evocation', slug='evocation')
        cls.spell = Spell.objects.create(
            rulebook=book, school=school, name='Arcane Ember', slug='arcane-ember',
            description='A small flame appears.', verbal_component=True,
            somatic_component=False, material_component=False,
            arcane_focus_component=False, divine_focus_component=False,
            xp_component=False, meta_breath_component=False, true_name_component=False,
        )

    def test_home_detail_and_first_party_search(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        detail = self.client.get(self.spell.get_absolute_url())
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, 'Arcane Ember')
        search = self.client.get(reverse('search'), {'q': 'Ember', 'category': 'spells'})
        self.assertEqual(search.status_code, 200)
        self.assertContains(search, self.spell.get_absolute_url())
        self.assertContains(search, 'Arcane Ember')
        self.assertContains(self.client.get(reverse('search'), {'q': 'no match'}), 'No matches')

    def test_old_mobile_detail_redirects_to_same_content(self):
        response = self.client.get('/m' + self.spell.get_absolute_url(), {'page': '2'})
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], self.spell.get_absolute_url() + '?page=2')

    def test_verification_requires_post_staff_and_csrf(self):
        url = reverse('spell_verify', kwargs={'spell_id': self.spell.id})
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.spell.refresh_from_db()
        self.assertFalse(self.spell.verified)

        staff = User.objects.create_user(username='editor', password='test-password', is_staff=True)
        client = Client(enforce_csrf_checks=True)
        client.force_login(staff)
        self.assertEqual(client.post(url).status_code, 403)
        detail = client.get(self.spell.get_absolute_url())
        self.assertEqual(detail.status_code, 200)
        token = client.cookies['csrftoken'].value
        response = client.post(url, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 301)
        self.spell.refresh_from_db()
        self.assertTrue(self.spell.verified)
        self.assertEqual(self.spell.verified_author, staff)

    def test_contact_uses_issue_flow_without_unconfigured_email(self):
        self.assertContains(self.client.get(reverse('contact')), 'Open a project issue')
        self.assertEqual(self.client.post(reverse('contact')).status_code, 405)
        self.assertEqual(self.client.post(reverse('inaccurate_content')).status_code, 405)

    def test_conditions_and_missing_legacy_android_page(self):
        condition = RuleCondition.objects.create(name='Dazed', description='Limited actions.')
        self.assertContains(self.client.get(reverse('rule_condition_list')), condition.get_absolute_url())
        self.assertContains(self.client.get(condition.get_absolute_url()), 'Limited actions.')
        self.assertContains(self.client.get(reverse('search'), {'q': 'Dazed'}), condition.get_absolute_url())
        self.assertContains(self.client.get(reverse('android')), 'not available in this catalog snapshot')
