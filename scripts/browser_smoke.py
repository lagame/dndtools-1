"""Check the public shell, search, and mobile layout in a real browser."""

import os
import time

from playwright.sync_api import sync_playwright


BASE = os.environ.get('DND_TEST_BASE_URL', 'http://127.0.0.1:8765')


def main():
    with sync_playwright() as playwright:
        executable = os.environ.get('DND_BROWSER_EXECUTABLE')
        browser = playwright.chromium.launch(headless=True, executable_path=executable)
        try:
            for width in (390, 1440):
                page = browser.new_page(viewport={'width': width, 'height': 850})
                for attempt in range(10):
                    try:
                        response = page.goto(BASE + '/', wait_until='networkidle', timeout=10000)
                        break
                    except Exception:
                        if attempt == 9:
                            raise
                        time.sleep(1)
                assert response.status == 200
                assert page.get_by_role('searchbox', name='Search the catalog').count() == 1
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                assert page.goto(BASE + '/search/?q=ember', wait_until='networkidle').status == 200
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                assert page.goto(BASE + '/contacts/', wait_until='networkidle').status == 200
                assert page.get_by_text('Open a project issue').count() >= 1
                page.close()
            page = browser.new_page()
            page.goto(BASE + '/m/spells/', wait_until='networkidle')
            assert page.url.rstrip('/') == BASE + '/spells'
            page.close()
        finally:
            browser.close()
    print('Browser smoke passed at 390px and 1440px.')


if __name__ == '__main__':
    main()
