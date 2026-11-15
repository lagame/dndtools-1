# Admin login security QA — 2026-11-15

## Changes

- Branded the Django admin login in the Standard visual family, with responsive controls and a back link. The login retains Django's CSRF token, form errors and `next` field.
- Added a shared MySQL-backed, username-based lockout: five failed attempts in a rolling 15-minute window return HTTP 429. A different account remains usable. The login GET remains available to explain the state.
- Enabled Django's standard password checks with a minimum length of 14 characters for new/changed passwords. Existing passwords are not changed automatically.
- Kept administrator HTML responses out of caches with `Cache-Control: no-store`.
- Excluded client IPs from the Axes attempt table and disabled its successful-login access log. The privacy page describes the remaining failed-login records.

## Validation

- A private local MySQL backup was created outside Git and restored into a disposable database before local migrations. The restored catalog contained 58 content tables and 4,918 spells.
- Local `axes` migrations applied successfully; the catalog remained available.
- 20 Django tests passed, including CSRF rejection, cross-client lockout with changing user agents, an unaffected second account, admin access and password validation.
- `check --deploy --fail-level WARNING` passed with one intentional `axes.W006` silence. Axes warns about username-only limits; the repository tests cover the selected behavior. An IP limit would treat visitors behind the shared tunnel IP as one client.
- `makemigrations --check --dry-run` found no model changes.
- Browser smoke passed at 360, 390, 768 and 1440 pixels. Login screenshots at 390 and 1440 pixels were reviewed locally, with no horizontal overflow and the CSS, CSRF field and `no-store` header present.

## Before a production release

- Create and verify a Cloudflare Access policy for `/admin` and `/admin/*` on both public hostnames, limited to the administrator. This is an external configuration and is not yet verified.
- Create the production superuser interactively on the VPS after the release; do not publish the credentials. The local database had no active staff or superuser before this change. The production account inventory has not been verified.
- Review the controller identity and infrastructure log/backup retention described in the identity and privacy QA report. This change alone is not a legal compliance certification.
- No production deployment was performed for this branch.
