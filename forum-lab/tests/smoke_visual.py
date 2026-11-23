"""Check guest forum layout and shared themes in the local gateway."""

import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


BASE = "http://127.0.0.1:18766/forum/"
THEMES = ("standard", "modern", "simple", "dark", "oled")


def main():
    output = Path(os.environ["DND_QA_OUTPUT"]) if os.environ.get("DND_QA_OUTPUT") else None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(BASE, wait_until="domcontentloaded")
            expect(page.locator(".dnd-forum-header")).to_be_visible()
            expect(page.locator("#stoker-chat")).to_have_count(0)  # Guests cannot read chat.
            assert page.locator("a.forumtitle").count() == 9
            expect(page.get_by_role("link", name="Encontre uma mesa")).to_be_visible()
            expect(page.get_by_role("link", name="Eventos de RPG")).to_be_visible()

            for width in (390, 1440):
                page.set_viewport_size({"width": width, "height": 900})
                for theme in THEMES:
                    page.locator("#theme-select").select_option(theme)
                    expect(page.locator("html")).to_have_attribute("data-theme", theme)
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= window.innerWidth + 1"
                    ), f"Horizontal overflow at {width}px in {theme} theme"
                    if output and theme in ("standard", "oled"):
                        output.mkdir(parents=True, exist_ok=True)
                        page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
                        page.screenshot(path=str(output / f"forum-{theme}-{width}.png"))
            page.set_viewport_size({"width": 390, "height": 844})
            page.get_by_role("link", name="Apresentações e ajuda").click()
            welcome_row = page.locator("li.row").filter(
                has=page.get_by_role("link", name="Bem-vindo ao fórum D&D Tools")
            )
            expect(welcome_row.get_by_text("Ronassic").first).to_be_visible()
            assert "Visitante" not in welcome_row.inner_text()
            page.get_by_role("link", name="Regras do fórum D&D Tools").click()
            expect(page.get_by_text("1. Respeite as pessoas")).to_be_visible()
            expect(page.get_by_text("4. Organize o assunto para que outras pessoas o encontrem")).to_be_visible()
            expect(page.get_by_text("9. Ajude a moderação")).to_be_visible()
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth + 1"
            ), "Forum rules topic has horizontal overflow at 390px"
            page.goto(BASE, wait_until="domcontentloaded")
            page.get_by_role("link", name="Apresentações e ajuda").click()
            page.get_by_role("link", name="Bem-vindo ao fórum D&D Tools").click()
            expect(page.get_by_text("Começando por mim:")).to_be_visible()
            expect(page.get_by_text("ex-administrador do SpellBrasil")).to_be_visible()
            assert page.locator(
                'a[href="https://chat.whatsapp.com/EYOrv7ZcCWVHEw6CTPFHBe"]'
            ).count() >= 2
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth + 1"
            ), "Welcome topic has horizontal overflow at 390px"
            page.goto(BASE + "viewtopic.php?t=5", wait_until="domcontentloaded")
            expect(page.get_by_text("Encontrou um erro em uma página do catálogo", exact=False)).to_be_visible()
            assert "Inclua o link da ficha" not in page.locator("body").inner_text()
            page.goto(BASE + "viewtopic.php?t=9", wait_until="domcontentloaded")
            expect(page.get_by_role("heading", name="Como compartilhar um encontro").first).to_be_visible()
            expect(page.get_by_text("Este tópico é só um guia.", exact=False)).to_be_visible()
            assert "Regra que gerou dúvida" not in page.locator("body").inner_text()
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth + 1"
            ), "Encounter guide has horizontal overflow at 390px"
            print("Nine forums, rules, revised guides, signature, links and five responsive themes passed.")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
