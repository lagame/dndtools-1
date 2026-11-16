# Bilingual catalog and editorial workflow: QA status (2026-11-16)

## Implemented

- English catalog URLs remain valid; `/pt-br/` offers translated interface labels and approved full-record translations with English fallback.
- Owner-reviewed proposals cover additions, corrections, removals and PT-BR translations for recovered catalog models, creature templates, and six additional D&D 3.5 mechanic types. Removal approval blocks linked records to avoid cascading content loss.
- Collaborator grants are scoped by resource and action. Direct Django Admin mutations are owner-only, even when a collaborator receives ordinary model permissions.
- Invitations use one-time codes and signed Cloudflare Access identity binding. Each proposal sends an owner email alert when private SMTP is configured.
- New catalog types have public list/detail/search pages after approval. The public menu links to all seven sections.

## Verified locally

- A private MySQL snapshot was taken and restore-checked before local migrations. The restored catalog contained 58 tables and 4,918 spells. No database or backup is in Git.
- `python manage.py test dnd --keepdb --noinput`: 49 tests passed against MySQL, including removal approval, stale proposals, dependent-link protection and translation cleanup.
- `python manage.py migrate --noinput`: `dnd.0005_editorial_removal` applied to the private local MySQL database after the verified snapshot.
- Editorial registry audit: all 47 catalog models are supported. News and static pages remain owner-only in Django Admin; the other four unsupported models are editorial workflow metadata.
- `python manage.py makemigrations --check --dry-run`: no drift.
- `python manage.py check --deploy --fail-level WARNING` with synthetic production settings: no issues.
- All 184 public templates compile; PT-BR messages compile with no untranslated or fuzzy entries except the empty PO header.
- Chrome browser smoke: desktop and mobile widths 360, 390, 768 and 1440 px against the local real catalog.
- Two GitHub CI checks passed for commit `3239d81` on the draft PR.
- On 2026-11-16, anonymous requests to the old and replacement admin base/login paths on both public hosts redirected to the same Cloudflare Access application. Both public home pages returned HTTP 200. This confirms edge interception, not the current Allow/MFA policy contents.
- The VPS private `.env` was backed up before adding the Access team/audience and Gmail SMTP settings; it remains root-owned with mode `0600`. The VPS reached `smtp.gmail.com:587`, completed STARTTLS and authenticated with the saved app password. The owner received the test message. No application restart or deploy occurred.
- The owner created the dedicated `DND Tools Collaborators` Access rule group and a separate `DND Tools - Collaborators` Allow policy using that group. Screenshots showed the application with both the existing owner policy and the new collaborator policy, configured for authenticator-app MFA with a 24-hour authentication duration. The owner confirmed saving the application. Group membership after removing extra addresses is owner-reported; no Cloudflare API read has been performed.
- The Cloudflare policy tester approved the active owner identity. Testing the initial collaborator address returned `access.api.error.invalid_user_id`, zero evaluated policies and no user details; the tester explicitly requires a prior login attempt. Its displayed denial is therefore not evidence that the collaborator policy rejected this address.
- A fresh guest sign-in attempt first reached the Cloudflare identity provider but failed with `Cloudflare sign-in is restricted to members of the account.` The Access user list then showed only the owner. The default Cloudflare identity provider cannot authenticate this guest; a separate One-time PIN method was needed while retaining exact-email Access policy and MFA.
- The owner added One-time PIN alongside the existing Cloudflare identity provider, selected both methods for the D&D Tools Access application and added the collaborator rule group as a second Include rule on the App Launcher policy. A fresh guest session reached the App Launcher with the correct email and `Onetimepin` identity provider. The guest enrolled a TOTP authenticator and completed the D&D Tools Access challenge, reaching the Django login page on the protected production route. This confirms guest authentication, App Launcher authorization, MFA and edge access on the apex host.
- Read-only production check at deployed commit `c506fd5`: zero Django users have the guest email, and the editorial invitation table does not yet exist. The Django login prompt after Cloudflare MFA is expected until this branch is deployed and the owner creates an invitation. No credentials or database rows were changed.
- The new schema migrations contain no data insertion or sourcebook prose. Publication rights still need review before accepting future translated prose or new excerpts.

## Release gates still open

- After deployment, create an invitation and verify Django activation/sign-in; also verify the protected www host with the guest identity. The interface and workflow are ready; existing catalog prose stays in English until approved translation proposals exist.
- The VPS and public domains have not been updated from this branch.
