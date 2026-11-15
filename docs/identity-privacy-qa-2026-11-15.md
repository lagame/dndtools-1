# Identity and privacy QA — 2026-11-15

## Scope

- Applied the HeroForge visual family to the existing catalog layout: Inter served locally under its OFL license, lavender surfaces, purple controls, responsive header and cards. The catalog menu, search, filters and detail URLs remain in place.
- Added a bilingual privacy page and an informational notice. Public browsing does not set a D&D Tools cookie. The notice writes a dismissal timestamp to local storage only after a click; it expires after 180 days and is removed on the next visit after expiry.
- Stopped issuing the old ten-year `top_news` cookie and clear the old `top_news`, `disable_social` and `force_desktop` cookies when a visitor returns.
- Updated the project announcement and moved the original announcements into a labelled archive.

## Validation

- `docker compose build app`: passed.
- `docker compose run --rm app python manage.py test dnd --keepdb --noinput`: 16 tests passed.
- `docker compose run --rm app python manage.py makemigrations --check --dry-run`: no changes detected.
- `docker compose run --rm -e DND_DEBUG=0 app python manage.py check --deploy --fail-level WARNING`: no issues.
- `python scripts/browser_smoke.py` with the local MySQL catalog: passed at 360, 390, 768 and 1440 px. It covered navigation, search, filters, privacy notice dismissal, language switching and mobile policy layout. Screenshots are outside Git under the local temporary directory.
- A fresh browser visited the home, spell, feat, contact and privacy pages: no request to a third-party host and no browser cookie were observed.
- Both public hostnames returned HTTP 200 with the D&D Tools title before this branch was published. The visual and privacy work is currently local only.
- GitHub Actions runs [43725902565](https://github.com/lagame/dndtools-1/actions/runs/43725902565) and [43725934765](https://github.com/lagame/dndtools-1/actions/runs/43725934765) passed for commit `fa763fb`. The PR remains a draft and no deployment workflow was triggered.

## Privacy review before release

- The public contact address is `ronassic@gmail.com`; the legal identity of the data controller still needs confirmation.
- The VPS tunnel proxy has no explicit access-log directive. Docker logs for the app and tunnel proxy use `json-file` with three files of 20 MB each, a size limit rather than a time limit. Cloudflare retention and account-level logging settings have not been verified.
- [LGPD Article 9](https://www2.camara.leg.br/legin/fed/lei/2018/lei-13709-14-agosto-2018-787077-normaatualizada-pl.html) calls for clear information about the controller and processing duration. [ANPD's cookie guide](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/anonimizado___guia_de_cookies.pdf) says legitimate interest may be appropriate for strictly necessary cookies after a context-specific assessment. The project's legal basis and controller identity still require the owner's review.
- [Cloudflare's analytics documentation](https://developers.cloudflare.com/observability/logs/datasets/) says retention depends on the dataset and plan. Its exact settings for this account could not be read in this session.
- The policy describes observed browser storage and the known hosting path. A legal review should confirm controller details and the exact infrastructure retention before claiming full LGPD compliance.
- If optional analytics or advertising are later added, they must remain off until the visitor has a real opportunity to accept or refuse them.
