# Bilingual catalog and editorial workflow: QA status (2026-11-16)

## Implemented

- English catalog URLs remain valid; `/pt-br/` offers translated interface labels and approved full-record translations with English fallback.
- Owner-reviewed proposals cover additions, corrections and PT-BR translations for recovered catalog models, creature templates, and six additional D&D 3.5 mechanic types.
- Collaborator grants are scoped by resource and action. Direct Django Admin mutations are owner-only, even when a collaborator receives ordinary model permissions.
- Invitations use one-time codes and signed Cloudflare Access identity binding. Each proposal sends an owner email alert when private SMTP is configured.
- New catalog types have public list/detail/search pages after approval. The public menu links to all seven sections.

## Verified locally

- A private MySQL snapshot was taken and restore-checked before local migrations. The restored catalog contained 58 tables and 4,918 spells. No database or backup is in Git.
- `python manage.py test dnd --keepdb --noinput`: 46 tests passed against MySQL.
- `python manage.py makemigrations --check --dry-run`: no drift.
- `python manage.py check --deploy --fail-level WARNING` with synthetic production settings: no issues.
- All 184 public templates compile; PT-BR messages compile with no untranslated or fuzzy entries except the empty PO header.
- Chrome browser smoke: desktop and mobile widths 360, 390, 768 and 1440 px against the local real catalog.

## Release gates still open

- Confirm whether collaborators may propose deletions; no contributor delete action is implemented yet. Owner-only Django Admin deletion remains available.
- Configure and test private SMTP credentials on the VPS, a dedicated Cloudflare Access group and policy for the configured admin route on both hosts, and the Access audience values. A real email delivery and a real invited collaborator sign-in have not yet been verified.
- Review source rights before publishing translated catalog prose or new source excerpts. The interface and workflow are ready; existing catalog prose stays in English until approved translation proposals exist.
- The VPS and public domains have not been updated from this branch.
