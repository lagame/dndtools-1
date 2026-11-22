from io import BytesIO
import json
import re
from datetime import date
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from types import SimpleNamespace

from PIL import Image
from axes.models import AccessAttempt
from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase
from django.test.utils import override_settings
from django.urls import reverse

from dnd.models import (
    CharacterClass, CharacterClassVariant, DndEdition, Domain, DomainVariant, Feat, FeatCategory,
    Item, ItemActivationType, ItemAuraType, ItemSlot, MonsterSubtype, MonsterType, Race, RaceSize,
    NewsEntry, RuleCondition, Rulebook, Spell, SpellClassLevel, SpellDescriptor, SpellDomainLevel, SpellSchool, StaticPage,
    TextFeatPrerequisite,
)
from dnd.templatetags.versioned_static import versioned_static
from dnd.security import _tunnel_peers, axes_client_ip, axes_lockout_parameters
from dnd.templatetags.catalog_html import safe_catalog_html
from dndproject import settings as project_settings


class AdminSecurityTests(TestCase):
    def test_custom_route_and_report_only_csp(self):
        login = reverse('admin:login')
        self.assertEqual(login, '/' + settings.ADMIN_URL + 'login/')
        response = self.client.get(login)
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertIn('Content-Security-Policy-Report-Only', response)
        self.assertNotIn('Content-Security-Policy', response)

    def test_cf_ip_requires_trusted_peer_and_valid_address(self):
        _tunnel_peers.cache_clear()
        factory = RequestFactory()
        request = factory.post('/' + settings.ADMIN_URL + 'login/',
                               REMOTE_ADDR='198.51.100.8', HTTP_CF_CONNECTING_IP='203.0.113.10')
        with patch('dnd.security.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('172.20.0.2', 0))]):
            self.assertIsNone(axes_client_ip(request))
            self.assertEqual(axes_lockout_parameters(request, {}), ['username'])
            request.META['REMOTE_ADDR'] = '172.20.0.2'
            self.assertEqual(axes_client_ip(request), '203.0.113.10')
            self.assertEqual(axes_lockout_parameters(request, {}), ['username', 'ip_address'])
            request.META['HTTP_CF_CONNECTING_IP'] = '203.0.113.10, 198.51.100.8'
            self.assertIsNone(axes_client_ip(request))
        self.assertEqual(axes_lockout_parameters(SimpleNamespace(ip_address='203.0.113.10'), {}),
                         ['username', 'ip_address'])

    def test_cf_ip_limits_multiple_usernames_without_blocking_another_ip(self):
        _tunnel_peers.cache_clear()
        login = reverse('admin:login')
        with patch('dnd.security.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('172.20.0.2', 0))]):
            for index in range(4):
                response = Client().post(login, {'username': 'invalid-%d' % index, 'password': 'wrong'},
                                         REMOTE_ADDR='172.20.0.2', HTTP_CF_CONNECTING_IP='203.0.113.10')
                self.assertEqual(response.status_code, 200)
            blocked = Client().post(login, {'username': 'invalid-4', 'password': 'wrong'},
                                    REMOTE_ADDR='172.20.0.2', HTTP_CF_CONNECTING_IP='203.0.113.10')
            self.assertEqual(blocked.status_code, 429)
            self.assertTrue(AccessAttempt.objects.filter(ip_address='203.0.113.10').exists())
            other = Client().post(login, {'username': 'invalid-other', 'password': 'wrong'},
                                  REMOTE_ADDR='172.20.0.2', HTTP_CF_CONNECTING_IP='203.0.113.11')
            self.assertEqual(other.status_code, 200)

    def test_login_is_branded_uncached_and_requires_csrf(self):
        login = reverse('admin:login')
        client = Client(enforce_csrf_checks=True)
        page = client.get(login)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'Catalog administration')
        self.assertContains(page, 'css/admin-login.css?v=')
        self.assertEqual(page['Cache-Control'], 'no-store')
        self.assertEqual(client.post(login, {'username': 'someone', 'password': 'wrong'}).status_code, 403)

    def test_five_failures_lock_username_across_clients(self):
        login = reverse('admin:login')
        User.objects.create_superuser(username='editor', email='editor@example.test', password='Long-test-password-123')
        first = Client()
        for attempt in range(4):
            response = first.post(login, {'username': 'editor', 'password': 'wrong'}, HTTP_USER_AGENT='agent-%d' % attempt)
            self.assertEqual(response.status_code, 200)
        fifth = Client().post(login, {'username': 'editor', 'password': 'wrong'}, HTTP_USER_AGENT='another-agent')
        self.assertEqual(fifth.status_code, 429)
        self.assertContains(fifth, 'Too many login attempts', status_code=429)
        self.assertEqual(fifth['Cache-Control'], 'no-store')
        self.assertTrue(AccessAttempt.objects.filter(username='editor').exists())
        self.assertFalse(AccessAttempt.objects.filter(username='editor').exclude(ip_address__isnull=True).exists())
        self.assertFalse(AccessAttempt.objects.filter(username='editor', post_data__contains='wrong').exists())
        self.assertEqual(Client().post(login, {'username': 'editor', 'password': 'Long-test-password-123'}).status_code, 429)
        self.assertEqual(Client().get(login).status_code, 200)
        User.objects.create_superuser(username='another-editor', email='another@example.test', password='Long-test-password-456')
        self.assertEqual(Client().post(login, {'username': 'another-editor', 'password': 'Long-test-password-456'}).status_code, 302)

    def test_valid_admin_login_and_password_policy(self):
        User.objects.create_superuser(username='editor', email='editor@example.test', password='Long-test-password-123')
        self.assertEqual(self.client.post(reverse('admin:login'), {'username': 'editor', 'password': 'Long-test-password-123'}).status_code, 302)
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)
        with self.assertRaises(ValidationError):
            validate_password('short')

    def test_workspace_links_follow_model_permissions(self):
        editor = User.objects.create_user(username='book-editor', is_staff=True)
        editor.user_permissions.add(Permission.objects.get(
            content_type__app_label='dnd', codename='view_rulebook'))
        self.client.force_login(editor)
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Catalog workspace')
        self.assertContains(response, 'css/admin-workspace.css?v=')
        self.assertContains(response, reverse('admin:dnd_rulebook_changelist'))
        self.assertNotContains(response, reverse('admin:dnd_rulebook_add'))
        self.assertNotContains(response, reverse('admin:dnd_spell_changelist'))
        self.assertEqual(self.client.get(reverse('admin:dnd_spell_changelist')).status_code, 403)
        self.assertEqual(self.client.get(reverse('admin:dnd_rulebook_add')).status_code, 403)

    def test_workspace_explains_missing_permissions(self):
        editor = User.objects.create_user(username='unassigned-editor', is_staff=True)
        self.client.force_login(editor)
        response = self.client.get(reverse('admin:index'))
        self.assertContains(response, 'You don’t have permission to view or edit anything.')
        self.assertNotContains(response, 'workspace-card-actions')


