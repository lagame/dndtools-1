"""Exercise navigation, search and filters at compact and desktop widths."""

import os
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


BASE = os.environ.get('DND_TEST_BASE_URL', 'http://127.0.0.1:8765')
OUTPUT = Path(os.environ['DND_QA_OUTPUT']) if os.environ.get('DND_QA_OUTPUT') else None
DETAIL = os.environ.get('DND_QA_DETAIL_URL', '')
REAL_DATA = os.environ.get('DND_QA_REAL_DATA') == '1'
MISSING_IMAGE = os.environ.get('DND_QA_MISSING_IMAGE_URL', '')


def screenshot(page, name):
    if OUTPUT:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(OUTPUT / name), full_page=True)


def visit(page, path):
    for attempt in range(10):
        try:
            return page.goto(BASE + path, wait_until='networkidle', timeout=12000)
        except Exception:
            if attempt == 9:
                raise
            time.sleep(1)


def main():
    with sync_playwright() as playwright:
        executable = os.environ.get('DND_BROWSER_EXECUTABLE')
        browser = playwright.chromium.launch(headless=True, executable_path=executable)
        try:
            for width in (360, 390, 768, 1440):
                page = browser.new_page(viewport={'width': width, 'height': 750}, locale='en-US')
                assert visit(page, '/').status == 200
                notice = page.locator('#privacy-notice')
                expect(notice).to_be_visible()
                lore_mark = page.get_by_role('link', name='Oghma')
                expect(lore_mark).to_be_visible()
                assert lore_mark.get_attribute('href').startswith('/')
                assert lore_mark.get_attribute('href').endswith('/')
                assert lore_mark.get_attribute('rel') == 'nofollow noopener'
                assert lore_mark.locator('svg[aria-hidden="true"]').count() == 1
                assert lore_mark.inner_text().strip() == ''
                assert lore_mark.evaluate('(link) => getComputedStyle(link).position') == 'fixed'
                assert lore_mark.bounding_box()['y'] + lore_mark.bounding_box()['height'] < notice.bounding_box()['y']
                assert all('?v=' in url for url in page.locator('link[rel="stylesheet"][href]').evaluate_all('(links) => links.map(link => link.href)'))
                assert page.evaluate("localStorage.getItem('dnd_privacy_notice_v1')") is None
                if width in (390, 1440):
                    screenshot(page, f'privacy-notice-{width}.png')
                notice.get_by_role('button', name='Got it').click()
                expect(notice).to_be_hidden()
                shortcut_y = lore_mark.bounding_box()['y']
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                assert abs(lore_mark.bounding_box()['y'] - shortcut_y) <= 1
                assert visit(page, '/').status == 200
                expect(notice).to_be_hidden()
                if width == 390:
                    page.evaluate("localStorage.setItem('dnd_privacy_notice_v1', String(Date.now() - 181 * 86400000))")
                    assert visit(page, '/').status == 200
                    expect(notice).to_be_visible()
                    assert page.evaluate("localStorage.getItem('dnd_privacy_notice_v1')") is None
                    notice.get_by_role('button', name='Got it').click()
                toggle = page.get_by_role('button', name='Toggle catalog menu')
                sidebar = page.locator('#catalog-sidebar')
                assert page.get_by_role('combobox', name='Search the catalog').count() == 1
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                if width <= 900:
                    assert not sidebar.is_visible()
                    toggle.click()
                    expect(sidebar).to_be_visible()
                    expect(page.locator('#navigation-close')).to_be_focused()
                    assert sidebar.get_attribute('aria-modal') == 'true'
                    page.keyboard.press('Shift+Tab')
                    assert sidebar.evaluate('(element) => element.contains(document.activeElement)')
                    page.get_by_role('button', name='Toggle Character Options sections').click()
                    page.get_by_role('button', name='Toggle Feats sections').click()
                    page.get_by_role('button', name='Toggle Feat categories sections').click()
                    assert page.get_by_role('link', name='Traits', exact=True).is_visible()
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    screenshot(page, f'menu-{width}.png')
                    page.keyboard.press('Escape')
                    expect(sidebar).to_be_hidden()
                    expect(toggle).to_be_focused()
                else:
                    assert sidebar.is_visible()
                    page.get_by_role('button', name='Toggle Character Options sections').click()
                    screenshot(page, f'menu-{width}.png')
                    toggle.click()
                    expect(sidebar).to_be_hidden()
                    toggle.click()
                    expect(sidebar).to_be_visible()
                assert visit(page, '/search/?q=ember').status == 200
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                assert visit(page, '/spells/').status == 200
                assert page.get_by_text('spells found.').count() >= 1 or page.get_by_text('spell found.').count() >= 1
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                screenshot(page, f'spells-{width}.png')
                picker = page.get_by_role('combobox', name='Site theme')
                expect(picker).to_be_visible()
                assert picker.input_value() == 'standard'
                assert page.evaluate("localStorage.getItem('dnd_theme_v2')") is None
                for theme, heading_font in (('simple', 'Arial'), ('modern', 'Georgia'),
                                            ('standard', 'Inter'), ('dark', 'Georgia'),
                                            ('oled', 'Georgia')):
                    picker.select_option(theme)
                    assert page.evaluate('document.documentElement.dataset.theme') == theme
                    brand_x = page.locator('.site-header .brand').bounding_box()['x']
                    menu_x = page.locator('#navigation-toggle').bounding_box()['x']
                    theme_x = picker.bounding_box()['x']
                    assert brand_x < menu_x < theme_x
                    assert page.locator('#identity-stylesheet').evaluate('(link) => link.hasAttribute("href")') == (theme == 'standard')
                    assert page.evaluate("localStorage.getItem('dnd_theme_v2')") == theme
                    assert page.locator('#content h1, #content h2').first.evaluate('(heading) => getComputedStyle(heading).fontFamily').startswith(heading_font)
                    if theme in ('dark', 'oled'):
                        contrast = page.evaluate("""() => {
                            const luminance = (color) => {
                                const rgb = color.match(/[\\d.]+/g).slice(0, 3).map(Number).map((v) => {
                                    v /= 255;
                                    return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
                                });
                                return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2];
                            };
                            const ratio = (foreground, background) => {
                                const values = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
                                return (values[0] + 0.05) / (values[1] + 0.05);
                            };
                            const body = getComputedStyle(document.body);
                            const link = getComputedStyle(document.querySelector('#content a'));
                            return {
                                body: ratio(body.color, body.backgroundColor),
                                link: ratio(link.color, body.backgroundColor),
                                background: body.backgroundColor,
                            };
                        }""")
                        assert contrast['body'] >= 4.5, contrast
                        assert contrast['link'] >= 4.5, contrast
                        expected_background = 'rgb(0, 0, 0)' if theme == 'oled' else 'rgb(16, 26, 35)'
                        assert contrast['background'] == expected_background, contrast
                        assert visit(page, '/').status == 200
                        if theme == 'oled':
                            surfaces = page.evaluate("""() => {
                                const style = selector => getComputedStyle(document.querySelector(selector));
                                return {
                                    html: style('html').backgroundColor,
                                    header: style('.site-header').backgroundColor,
                                    main: style('.main-content').backgroundColor,
                                    sidebar: style('.catalog-sidebar').backgroundColor,
                                    hero: style('.home-hero').backgroundColor,
                                    hero_image: style('.home-hero').backgroundImage,
                                    card: style('.category-grid a').backgroundColor,
                                    input: style('.header-search input').backgroundColor,
                                    notice: style('.privacy-notice').backgroundColor,
                                    heading: style('.home-hero h1').color,
                                    secondary: style('.home-hero p').color,
                                };
                            }""")
                            assert surfaces == {
                                'html': 'rgb(0, 0, 0)', 'header': 'rgb(10, 10, 10)',
                                'main': 'rgb(10, 10, 10)', 'sidebar': 'rgb(10, 10, 10)',
                                'hero': 'rgb(10, 10, 10)', 'hero_image': 'none',
                                'card': 'rgb(17, 17, 17)', 'input': 'rgb(17, 17, 17)',
                                'notice': 'rgb(10, 10, 10)', 'heading': 'rgb(255, 255, 255)',
                                'secondary': 'rgb(179, 179, 179)',
                            }, surfaces
                        action_contrast = page.locator('.hero-actions a').first.evaluate("""(link) => {
                            const luminance = (color) => {
                                const rgb = color.match(/[\\d.]+/g).slice(0, 3).map(Number).map((v) => {
                                    v /= 255;
                                    return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
                                });
                                return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2];
                            };
                            const style = getComputedStyle(link);
                            const values = [luminance(style.color), luminance(style.backgroundColor)].sort((a, b) => b - a);
                            return (values[0] + 0.05) / (values[1] + 0.05);
                        }""")
                        assert action_contrast >= 4.5, action_contrast
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    if width in (390, 1440):
                        screenshot(page, f'theme-{theme}-spells-{width}.png')
                    assert visit(page, '/spells/').status == 200
                    assert picker.input_value() == theme
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    if theme in ('simple', 'modern', 'oled') and width in (390, 1440):
                        assert visit(page, '/').status == 200
                        if theme == 'simple':
                            assert page.locator('.home-hero p').evaluate('(text) => getComputedStyle(text).color') == 'rgb(51, 51, 51)'
                        screenshot(page, f'theme-{theme}-home-{width}.png')
                        assert visit(page, '/spells/').status == 200
                assert not page.context.cookies(BASE)
                assert visit(page, '/contacts/').status == 200
                assert page.get_by_text('Open a project issue').count() >= 1
                if width in (390, 1440):
                    assert visit(page, '/privacy/').status == 200
                    expect(page.get_by_role('heading', name='Privacy at D&D Tools')).to_be_visible()
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    if width == 390:
                        assert page.locator('.privacy-policy table').evaluate('(el) => el.scrollWidth <= el.clientWidth')
                    screenshot(page, f'privacy-policy-{width}.png')
                    page.get_by_role('link', name='Português (Brasil)').click()
                    expect(page.get_by_role('heading', name='Privacidade no D&D Tools')).to_be_visible()
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    if width == 390:
                        assert page.locator('.privacy-policy table').evaluate('(el) => el.scrollWidth <= el.clientWidth')
                        screenshot(page, 'privacy-policy-pt-390.png')
                if DETAIL and width in (390, 1440):
                    assert visit(page, DETAIL).status == 200
                    screenshot(page, f'detail-{width}.png')
                    assert visit(page, '/spells/?class_levels__slug=wizard&spellclasslevel__level=0&_filter=1').status == 200
                    screenshot(page, f'filters-{width}.png')
                page.close()
            for theme in ('simple', 'modern', 'dark', 'oled'):
                returning = browser.new_page(viewport={'width': 390, 'height': 750}, locale='en-US')
                returning.add_init_script(f"localStorage.setItem('dnd_theme_v2', '{theme}')")
                assert visit(returning, '/').status == 200
                expect(returning.locator('#privacy-notice')).to_be_visible()
                assert returning.get_by_role('combobox', name='Site theme').input_value() == theme
                assert returning.evaluate('document.documentElement.scrollWidth <= innerWidth')
                screenshot(returning, f'theme-{theme}-notice-390.png')
                returning.get_by_role('button', name='Got it').click()
                assert visit(returning, '/privacy/?lang=pt').status == 200
                assert returning.locator('.privacy-policy table').evaluate('(table) => table.scrollWidth <= table.clientWidth')
                assert returning.evaluate('document.documentElement.scrollWidth <= innerWidth')
                returning.close()
            for old, current in (('modern', 'standard'), ('classic', 'modern'), ('simple', 'simple')):
                migrating = browser.new_page()
                migrating.add_init_script(f"localStorage.setItem('dnd_theme_v1', '{old}')")
                assert visit(migrating, '/').status == 200
                assert migrating.get_by_role('combobox', name='Site theme').input_value() == current
                assert migrating.evaluate("localStorage.getItem('dnd_theme_v1')") is None
                assert migrating.evaluate("localStorage.getItem('dnd_theme_v2')") == current
                migrating.close()
            simple_page = browser.new_page()
            simple_page.add_init_script("""
                localStorage.setItem('dnd_theme_v2', 'simple');
                document.addEventListener('DOMContentLoaded', () => {
                    const image = document.createElement('img');
                    image.dataset.themeSrc = '/static/favicon.ico?theme-image-test=1';
                    document.body.prepend(image);
                });
            """)
            simple_requests = []
            simple_page.on('request', lambda request: simple_requests.append(request))
            assert visit(simple_page, '/').status == 200
            assert not simple_page.locator('#identity-stylesheet').evaluate('(link) => link.hasAttribute("href")')
            assert simple_page.locator('#site-icon').get_attribute('href') == 'data:,'
            assert simple_page.locator('img[data-theme-src]').get_attribute('src') is None
            assert not any(request.resource_type in ('image', 'font') or 'identity.css' in request.url
                           for request in simple_requests)
            with simple_page.expect_request(lambda request: request.resource_type == 'image' and request.url.endswith('/static/favicon.ico?theme-image-test=1')):
                simple_page.get_by_role('combobox', name='Site theme').select_option('modern')
            assert simple_page.locator('img[data-theme-src]').get_attribute('src') == '/static/favicon.ico?theme-image-test=1'
            simple_page.get_by_role('combobox', name='Site theme').select_option('simple')
            assert simple_page.locator('img[data-theme-src]').get_attribute('src') is None
            simple_page.close()
            without_js = browser.new_page(java_script_enabled=False)
            fallback_requests = []
            without_js.on('request', lambda request: fallback_requests.append(request.url))
            assert visit(without_js, '/').status == 200
            assert any('identity.css' in url for url in fallback_requests)
            without_js.close()
            portuguese = browser.new_page(locale='pt-BR')
            assert visit(portuguese, '/').status == 200
            expect(portuguese.get_by_role('heading', name='Sua privacidade')).to_be_visible()
            portuguese.close()
            page = browser.new_page()
            visit(page, '/m/spells/by-rulebooks/')
            assert page.url.rstrip('/') == BASE + '/spells/by-rulebooks'
            visit(page, '/')
            page.set_viewport_size({'width': 360, 'height': 600})
            page.get_by_role('button', name='Toggle catalog menu').click()
            expect(page.locator('#catalog-sidebar')).to_be_visible()
            page.set_viewport_size({'width': 1440, 'height': 750})
            expect(page.locator('#catalog-sidebar')).to_be_visible()
            page.close()
            if REAL_DATA:
                page = browser.new_page()
                visit(page, '/')
                destinations = set(page.locator('#catalog-sidebar a[href]').evaluate_all(
                    '(links) => links.map((link) => link.getAttribute("href"))'))
                for path in sorted(destinations):
                    response = page.request.get(BASE + path)
                    assert response.status == 200, f'Navigation destination {path}: {response.status}'
                for path in ('/rulebooks/', '/feats/', '/monsters/', '/races/', '/items/',
                             '/skills/', '/languages/', '/rules/', '/deities/',
                             '/spells/domains/', '/spells/descriptors/'):
                    response = page.request.get(BASE + path + '?name=a')
                    assert response.status == 200, f'Filtered category {path}: {response.status}'
                response = page.request.get(BASE + '/classes/?character_class__name=a')
                assert response.status == 200, f'Filtered classes: {response.status}'
                assert visit(page, '/search/').status == 200
                categories = page.locator('#catalog-category option').evaluate_all(
                    '(options) => options.map((option) => option.value).filter(Boolean)')
                for category in categories:
                    response = page.request.get(BASE + '/search/?q=a&category=' + category)
                    assert response.status == 200, f'Search category {category}: {response.status}'
                for path, expected in (
                    ('/spells/?name=Elation&class_levels__slug=wizard&spellclasslevel__level=3', '1 spell found.'),
                    ('/spells/?name=Elation&class_levels__slug=wizard&spellclasslevel__level=2', '0 spells found.'),
                    ('/spells/?class_levels__slug=wizard&spellclasslevel__level=0', '53 spells found.'),
                    ('/spells/?name=unfindable-nonsense-zzzzz', '0 spells found.'),
                ):
                    assert visit(page, path).status == 200
                    assert page.get_by_text(expected).is_visible(), path
                page.go_back(wait_until='networkidle')
                assert page.get_by_text('53 spells found.').is_visible()
                assert visit(page, '/search/?q=Acid&category=spells').status == 200
                assert page.get_by_text('Acid Splash', exact=True).count() > 0
                assert visit(page, '/search/?q=ácid&category=spells').status == 200
                assert page.get_by_text('Acid Splash', exact=True).count() > 0
                assert visit(page, '/search/?q=a&category=spells&page=2').status == 200
                assert page.get_by_text('Page 2 of').count() > 0
                assert visit(page, '/').status == 200
                search = page.get_by_role('combobox', name='Search the catalog')
                search.fill('Acid')
                expect(page.locator('#site-suggestions a').first).to_be_visible()
                search.press('ArrowDown')
                search.press('Enter')
                assert page.url.startswith(BASE + '/') and '/search/' not in page.url
                assert visit(page, '/').status == 200
                search = page.get_by_role('combobox', name='Search the catalog')
                search.fill('zzzzz-no-catalog-match')
                expect(page.locator('#site-search-status')).to_have_text(
                    'No suggestions. Press Enter to search all content.')
                page.route('**/search/suggest/**', lambda route: route.abort())
                search.fill('Acid')
                expect(page.locator('#site-search-status')).to_have_text(
                    'Suggestions unavailable. Press Enter to search the catalog.')
                if MISSING_IMAGE:
                    assert visit(page, MISSING_IMAGE).status == 200
                    assert page.get_by_role('img', name='Cover unavailable').is_visible()
                page.close()
        finally:
            browser.close()
    print('Browser smoke passed at 360px, 390px, 768px and 1440px.')


if __name__ == '__main__':
    main()
