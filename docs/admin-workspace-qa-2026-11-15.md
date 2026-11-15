# Admin workspace QA — 2026-11-15

## Changes

- Added a catalog workspace to Django's admin home with direct links to the eight main catalog areas and permission-aware Manage/Add actions.
- Kept every registered model, user/group management, and supporting tools under an expandable directory.
- Applied the project's Standard palette and local Inter font to admin navigation, lists, filters, forms, messages and action buttons. The built-in Django light/dark selector continues to work.
- Kept model permissions authoritative: shortcuts are rendered from Django's permission-filtered app list, and direct unauthorized pages remain forbidden.
- Preserved the readable catalog relation labels already released. No schema or catalog-data changes.

## Validation

- 28 Django tests passed, including staff permission boundaries, catalog labels, search, security and sanitization.
- Admin home, a changelist and the spell form were visually reviewed at 360, 390, 768 and 1440 px in light and dark modes. Each page stayed within the viewport; desktop and mobile previews are saved outside Git.
- The Menu label and Theme label now both compute to 13.12 px in Standard, Modern and Simple. The hamburger icon keeps its existing size.
- The local Docker app is running at `http://127.0.0.1:8765/` for review. The administration preview used read-only rendered snapshots and did not create an account or save catalog changes.

## Production release

- PR #3 passed both CI runs and was deployed as commit `192d824df34994dc4100d54353b147d9bb62f1e8` after verifying a MySQL backup restore (58 catalog tables and 4,918 spells).
- Both public hostnames returned HTTP 200. The custom and old admin paths continued to require Cloudflare Access on both hosts.
- The production origin rendered the new admin login route as HTTP 200 with `no-store`; `/admin/login/` returned 404. Admin CSS is deployed with a versioned URL.
- The catalog still has 4,918 spells, UID 10001 runs the app, and all five unrelated Docker containers remained unchanged.
