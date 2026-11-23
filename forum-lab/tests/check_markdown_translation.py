"""Check local Markdown language completeness and the rendered help in both locales."""

import re
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
LANGUAGE = ROOT / "ext" / "alfredoramos" / "markdown" / "language"
HELP_URL = "http://127.0.0.1:18766/forum/app.php/help/markdown"


def keys(locale):
    source = (LANGUAGE / locale / "help" / "markdown.php").read_text(encoding="utf-8")
    return set(re.findall(r"^\s*'([A-Z_]+)'\s*=>", source, re.MULTILINE))


def help_page(locale):
    request = Request(HELP_URL, headers={"Cookie": f"django_language={locale}"})
    with urlopen(request, timeout=10) as response:
        assert response.status == 200, f"{locale}: HTTP {response.status}"
        return response.read().decode("utf-8")


def main():
    english = keys("en")
    portuguese = keys("pt_br")
    assert english == portuguese, f"Missing: {english - portuguese}; extra: {portuguese - english}"

    pt = help_page("pt-br")
    assert "Guia de Markdown" in pt
    assert "Como escrever em negrito?" in pt
    assert "Como criar uma lista de tarefas?" in pt
    assert "Markdown guide" not in pt

    en = help_page("en-us")
    assert "Markdown guide" in en
    assert "Creating bold text" in en
    assert "Creating task list" in en
    assert "Guia de Markdown" not in en

    print(f"Markdown help passed in EN and PT-BR ({len(english)} matching keys).")


if __name__ == "__main__":
    main()
