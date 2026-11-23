"""Exercise the local catalog-to-phpBB editor and linked topic flow."""

import re
import secrets
import subprocess
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
CONTAINER = "dndtools-forum_lab-1"
BASE = "http://127.0.0.1:18766"
RECORD = "/spells/dragons-of-faerun--26/abate-dracorage--1094/"


def docker(*args, input_text=None):
    result = subprocess.run(
        ["docker", *args], input=input_text, text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


def main():
    username = "chatqa_" + secrets.token_hex(4)
    password = secrets.token_urlsafe(24)
    title = "Catalog discussion QA " + secrets.token_hex(4)
    docker("cp", str(ROOT / "forum-lab/tests/smoke-user.php"),
           f"{CONTAINER}:/tmp/dndtools-smoke-user.php")
    docker("cp", str(ROOT / "forum-lab/tests/cleanup-discussion.php"),
           f"{CONTAINER}:/tmp/dndtools-cleanup-discussion.php")
    created = False
    topic_id = None
    try:
        docker("exec", "-i", "-e", "DND_FORUM_LAB=1", "-u", "www-data", CONTAINER,
               "php", "/tmp/dndtools-smoke-user.php", "create", username,
               input_text=password)
        created = True
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": 390, "height": 844})
                page.context.add_cookies([{
                    "name": "django_language", "value": "pt-br", "domain": "127.0.0.1", "path": "/"
                }])
                page.goto(BASE + "/forum/ucp.php?mode=login")
                page.locator('input[name="username"]').fill(username)
                page.locator('input[name="password"]').fill(password)
                time.sleep(6)  # phpBB rejects immediate form submissions.
                page.locator('input[name="login"]').click()
                assert username in page.locator("body").inner_text()

                page.goto(BASE + RECORD)
                expect(page.locator(".record-discussions-frame")).to_be_visible()
                frame = page.frame_locator(".record-discussions-frame")
                expect(frame.get_by_role("heading", name="Discutir: Abate Dracorage")).to_be_visible()
                frame.get_by_role("link", name="Iniciar discussão").click()
                expect(frame.locator('input[name="subject"]')).to_be_visible()
                assert frame.locator("body").evaluate(
                    "el => el.scrollWidth <= el.clientWidth + 1"
                ), "Native editor overflows horizontally on mobile"
                assert frame.locator('input[name="dnd_kind"]').input_value() == "spell"
                assert frame.locator('input[name="dnd_id"]').input_value() == "1094"
                frame.locator('input[name="subject"]').fill(title)
                frame.locator('textarea[name="message"]').fill("Testando a conversa ligada à ficha.")
                time.sleep(6)
                frame.locator('input[name="post"]').click()
                expect(frame.get_by_text(title).first).to_be_visible(timeout=15000)
                topic_url = frame.locator('link[rel="canonical"]').get_attribute("href")
                if not topic_url:
                    topic_url = frame.locator("body").evaluate("el => el.ownerDocument.location.href")
                match = re.search(r"[?&]t=(\d+)", topic_url)
                assert match, f"No topic ID after posting: {topic_url}"
                topic_id = int(match.group(1))
                catalog_link = frame.get_by_role("link", name="Abate Dracorage")
                expect(catalog_link).to_be_visible()
                assert catalog_link.get_attribute("href").startswith("/pt-br/spells/")

                page.reload()
                frame = page.frame_locator(".record-discussions-frame")
                expect(frame.get_by_role("link", name=title)).to_be_visible()
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= window.innerWidth + 1"
                ), "Catalog overflows horizontally on mobile"
                assert frame.locator("body").evaluate(
                    "el => el.scrollWidth <= el.clientWidth + 1"
                ), "Embedded forum overflows horizontally on mobile"
                page.set_viewport_size({"width": 1440, "height": 900})
                expect(frame.get_by_role("link", name=title)).to_be_visible()
                print("Linked topic, native editor, language, mobile and desktop passed.")
            finally:
                browser.close()
    finally:
        if topic_id:
            docker("exec", "-e", "DND_FORUM_LAB=1", "-u", "www-data", CONTAINER,
                   "php", "/tmp/dndtools-cleanup-discussion.php", str(topic_id))
        if created:
            docker("exec", "-e", "DND_FORUM_LAB=1", "-u", "www-data", CONTAINER,
                   "php", "/tmp/dndtools-smoke-user.php", "delete", username)


if __name__ == "__main__":
    main()
