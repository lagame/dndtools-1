# Catalog label regression QA — 2026-11-15

## Change

- Replaced the 33 legacy Python 2 `__unicode__` model methods with `__str__` so current Django renders catalog names in relations, admin lists, filters and selection fields.
- Added a domain-variant label containing its domain and sourcebook, matching the existing class/skill variant pattern.
- Updated the editorial feed's explicit string conversion. No fields, database schema or catalog records change.
- Additional administration workspace styling remains deferred and is excluded from this release.

## Validation

- All 26 Django tests passed, including regressions for monster/spell selection labels, class-variant lists and public item relations/prerequisites.
- `makemigrations --check --dry-run` found no changes.
- A read-only real-catalog rendering audit initially used the test client's default hostname and was rejected by `ALLOWED_HOSTS`; the audit was rerun with the configured local hostname.
- The corrected read-only audit passed for all 33 registered catalog models with data, the class-variant and monster lists, and the public Absorbing Shield detail. No generic `Model object (ID)` labels remained in those rendered pages.
- The public-site release still uses the manual workflow and its verified MySQL backup.
