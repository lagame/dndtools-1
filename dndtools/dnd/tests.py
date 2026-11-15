from io import BytesIO
from datetime import date
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.test.utils import override_settings
from django.urls import reverse

from dnd.models import (
    CharacterClass, DndEdition, Domain, Feat, FeatCategory, Race, RaceSize,
    NewsEntry, RuleCondition, Rulebook, Spell, SpellClassLevel, SpellDomainLevel, SpellSchool, StaticPage,
    TextFeatPrerequisite,
)
from dnd.templatetags.versioned_static import versioned_static


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

    def test_html_revalidates_and_asset_urls_change_with_content(self):
        response = self.client.get('/')
        self.assertEqual(response['Cache-Control'], 'no-cache, max-age=0, must-revalidate')
        for path in ('css/modern.css', 'css/identity.css', 'css/privacy.css', 'css/themes.css',
                     'js/theme.js', 'js/navigation.js', 'js/search_suggest.js', 'js/privacy_notice.js'):
            digest = sha256((Path(settings.STATIC_DIR) / path).read_bytes()).hexdigest()[:12]
            self.assertContains(response, '/static/%s?v=%s' % (path, digest))
        with TemporaryDirectory() as static_dir, override_settings(STATIC_DIR=static_dir, DEBUG=True):
            asset = Path(static_dir) / 'theme-check.css'
            asset.write_text('body { color: blue; }', encoding='utf-8')
            before = versioned_static(asset.name)
            asset.write_text('body { color: red; }', encoding='utf-8')
            self.assertNotEqual(before, versioned_static(asset.name))

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

    def test_privacy_notice_and_legacy_news_cookie(self):
        NewsEntry.objects.create(published=date(2026, 11, 15), title='Catalog update', body='Updated catalog.')
        home = self.client.get('/', HTTP_ACCEPT_LANGUAGE='pt-BR,pt;q=0.9')
        self.assertContains(home, 'Sua privacidade')
        self.assertContains(home, reverse('privacy'))
        self.assertNotIn('top_news', home.cookies)
        self.assertNotIn('sessionid', home.cookies)

        for name in ('top_news', 'disable_social', 'force_desktop'):
            self.client.cookies[name] = '1'
        response = self.client.get('/spells/')
        for name in ('top_news', 'disable_social', 'force_desktop'):
            self.assertEqual(int(response.cookies[name]['max-age']), 0)
        self.assertContains(self.client.get('/', HTTP_ACCEPT_LANGUAGE='en-US'), 'Your privacy')
        policy = self.client.get(reverse('privacy'))
        self.assertContains(policy, 'ronassic@gmail.com')
        self.assertContains(policy, 'dnd_privacy_notice_v1')
        self.assertContains(policy, 'dnd_theme_v2')
        self.assertContains(policy, 'Privacy at D&amp;D Tools')
        self.assertNotContains(policy, 'Privacidade no D&amp;D Tools')
        portuguese_policy = self.client.get(reverse('privacy'), {'lang': 'pt'})
        self.assertContains(portuguese_policy, 'Privacidade no D&amp;D Tools')
        self.assertNotContains(portuguese_policy, 'Privacy at D&amp;D Tools')

    def test_staff_page_shows_current_maintainer_without_legacy_staff(self):
        response = self.client.get(reverse('staff'))
        self.assertContains(response, 'Ronassic')
        self.assertContains(response, 'mailto:ronassic@gmail.com')
        self.assertContains(response, 'Maintainer')
        StaticPage.objects.create(name='staff', body='Outdated volunteer listing')
        self.assertNotContains(self.client.get(reverse('staff')), 'Outdated volunteer listing')

    def test_conditions_and_missing_legacy_android_page(self):
        condition = RuleCondition.objects.create(name='Dazed', description='Limited actions.')
        self.assertContains(self.client.get(reverse('rule_condition_list')), condition.get_absolute_url())
        self.assertContains(self.client.get(condition.get_absolute_url()), 'Limited actions.')
        self.assertContains(self.client.get(reverse('search'), {'q': 'Dazed'}), condition.get_absolute_url())
        self.assertContains(self.client.get(reverse('android')), 'not available in this catalog snapshot')

    def test_navigation_keeps_legacy_destinations_and_mobile_redirects(self):
        page = self.client.get('/spells/')
        self.assertContains(page, 'href="%s"' % reverse('admin:index'))
        self.assertContains(page, 'Admin login')
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 302)
        self.assertContains(page, reverse('feat_category_list'))
        self.assertContains(page, reverse('spell_school_list'))
        self.assertContains(page, reverse('race_type_index'))
        self.assertContains(page, reverse('spell_list_by_rulebook'))
        self.assertContains(page, reverse('skills_list_by_rulebook'))
        self.assertContains(page, 'Planned')
        self.assertEqual(self.client.get('/m/spells/by-rulebooks/')['Location'],
                         reverse('spell_list_by_rulebook'))
        self.assertEqual(self.client.get('/m/skills/by-rulebooks/')['Location'],
                         reverse('skills_list_by_rulebook'))

    def test_search_is_accent_insensitive_and_suggests_real_urls(self):
        spell = Spell.objects.create(
            rulebook=self.spell.rulebook, school=self.spell.school,
            name='Árcane Flame', slug='arcane-flame', description='A second flame.',
            verbal_component=True, somatic_component=False, material_component=False,
            arcane_focus_component=False, divine_focus_component=False, xp_component=False,
            meta_breath_component=False, true_name_component=False,
        )
        result = self.client.get(reverse('search'), {'q': 'arcane', 'category': 'spells'})
        self.assertContains(result, spell.get_absolute_url())
        self.assertContains(result, 'Test Handbook')
        suggestions = self.client.get(reverse('search_suggest'), {'q': 'arcane'})
        self.assertEqual(suggestions.status_code, 200)
        self.assertIn(spell.get_absolute_url(), [item['url'] for item in suggestions.json()['results']])
        self.assertEqual(self.client.get(reverse('search_suggest'), {'q': 'a'}).json(), {'results': []})
        self.assertEqual(self.client.get(reverse('search'), {'q': 'arcane', 'category': 'bogus'}).status_code, 400)

    def test_spell_class_and_level_use_the_same_link(self):
        wizard = CharacterClass.objects.create(name='Wizard', slug='wizard', prestige=False)
        cleric = CharacterClass.objects.create(name='Cleric', slug='cleric', prestige=False)
        SpellClassLevel.objects.create(spell=self.spell, character_class=wizard, level=0)
        SpellClassLevel.objects.create(spell=self.spell, character_class=cleric, level=1)
        params = {'name': 'Arcane Ember', 'class_levels__slug': 'wizard'}
        self.assertContains(self.client.get('/spells/', {**params, 'spellclasslevel__level': '0'}),
                            '1 spell found.')
        self.assertContains(self.client.get('/spells/', {**params, 'spellclasslevel__level': '1'}),
                            '0 spells found.')
        self.assertContains(self.client.get('/spells/', {'class_levels__slug': '__missing__'}),
                            '0 spells found.')
        invalid = self.client.get('/spells/', {'class_levels__slug': 'not-a-class'})
        self.assertEqual(invalid.status_code, 400)
        self.assertContains(invalid, 'could not be applied', status_code=400)

    def test_spell_filter_preserves_legacy_boolean_values(self):
        positive = self.client.get('/spells/', {'verbal_component': 'True'})
        self.assertContains(positive, '1 spell found.')
        negative = self.client.get('/spells/', {'verbal_component': 'False'})
        self.assertContains(negative, '0 spells found.')

    def test_missing_spell_metadata_and_domain_level(self):
        self.assertContains(self.client.get('/spells/', {'sub_school__slug': '__missing__'}),
                            '1 spell found.')
        self.assertContains(self.client.get('/spells/', {'descriptors__slug': '__missing__'}),
                            '1 spell found.')
        self.assertContains(self.client.get('/spells/', {'spellclasslevel__level': '__missing__'}),
                            '1 spell found.')
        fire = Domain.objects.create(name='Fire', slug='fire')
        sun = Domain.objects.create(name='Sun', slug='sun')
        SpellDomainLevel.objects.create(spell=self.spell, domain=fire, level=0)
        SpellDomainLevel.objects.create(spell=self.spell, domain=sun, level=1)
        self.assertContains(self.client.get('/spells/', {
            'domain_levels__slug': 'fire', 'spelldomainlevel__level': '0'}), '1 spell found.')
        self.assertContains(self.client.get('/spells/', {
            'domain_levels__slug': 'fire', 'spelldomainlevel__level': '1'}), '0 spells found.')

    def test_invalid_legacy_filter_reports_error_without_partial_application(self):
        response = self.client.get('/rulebooks/', {
            'name': 'not-a-book', 'dnd_edition__slug': 'unknown-edition'})
        self.assertContains(response, 'could not be applied')
        self.assertContains(response, 'Test Handbook')

    def test_multiselect_category_counts_each_feat_once(self):
        general = FeatCategory.objects.create(name='General', slug='general')
        combat = FeatCategory.objects.create(name='Combat', slug='combat')
        feat = Feat.objects.create(rulebook=self.spell.rulebook, name='Quick Study',
                                   slug='quick-study', description='Study quickly.', benefit='Learn.')
        feat.feat_categories.add(general, combat)
        response = self.client.get('/feats/', {
            'feat_categories__slug': ['general', 'combat']})
        self.assertContains(response, '1 result found.')
        self.assertEqual(response.context['paginator'].count(), 1)

    def test_catalog_text_filters_ignore_case(self):
        feat = Feat.objects.create(rulebook=self.spell.rulebook, name='Power Attack',
                                   slug='power-attack', description='A stronger blow.',
                                   benefit='Trade accuracy for damage.')
        TextFeatPrerequisite.objects.create(feat=feat, text='Strength 13')
        for term in ('Power', 'power', 'POWER'):
            response = self.client.get('/feats/', {'name': term})
            self.assertContains(response, feat.get_absolute_url())
            self.assertEqual(response.context['paginator'].count(), 1)
        for term in ('Strength', 'strength', 'STRENGTH'):
            response = self.client.get('/feats/', {'prerequisite': term})
            self.assertContains(response, feat.get_absolute_url())
            self.assertEqual(response.context['paginator'].count(), 1)
        accented = Feat.objects.create(rulebook=self.spell.rulebook, name='Ágil Mind',
                                       slug='agil-mind', description='Think quickly.', benefit='Focus.')
        self.assertContains(self.client.get('/feats/', {'name': 'agil'}),
                            accented.get_absolute_url())
        for term in ('Test', 'test', 'TEST'):
            response = self.client.get('/rulebooks/', {'name': term})
            self.assertContains(response, self.spell.rulebook.get_absolute_url())
            self.assertEqual(response.context['paginator'].count(), 1)

    def test_race_image_upload_uses_supported_pillow_resampling(self):
        size = RaceSize.objects.create(name='Medium', order=1)
        buffer = BytesIO()
        Image.new('RGB', (600, 600), color='blue').save(buffer, format='JPEG')
        upload = SimpleUploadedFile('portrait.jpg', buffer.getvalue(), content_type='image/jpeg')
        with TemporaryDirectory() as media_dir, override_settings(MEDIA_ROOT=media_dir):
            race = Race.objects.create(
                rulebook=self.spell.rulebook, size=size, name='Test Race', slug='test-race',
                space=5, reach=5, image=upload)
            self.assertEqual(race.image.name, f'race/{race.pk}.jpg')
            with Image.open(race.image.path) as saved:
                self.assertEqual(saved.size, (500, 500))
