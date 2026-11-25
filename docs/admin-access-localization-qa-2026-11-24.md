# Admin Access and PT-BR interface — 24 November 2026

## Observed behavior

- Production still runs `2758bc8e1ad5d57df5db54b7aeb53141cc06a01a`. Its middleware validates the Cloudflare Access JWT but only creates a Django session automatically for active collaborators. The configured owner is intentionally excluded, so a completed Cloudflare MFA challenge leads to the separate Django password screen. A read-only check found exactly one configured owner account, one account with the configured email, and active/staff/superuser flags all enabled.
- The user's screenshot has PT-BR selected and Django's built-in controls translated, while the custom catalog dashboard remains in English. Its headings, actions and help text were literal strings without translation tags; the legacy model labels were also supplied to admin templates in English.

## Changes

- After a signed Access assertion passes the existing signature, issuer, audience and expiry checks, a GET or HEAD request creates a Django session for the unique configured owner account. The account must have the exact configured username and email and be active, staff and superuser. Missing or invalid assertions, ambiguous owner email, invalid account flags and a conflicting existing session do not grant access. The collaborator invitation and authorization path remains in place. Cloudflare Access must continue to require MFA for the owner policy.
- The catalog dashboard, resource list, navigation labels, list and form titles, primary field labels, inline headers, breadcrumbs, creation action and record count now use PT-BR translations when selected. EN remains available. Catalog record values and legacy source text are not rewritten.
- A follow-up review of the owner's local screenshot found English table headings and filter titles on the Talentos list. The catalog changelist now uses the existing localized field labels for these controls in PT-BR and EN.
- The README now describes the owner session correctly. No database migration or production data edit is part of this change.

## Validation and limits

- Focused Access tests covered automatic owner login without a Django password, missing identity, duplicate email, inactive/staff/superuser flag failures, and a conflicting session. The complete Django suite passed 108 tests before the follow-up label change; all 59 editorial tests passed afterward. The migration drift check and deployment check also passed locally. CI for the follow-up is pending.
- Playwright exercised the local admin dashboard, editorial area and feat list at 390 and 1440 px in PT-BR and EN. The four dashboard screenshots were visually reviewed; there was no horizontal page overflow. A separate desktop review confirmed translated feat list and creation form headings, labels and inline headers. These checks used an isolated, disposable MySQL test database.
- The live Cloudflare MFA-to-Django transition and account switching cannot be verified on the old production version. After the code is deployed, verify those flows through the real protected route on both public hostnames. The Access JWT validation follows [Cloudflare's origin guidance](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/).
- A local server is running at `http://127.0.0.1:8765/admin/login/` against the existing local catalog. The local MySQL backup was restored into a disposable schema and verified before local migrations; the local catalog still has 4,918 spells and 165 items. Opening a visible Chrome window from this agent was blocked by the terminal policy, and the computer-use pipe was unavailable. The owner opened the local page and supplied screenshots; a refreshed review after the follow-up change remains pending. No production deployment was attempted.
