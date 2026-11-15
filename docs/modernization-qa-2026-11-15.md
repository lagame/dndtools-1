# Modernization QA — 2026-11-15

## Delivered

- Hierarchical navigation shared by desktop and mobile, with direct links, current-page state, expandable subgroups, a modal compact drawer and keyboard controls. The [menu map](navigation-and-filters.md) records original destinations and entries that were only announcements.
- Ranked MySQL catalog search, suggestions and category pagination. Search names and text are case and accent insensitive; the suggestions search names only.
- Spell filters for class and level on the same catalog link, domain and level on the same link, level 0, absent metadata, source and edition, plus active filters and URL state. Existing category filters remain available; invalid legacy filter values display an error and leave the list unfiltered.
- Multiple category selections in legacy filters now count each matching catalog row once.
- The [image inventory](image-inventory.md) and [CSV](image-inventory.csv) record 81 missing file references from 68 books and 13 races. The 46 books and 29 races with no registered image are counted separately. All 33 versioned static images and 20 literal image references were checked. The private media volume was inspected and contained none of the 81 files. No external `<img>` reference was found in the scanned catalog fields. Placeholders preserve the image names in the database; they do not represent recovered images.
- New race illustrations now save after the race receives its ID and resize with the supported Pillow resampling API.

## Local checks

- `docker compose run --rm app python manage.py test dnd --keepdb --noinput`: 14 focused tests passed, including search, case-insensitive text filters, redirects, staff verification, invalid input, duplicate prevention and a new race illustration upload.
- Real MySQL regression: `/feats/?name=Power`, `power` and `POWER` now each return 96 results; before the correction they returned 72, 25 and 0. The same `a`/`A` comparison returned identical totals in 12 catalog sections, including feats, books, classes, monsters, races, items, skills, languages, rules, deities, domains and descriptors.
- `docker compose run --rm app python manage.py audit_catalog`: 43 representative detail pages returned HTTP 200. `import_legacy_sqlite --verify` compared every field of all 50,958 rows in the 58 catalog tables against the private SQLite snapshot.
- `py -3 scripts/browser_smoke.py` with `DND_QA_REAL_DATA=1` and `DND_QA_MISSING_IMAGE_URL=/rulebooks/forgotten-realms-35--4/serpent-kingdoms--24/` against the local MySQL copy: passed at 360, 390, 768 and 1440 px. It visited every link in the catalog sidebar, filtered 12 content sections, queried all 21 search categories, checked the spell class/level mismatch, level 0, no results, search pagination, accent variation, suggestions with keyboard selection plus empty/error states, browser Back, menu focus/closing/resizing, and a rulebook with a missing cover.
- A global `/search/?q=a` request returned HTTP 200 in 229 ms on the local Docker catalog. This is an observation on the local data and hardware, not a production latency guarantee.
- `docker compose --profile production run --rm --no-deps --entrypoint caddy proxy validate --config /etc/caddy/Caddyfile`: valid configuration.
- Real screenshots were saved outside Git in the private backup under `qa/modernization-2026-11-15/`: menu, spell listing and active filters at mobile and desktop widths, and a spell detail at 390 and 1440 px. The menu, filter, listing and detail screenshots were visually reviewed. Screenshots are kept private because they show content from the private catalog.

## Limits and next steps

- The 81 media files remain to be sourced and reviewed before inclusion. The old direct URL `/static/media/rulebook/serpent-kingdoms.jpg` still returns 404 until its file exists. The page for that book shows “Cover unavailable” instead of a broken image.
- The generic category filters still use the legacy `django_filters2` implementation. Their missing-value semantics are not uniform with the new spell filters; this is described in the [filter map](navigation-and-filters.md).
- The complete search uses a short server-side query across catalog tables; no new index was added because the current substring predicates cannot use an ordinary prefix B-tree index. Reassess against production traffic and a full production dataset before considering full-text indexing.
- No VPS deployment or public release was performed. Publication of the private catalog requires a rights decision and deployment preparation described in the [baseline status](modernization-status.md).
