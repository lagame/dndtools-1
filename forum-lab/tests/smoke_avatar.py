"""Exercise avatar upload and size limits in the local phpBB lab."""

import io
import os
import secrets
import subprocess
import time
from pathlib import Path
from urllib.parse import urljoin

from PIL import Image
from playwright.sync_api import expect, sync_playwright


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


def image_bytes(width, height, format_name):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "#6750a4").save(buffer, format=format_name)
    return buffer.getvalue() + b"DNDTOOLS_UNTRUSTED_TRAILER"


def main():
    username = "chatqa_" + secrets.token_hex(4)
    password = secrets.token_urlsafe(24)
    helper = ROOT / "forum-lab" / "tests" / "smoke-user.php"
    docker("cp", str(helper), f"{CONTAINER}:/tmp/dndtools-smoke-user.php")
    created = False
    try:
        docker("exec", "-i", "-e", "DND_FORUM_LAB=1", "-u", "www-data", CONTAINER,
               "php", "/tmp/dndtools-smoke-user.php", "create", username, input_text=password)
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

                avatar_url = BASE + "ucp.php?i=profile&mode=avatar"
                page.goto(avatar_url, wait_until="domcontentloaded")
                body = page.locator("body").inner_text()
                assert "300 pixels" in body and "512.00 KiB" in body
                assert "pixels pixels" not in body
                accepted = page.locator('input[name="avatar_upload_file"]').get_attribute("accept")
                assert accepted == ".gif,.jpg,.jpeg,.png,.webp,.avif"

                for extension, format_name, mime in (
                    ("gif", "GIF", "image/gif"),
                    ("jpg", "JPEG", "image/jpeg"),
                    ("png", "PNG", "image/png"),
                    ("webp", "WEBP", "image/webp"),
                    ("avif", "AVIF", "image/avif"),
                ):
                    payload = image_bytes(300, 300, format_name)
                    if extension == "gif":
                        payload = payload.removesuffix(b"DNDTOOLS_UNTRUSTED_TRAILER")
                    page.locator('input[name="avatar_upload_file"]').set_input_files({
                        "name": f"avatar.{extension}", "mimeType": mime,
                        "buffer": payload,
                    })
                    time.sleep(6)
                    page.locator('input[name="submit"]').click()
                    post_result = page.locator("body").inner_text()[:1100]
                    page.goto(avatar_url, wait_until="domcontentloaded")
                    avatar = page.locator("#ucp img.avatar").first
                    assert avatar.count() == 1, f"{extension}: {post_result}"
                    expect(avatar).to_be_visible()
                    source = avatar.get_attribute("src") or ""
                    assert "avatar=" in source and ".webp" in source
                    response = page.request.get(urljoin(page.url, source))
                    assert response.status == 200, f"{extension}: {response.status} {source}"
                    assert response.headers["content-type"].startswith("image/webp")
                    assert b"DNDTOOLS_UNTRUSTED_TRAILER" not in response.body()
                    assert Image.open(io.BytesIO(response.body())).size == (300, 300)
                    thumbnail = page.request.get(urljoin(page.url, source + "&thumb=1"))
                    assert thumbnail.status == 200, f"{extension}: thumbnail unavailable"
                    assert thumbnail.headers["content-type"].startswith("image/webp")
                    assert Image.open(io.BytesIO(thumbnail.body())).size == (64, 64)

                page.locator('input[name="avatar_upload_file"]').set_input_files({
                    "name": "portrait.jpg", "mimeType": "image/jpeg",
                    "buffer": image_bytes(200, 300, "JPEG"),
                })
                time.sleep(6)
                page.locator('input[name="submit"]').click()
                page.goto(avatar_url, wait_until="domcontentloaded")
                avatar = page.locator("#ucp img.avatar").first
                expect(avatar).to_be_visible()
                response = page.request.get(urljoin(page.url, avatar.get_attribute("src")))
                assert Image.open(io.BytesIO(response.body())).size == (200, 300)

                page.locator('input[name="avatar_upload_file"]').set_input_files({
                    "name": "oversized.jpg", "mimeType": "image/jpeg",
                    "buffer": image_bytes(400, 300, "JPEG"),
                })
                time.sleep(6)
                page.locator('input[name="submit"]').click()
                page.goto(avatar_url, wait_until="domcontentloaded")
                avatar = page.locator("#ucp img.avatar").first
                response = page.request.get(urljoin(page.url, avatar.get_attribute("src")))
                assert Image.open(io.BytesIO(response.body())).size == (300, 225)

                sample = os.environ.get("DNDTOOLS_AVATAR_SAMPLE")
                if sample:
                    expected = Image.open(sample).size
                    scale = min(1, 300 / expected[0], 300 / expected[1])
                    expected = tuple(max(1, round(side * scale)) for side in expected)
                    page.locator('input[name="avatar_upload_file"]').set_input_files(sample)
                    time.sleep(6)
                    page.locator('input[name="submit"]').click()
                    page.goto(avatar_url, wait_until="domcontentloaded")
                    avatar = page.locator("#ucp img.avatar").first
                    expect(avatar).to_be_visible()
                    response = page.request.get(urljoin(page.url, avatar.get_attribute("src")))
                    assert response.status == 200
                    assert Image.open(io.BytesIO(response.body())).size == expected

                original_src = avatar.get_attribute("src")
                page.locator('input[name="avatar_upload_file"]').set_input_files({
                    "name": "not-a-jpeg.jpg", "mimeType": "image/jpeg",
                    "buffer": image_bytes(100, 100, "PNG"),
                })
                time.sleep(6)
                page.locator('input[name="submit"]').click()
                assert "possível vetor de ataque" in page.locator("body").inner_text()
                page.goto(avatar_url, wait_until="domcontentloaded")
                assert page.locator("#ucp img.avatar").first.get_attribute("src") == original_src
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                print("GIF, JPEG, PNG, WebP, AVIF reencoded; trailer removed; 300px limit and resizing verified; disguised file rejected; mobile width verified.")
            finally:
                browser.close()
    finally:
        if created:
            docker("exec", "-e", "DND_FORUM_LAB=1", "-u", "www-data", CONTAINER,
                   "php", "/tmp/dndtools-smoke-user.php", "delete", username)


if __name__ == "__main__":
    main()
