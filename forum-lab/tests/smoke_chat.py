"""Exercise the local forum chat with a disposable account and browser."""

import io
import os
import secrets
import subprocess
import time
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import expect, sync_playwright
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
CONTAINER = "dndtools-forum_lab-1"
BASE = "http://127.0.0.1:18766/forum/"


def docker(*args, input_text=None):
    result = subprocess.run(
        ["docker", *args], input=input_text, text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


def contrast_ratio(page, selector):
    return page.locator(selector).first.evaluate("""element => {
        const rgb = value => (value.match(/[\\d.]+/g) || []).map(Number);
        const fg = rgb(getComputedStyle(element).color);
        let background = element;
        while (background && rgb(getComputedStyle(background).backgroundColor)[3] === 0) {
            background = background.parentElement;
        }
        const bg = rgb(getComputedStyle(background || document.body).backgroundColor);
        const luminance = channels => channels.slice(0, 3).map(v => {
            v /= 255;
            return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4;
        }).reduce((sum, value, i) => sum + value * [.2126, .7152, .0722][i], 0);
        const a = luminance(fg), b = luminance(bg);
        return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
    }""")


def main():
    username = "chatqa_" + secrets.token_hex(4)
    password = secrets.token_urlsafe(24)
    helper = ROOT / "forum-lab" / "tests" / "smoke-user.php"
    qa_output = Path(os.environ["DND_QA_OUTPUT"]) if os.environ.get("DND_QA_OUTPUT") else None
    docker("cp", str(helper), f"{CONTAINER}:/tmp/dndtools-smoke-user.php")
    created = False
    try:
        docker("exec", "-i", "-e", "DND_FORUM_LAB=1", "-u", "www-data",
               CONTAINER, "php", "/tmp/dndtools-smoke-user.php", "create_new", username,
               input_text=password)
        created = True
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": 390, "height": 844})
                page.goto(BASE + "ucp.php?mode=login", wait_until="domcontentloaded")
                page.locator('input[name="username"]').fill(username)
                page.locator('input[name="password"]').fill(password)
                time.sleep(6)  # phpBB rejects forms submitted immediately after loading.
                page.locator('input[name="login"]').click()
                assert username in page.locator("body").inner_text(), "Login did not complete"

                page.goto(BASE, wait_until="domcontentloaded")
                expect(page.locator("#stoker-chat")).to_be_visible()
                expect(page.locator("#stoker-chat-text")).to_be_visible()
                expect(page.locator("#stoker-chat-send")).to_have_text("Enviar")
                expect(page.locator("#stoker-chat-emoji-btn")).to_be_visible()
                page.locator("#stoker-chat-emoji-btn").click()
                expect(page.locator("#stoker-chat-emoji-picker")).to_be_visible()
                page.locator("#stoker-chat-emoji-btn").click()
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= window.innerWidth + 1"
                ), "Forum has horizontal overflow at 390px"

                page.locator(".dnd-forum-language a", has_text="EN").click()
                expect(page.locator("#stoker-chat-send")).to_have_text("Send")
                page.locator(".dnd-forum-links a", has_text="Catalog").click()
                expect(page.locator("html")).to_have_attribute("lang", "en")
                page.locator(".language-picker a", has_text="PT-BR").click()
                expect(page.locator("html")).to_have_attribute("lang", "pt-BR")
                page.locator(".forum-nav-link").click()
                expect(page.locator("#stoker-chat-send")).to_have_text("Enviar")

                page.goto(BASE + "ucp.php?i=ucp_prefs&mode=personal", wait_until="domcontentloaded")
                page.locator('select[name="lang"]').select_option("en")
                time.sleep(6)
                page.locator('input[name="submit"]').click()
                page.goto(BASE, wait_until="domcontentloaded")
                expect(page.locator("#stoker-chat-send")).to_have_text("Send")
                page.locator(".dnd-forum-links a", has_text="Catalog").click()
                expect(page.locator("html")).to_have_attribute("lang", "en")
                page.locator(".language-picker a", has_text="PT-BR").click()
                page.locator(".forum-nav-link").click()
                expect(page.locator("#stoker-chat-send")).to_have_text("Enviar")

                page.locator("#theme-select").select_option("oled")
                expect(page.locator("html")).to_have_attribute("data-theme", "oled")
                page.locator(".dnd-forum-links a", has_text="Catálogo").click()
                expect(page.locator("html")).to_have_attribute("data-theme", "oled")
                page.locator(".forum-nav-link").click()
                expect(page.locator("html")).to_have_attribute("data-theme", "oled")
                if qa_output:
                    qa_output.mkdir(parents=True, exist_ok=True)
                    page.evaluate("window.scrollTo(0, 0)")
                    page.screenshot(path=str(qa_output / "forum-chat-mobile-oled.png"), full_page=True)

                avatar_buffer = io.BytesIO()
                Image.new("RGB", (200, 300), "#6750a4").save(avatar_buffer, "JPEG")
                page.goto(BASE + "ucp.php?i=profile&mode=avatar", wait_until="domcontentloaded")
                page.locator('input[name="avatar_upload_file"]').set_input_files({
                    "name": "portrait.jpg", "mimeType": "image/jpeg",
                    "buffer": avatar_buffer.getvalue(),
                })
                time.sleep(6)
                page.locator('input[name="submit"]').click()
                page.goto(BASE + "ucp.php?i=profile&mode=avatar", wait_until="domcontentloaded")
                original_src = page.locator("#ucp img.avatar").first.get_attribute("src")
                original = page.request.get(urljoin(page.url, original_src))
                assert original.status == 200
                assert Image.open(io.BytesIO(original.body())).size == (200, 300)

                page.goto(BASE + "memberlist.php", wait_until="domcontentloaded")
                member_avatar = page.locator("#memberlist tr", has_text=username).locator(".member-avatar-thumb img")
                expect(member_avatar).to_be_visible()
                member_src = member_avatar.get_attribute("src")
                assert "thumb=1" in member_src
                member_image = page.request.get(urljoin(page.url, member_src))
                assert member_image.status == 200, (member_src, member_image.status, member_image.body()[:150])
                assert Image.open(io.BytesIO(member_image.body())).size == (64, 64)
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                header_avatar = page.locator(".header-avatar img").first
                assert "thumb=1" in header_avatar.get_attribute("src")
                if qa_output:
                    page.screenshot(path=str(qa_output / "forum-members-mobile-oled.png"), full_page=True)

                for theme in ("standard", "modern", "simple", "dark", "oled"):
                    page.locator("#theme-select").select_option(theme)
                    page.goto(BASE + "memberlist.php", wait_until="domcontentloaded")
                    expect(page.locator("html")).to_have_attribute("data-theme", theme)
                    for selector in ("#memberlist thead th.name", "#memberlist tbody td:first-child", "#memberlist tbody td.info", "#memberlist tbody td a:not(.username-coloured)"):
                        if page.locator(selector).count():
                            assert contrast_ratio(page, selector) >= 4.5, (theme, selector)
                    if qa_output and theme == "standard":
                        page.screenshot(path=str(qa_output / "forum-members-mobile-standard.png"), full_page=True)
                    page.goto(BASE + "memberlist.php?mode=team", wait_until="domcontentloaded")
                    for selector in ("#team thead th.name", "#team tbody td:first-child", "#team tbody td:nth-child(2)", "#team tbody tr:last-child td"):
                        assert contrast_ratio(page, selector) >= 4.5, (theme, selector)
                    page.goto(BASE + "app.php/chat", wait_until="domcontentloaded")
                    for selector in ("#stoker-chat-text", "#stoker-chat-send"):
                        assert contrast_ratio(page, selector) >= 4.5, (theme, selector)

                page.locator("#theme-select").select_option("oled")

                page.goto(BASE + "app.php/chat", wait_until="domcontentloaded")
                expect(page.locator("#stoker-chat-text")).to_be_visible()

                message = "Teste local do chat " + secrets.token_hex(3)
                page.locator("#stoker-chat-text").fill(message)
                page.locator("#stoker-chat-send").click()
                own_message = page.locator(".stoker-chat-msg").filter(has_text=message)
                expect(own_message).to_be_visible(timeout=10000)
                avatar_src = own_message.locator(".stoker-chat-avatar img").get_attribute("src")
                assert avatar_src.startswith("/forum/download/file.php?avatar="), avatar_src
                assert "thumb=1" in avatar_src
                assert own_message.locator(".stoker-chat-avatar img").get_attribute("width") == "32"
                assert own_message.locator(".stoker-chat-avatar img").get_attribute("height") == "32"
                chat_image = page.request.get(urljoin(page.url, avatar_src))
                assert chat_image.status == 200, f"Chat avatar is broken: {avatar_src}"
                assert Image.open(io.BytesIO(chat_image.body())).size == (64, 64)
                if qa_output:
                    page.set_viewport_size({"width": 1440, "height": 900})
                    page.evaluate("window.scrollTo(0, 0)")
                    page.screenshot(path=str(qa_output / "forum-chat-desktop-oled.png"), full_page=True)
                    page.set_viewport_size({"width": 390, "height": 844})
                own_message.locator(".stoker-chat-menu-toggle").click()
                own_message.locator(".stoker-chat-delete-btn").click()
                page.get_by_role("button", name="Sim").click()
                expect(own_message).to_have_count(0, timeout=10000)
                print("Mobile chat, member and header thumbnails, original avatar, language sync, theme, post and delete passed.")
            finally:
                browser.close()
    finally:
        if created:
            docker("exec", "-e", "DND_FORUM_LAB=1", "-u", "www-data",
                   CONTAINER, "php", "/tmp/dndtools-smoke-user.php", "delete", username)


if __name__ == "__main__":
    main()