class CatalogSmokeTests(TestCase):
    @override_settings(PUBLIC_HOST='dndtools.quest')
    def test_sitemap_uses_public_domain_and_contains_catalog_entries(self):
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('<loc>https://dndtools.quest/</loc>', content)
        self.assertIn('<loc>https://dndtools.quest/spells/</loc>', content)
        self.assertIn('<loc>https://dndtools.quest%s</loc>' % self.spell.get_absolute_url(), content)
        self.assertNotIn('example.com', content)

    @override_settings(PUBLIC_HOST='dndtools.quest')
    def test_catalog_listing_is_indexable_but_filtered_view_and_search_are_not(self):
        listing = self.client.get('/spells/')
        self.assertEqual(listing.status_code, 200)
        self.assertContains(listing, '<link rel="canonical" href="https://dndtools.quest/spells/">', html=True)
        self.assertNotIn('name="robots" content="noindex', listing.content.decode())
        self.assertContains(listing, 'hreflang="pt-BR"')
        filtered = self.client.get('/spells/', {'name': 'Ember'})
        self.assertContains(filtered, '<meta name="robots" content="noindex, follow">', html=True)
        search = self.client.get('/search/', {'q': 'Ember'})
        self.assertContains(search, '<meta name="robots" content="noindex, follow">', html=True)

    @override_settings(PUBLIC_HOST='dndtools.quest')
    def test_detail_has_absolute_canonical_and_breadcrumb_data(self):
        response = self.client.get(self.spell.get_absolute_url())
        self.assertContains(response, 'href="https://dndtools.quest%s"' % self.spell.get_absolute_url())
        scripts = re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                             response.content.decode(), re.DOTALL)
        breadcrumbs = [json.loads(script) for script in scripts if json.loads(script)['@type'] == 'BreadcrumbList']
        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual(breadcrumbs[0]['itemListElement'][-1]['item'],
                         'https://dndtools.quest' + self.spell.get_absolute_url())

    @override_settings(PUBLIC_HOST='dndtools.quest')
    def test_untranslated_portuguese_detail_points_to_english(self):
        response = self.client.get('/pt-br' + self.spell.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<meta name="robots" content="noindex, follow">', html=True)
        self.assertContains(response, '<link rel="canonical" href="https://dndtools.quest%s">' %
                            self.spell.get_absolute_url(), html=True)

    @override_settings(PUBLIC_HOST='dndtools.quest')
    def test_book_data_escapes_script_markup(self):
        Rulebook.objects.filter(pk=self.spell.rulebook_id).update(
            name='</script><script>alert(1)</script>')
        response = self.client.get(self.spell.rulebook.get_absolute_url())
        content = response.content.decode()
        scripts = re.findall(r'<script type="application/ld\+json">(.*?)</script>', content, re.DOTALL)
        books = [json.loads(script) for script in scripts if json.loads(script)['@type'] == 'Book']
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0]['name'], '</script><script>alert(1)</script>')
        self.assertNotIn('<script>alert(1)</script>', content)

    def test_crawlers_can_discover_catalog_without_legacy_feed(self):
        robots = self.client.get('/robots.txt')
        self.assertEqual(robots.status_code, 200)
        self.assertIn('text/plain', robots['Content-Type'])
        self.assertIn('no-store', robots['Cache-Control'])
        self.assertContains(robots, 'Allow: /')
        self.assertContains(robots, 'Sitemap: https://dndtools.quest/sitemap.xml')
        self.assertEqual(self.client.get('/rss.xml').status_code, 404)
        sitemap = self.client.get('/sitemap.xml')
        self.assertEqual(sitemap.status_code, 200)
        self.assertContains(sitemap, self.spell.get_absolute_url())

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

    def test_admin_lists_filters_and_choices_show_catalog_names(self):
        descriptor = SpellDescriptor.objects.create(name='Fire', slug='fire')
        size = RaceSize.objects.create(name='Large', order=2)
        monster_type = MonsterType.objects.create(name='Magical Beast', slug='magical-beast')
        subtype = MonsterSubtype.objects.create(name='Extraplanar', slug='extraplanar')
        wizard = CharacterClass.objects.create(name='Wizard', slug='wizard', prestige=False)
        variant = CharacterClassVariant.objects.create(character_class=wizard, rulebook=self.spell.rulebook)
        domain = Domain.objects.create(name='Fire', slug='fire')
        domain_variant = DomainVariant.objects.create(domain=domain, rulebook=self.spell.rulebook)
        self.assertEqual(str(variant), 'Wizard variant (Test Handbook)')
        self.assertEqual(str(domain_variant), 'Fire variant (Test Handbook)')
        editor = User.objects.create_superuser('editor', settings.ADMINS[0][1], 'Long-test-password-123')
        self.client.force_login(editor)
        choices = (
            ('admin:dnd_monster_add', (self.spell.rulebook, size, monster_type, subtype)),
            ('admin:dnd_spell_add', (descriptor, self.spell.rulebook, self.spell.school)),
        )
        for view, objects in choices:
            response = self.client.get(reverse(view))
            self.assertEqual(response.status_code, 200)
            for obj in objects:
                with self.subTest(view=view, model=type(obj).__name__):
                    self.assertContains(response, '<option value="%s">%s</option>' % (obj.pk, obj.name), html=True)
            self.assertNotRegex(response.content.decode(), r'\b[A-Z]\w* object \(')
        response = self.client.get(reverse('admin:dnd_characterclassvariant_changelist'))
        self.assertContains(response, 'Wizard')
        self.assertContains(response, 'Test Handbook')
        self.assertNotRegex(response.content.decode(), r'\b[A-Z]\w* object \(')

    def test_public_item_relations_show_names_instead_of_object_ids(self):
        slot = ItemSlot.objects.create(name='Shield', slug='shield')
        aura = ItemAuraType.objects.create(name='Moderate', slug='moderate')
        activation = ItemActivationType.objects.create(name='Command word', slug='command-word')
        feat = Feat.objects.create(rulebook=self.spell.rulebook, name='Craft Magic Arms and Armor',
                                   slug='craft-arms', description='Craft items.', benefit='Create equipment.')
        item = Item.objects.create(rulebook=self.spell.rulebook, name='Absorbing Shield',
                                   slug='absorbing-shield', type=Item.ItemType.MAGIC,
                                   body_slot=slot, aura=aura, activation=activation,
                                   caster_level=7, price_gp=10000, description='A silver shield.')
        item.aura_schools.add(self.spell.school)
        item.required_feats.add(feat)
        item.required_spells.add(self.spell)
        response = self.client.get(item.get_absolute_url())
        for name in ('Absorbing Shield', 'Shield', 'Moderate', 'Command word',
                     'Evocation', 'Craft Magic Arms and Armor', 'Arcane Ember'):
            self.assertContains(response, name)
        self.assertNotRegex(response.content.decode(), r'\b[A-Z]\w* object \(')

    def test_legacy_html_is_sanitized_at_render_time(self):
        fragment = ('<table><tr><td style="text-align:center; background-image:url(javascript:alert(5))"><strong>Arcane</strong> '
                    '<a href="/feats/test/">feat</a></td></tr></table>'
                    '<img src=x onerror=alert(1)><script>alert(2)</script>'
                    '<a href="javascript:alert(3)">bad</a>'
                    '<span class="errata-new" onclick="alert(4)">new</span>'
                    '<span class="caps">ABC</span>')
        Spell.objects.filter(pk=self.spell.pk).update(description_html=fragment)
        response = self.client.get(self.spell.get_absolute_url())
        self.assertContains(response, '<table>')
        self.assertContains(response, '<strong>Arcane</strong>')
        self.assertContains(response, 'href="/feats/test/"')
        self.assertContains(response, 'class="errata-new"')
        self.assertContains(response, 'class="caps"')
        self.assertContains(response, 'text-align:center')
        cleaned = str(safe_catalog_html(fragment))
        self.assertContains(response, cleaned, html=True)
        for dangerous in ('<img', '<script', 'alert(', 'javascript:', 'onclick=', 'onerror='):
            self.assertNotIn(dangerous, cleaned)
        self.assertNotIn('javascript:', safe_catalog_html('<a href="javascript:alert(1)">bad</a>'))
        self.assertNotIn('href=', safe_catalog_html('<a href="//evil.example">bad</a>'))
        self.assertNotIn('href=', safe_catalog_html('<a href="https://evil.example">bad</a>'))

    def test_html_revalidates_and_asset_urls_change_with_content(self):
        response = self.client.get('/')
        self.assertEqual(response['Cache-Control'], 'no-cache, max-age=0, must-revalidate')
        self.assertContains(response, '<option value="dark">Petroleo</option>')
        self.assertContains(response, '<option value="oled">Dark</option>')
        theme_script = (Path(settings.STATIC_DIR) / 'js/theme.js').read_text(encoding='utf-8')
        theme_styles = (Path(settings.STATIC_DIR) / 'css/themes.css').read_text(encoding='utf-8')
        self.assertIn("'dark'", theme_script)
        self.assertIn("'oled'", theme_script)
        for selector in ('--background: #101a23;', '--ink: #edf3f7;',
                         'a { color: #8edfff; }', 'color-scheme: dark;'):
            self.assertIn(selector, theme_styles)
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

    def test_public_help_explains_catalog_access_and_collaborator_recovery(self):
        english = self.client.get(reverse('help'))
        self.assertContains(english, 'Help and FAQ')
        self.assertContains(english, 'Public browsing, search and filters work without an account')
        self.assertContains(english, 'collaborators have no additional Django password')
        self.assertContains(english, 'lost Cloudflare authenticator')
        self.assertContains(english, 'I forgot my password. How do I recover it?')
        self.assertContains(english, 'an invalid code can also cause the access denied message')
        self.assertContains(english, 'href="/help/"')
        self.assertNotIn('sessionid', english.cookies)

        portuguese = self.client.get('/pt-br/help/')
        self.assertContains(portuguese, 'Ajuda e perguntas frequentes')
        self.assertContains(portuguese, 'colaboradores não têm uma senha adicional do Django')
        self.assertContains(portuguese, 'Esqueci minha senha. Como recupero?')
        self.assertContains(portuguese, 'um código inválido também pode causar a mensagem de acesso negado')
        self.assertContains(portuguese, 'href="/pt-br/help/"')
        self.assertContains(portuguese, 'aria-current="page"')
        self.assertNotIn('sessionid', portuguese.cookies)

    def test_privacy_notice_and_legacy_news_cookie(self):
        NewsEntry.objects.create(published=date(2026, 11, 15), title='Catalog update', body='Updated catalog.')
        home = self.client.get('/', HTTP_ACCEPT_LANGUAGE='pt-BR,pt;q=0.9')
        self.assertEqual(home.status_code, 302)
        self.assertEqual(home['Location'], '/pt-br/')
        home = self.client.get(home['Location'])
        self.assertContains(home, 'Sua privacidade')
        self.assertContains(home, '/pt-br/privacy/')
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
        self.assertEqual(portuguese_policy.status_code, 302)
        portuguese_policy = self.client.get(portuguese_policy['Location'])
        self.assertContains(portuguese_policy, 'Privacidade no D&amp;D Tools')
        self.assertNotContains(portuguese_policy, 'Privacy at D&amp;D Tools')

    def test_staff_page_shows_current_maintainer_without_legacy_staff(self):
        response = self.client.get(reverse('staff'))
        self.assertContains(response, 'Ronassic')
        self.assertContains(response, '37 years')
        self.assertContains(response, 'SpellBrasil')
        self.assertContains(response, '270 members')
        self.assertContains(response, 'mailto:ronassic@gmail.com')
        self.assertContains(response, 'Maintainer')
        portuguese = self.client.get('/pt-br/contacts/staff/')
        self.assertContains(portuguese, '37 anos')
        self.assertContains(portuguese, '270 membros')
        StaticPage.objects.create(name='staff', body='Outdated volunteer listing')
        self.assertNotContains(self.client.get(reverse('staff')), 'Outdated volunteer listing')

    def test_home_hides_legacy_domain_announcements(self):
        NewsEntry.objects.create(published=date(2012, 5, 5), title='Old domain update',
                                 body='http://dndtools.eu/spells/')
        NewsEntry.objects.create(published=date(2026, 11, 16), title='Current catalog update',
                                 body='The catalog is available here.')
        response = self.client.get('/')
        self.assertContains(response, 'Current catalog update')
        self.assertNotContains(response, 'Old domain update')
        self.assertNotContains(response, 'dndtools.eu')

    def test_conditions_and_missing_legacy_android_page(self):
        condition = RuleCondition.objects.create(name='Dazed', description='Limited actions.')
        self.assertContains(self.client.get(reverse('rule_condition_list')), condition.get_absolute_url())
        self.assertContains(self.client.get(condition.get_absolute_url()), 'Limited actions.')
        self.assertContains(self.client.get(reverse('search'), {'q': 'Dazed'}), condition.get_absolute_url())
        self.assertContains(self.client.get(reverse('android')), 'not available in this catalog snapshot')

    def test_navigation_keeps_legacy_destinations_and_mobile_redirects(self):
        page = self.client.get('/spells/')
        self.assertContains(page, 'href="%s"' % reverse('admin:index'))
        self.assertContains(page, 'class="lore-mark"')
        self.assertContains(page, 'rel="nofollow noopener"')
        self.assertContains(page, 'aria-label="Oghma"')
        self.assertNotContains(page, 'Admin login')
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

    def test_public_suggestions_are_small_and_expose_no_record_body(self):
        for index in range(10):
            Spell.objects.create(
                rulebook=self.spell.rulebook, school=self.spell.school,
                name=f'Arcane Test {index}', slug=f'arcane-test-{index}',
                description='Private body is not part of suggestions.',
                verbal_component=False, somatic_component=False,
                material_component=False, arcane_focus_component=False,
                divine_focus_component=False, xp_component=False,
                meta_breath_component=False, true_name_component=False,
            )
        response = self.client.get(reverse('search_suggest'), {'q': 'arcane'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertEqual(len(response.json()['results']), 3)
        self.assertEqual(set(response.json()['results'][0]),
                         {'title', 'original_title', 'url', 'category', 'book', 'edition'})
        self.assertNotIn('Private body', response.content.decode())

    def test_crawlers_can_discover_catalog_without_legacy_feed(self):
        robots = self.client.get('/robots.txt')
        self.assertEqual(robots.status_code, 200)
        self.assertIn('text/plain', robots['Content-Type'])
        self.assertContains(robots, 'Allow: /')
        self.assertContains(robots, 'Sitemap: https://dndtools.quest/sitemap.xml')
        self.assertEqual(self.client.get('/rss.xml').status_code, 404)
        sitemap = self.client.get('/sitemap.xml')
        self.assertEqual(sitemap.status_code, 200)
        self.assertContains(sitemap, self.spell.get_absolute_url())

    def test_rulebook_filters_and_large_html_page_size(self):
        book = self.spell.rulebook
        book.description = 'Rules for an arcane library.'
        book.publication_type = 'core'
        book.year = '2004'
        book.save(update_fields=['description', 'publication_type', 'year'])
        other = Rulebook.objects.create(
            dnd_edition=book.dnd_edition, name='Other Guide', abbr='OG',
            slug='other-guide', publication_type='sourcebook', year='2005')
        response = self.client.get('/rulebooks/', {
            'description': 'LIBRARY', 'publication_type': 'core',
            'publication_year': '2004', 'content': 'spells', 'page_size': '5000',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['paginator'].page_size, 5000)
        self.assertEqual(response.context['paginator'].count(), 1)
        self.assertContains(response, book.get_absolute_url())
        self.assertNotContains(response, other.get_absolute_url())
        self.assertContains(response, '<option value="5000" selected="selected">5000</option>', html=True)
        no_spells = self.client.get('/rulebooks/', {'publication_type': 'sourcebook',
                                                      'content': 'spells'})
        self.assertEqual(no_spells.context['paginator'].count(), 0)
        self.assertEqual(self.client.get('/spells/', {'page_size': '5001'}).context[
            'paginator'].page_size, 5000)

    def test_web_catalog_source_does_not_show_a_book_cover_placeholder(self):
        web = Rulebook.objects.create(
            dnd_edition=self.spell.rulebook.dnd_edition, name='Web', abbr='Web',
            slug='web', publication_type='periodical')
        listing = self.client.get('/rulebooks/')
        self.assertContains(listing, 'rulebook-card--text-only')
        self.assertContains(listing, web.get_absolute_url())
        detail = self.client.get(web.get_absolute_url())
        self.assertContains(detail, 'rulebook-detail-grid--text-only')
        self.assertNotContains(detail, 'Cover unavailable')
        self.assertNotContains(detail, 'rulebook-detail-cover')

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
        with TemporaryDirectory() as media_dir, override_settings(MEDIA_ROOT=media_dir), \
                patch.object(project_settings, 'MEDIA_ROOT', media_dir):
            race = Race.objects.create(
                rulebook=self.spell.rulebook, size=size, name='Test Race', slug='test-race',
                space=5, reach=5, image=upload)
            self.assertEqual(race.image.name, f'race/{race.pk}.jpg')
            with Image.open(race.image.path) as saved:
                self.assertEqual(saved.size, (500, 500))
            detail = self.client.get(race.get_absolute_url())
            self.assertContains(detail, f'data-theme-src="/media/race/{race.pk}.jpg"')
            self.assertContains(detail, 'Illustration hidden in Simple')
            self.assertContains(detail, f'<noscript><img src="/media/race/{race.pk}.jpg"')
