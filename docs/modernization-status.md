# Modernization status — 2026-11-14

## Delivered and verified locally

- Full workspace and Git history were copied to a private backup outside this repository. Consistent SQLite snapshots of both the original and working database passed integrity and isolated restoration checks. The older original has 4,911 spells and 84 existing foreign-key errors; the repaired working snapshot has 4,918 spells and no foreign-key errors.
- Django 5.2 migrations create the catalog schema on MySQL 8.4. The read-only importer copied and compared **all fields of all 50,958 rows in 58 catalog tables**. The unmodeled conditions table was retained; the unrelated HeroForge table was excluded.
- The local Docker stack serves the site from MySQL at `127.0.0.1:8765`. The former failing spell detail, core lists, search, contact and redirects returned expected HTTP statuses. A read-only catalog audit visited 43 representative detail pages with no failures. The public index routes, RSS, sitemap, CSS, conditions and legacy Android page returned 200.
- Backend tests passed for detail rendering, search, mobile redirects, contact behavior and staff verification with CSRF. `makemigrations --check --dry-run` found no drift; `check --deploy --fail-level WARNING` reported no issues with production settings.
- A MySQL dump was created outside the repository and restored to a disposable database. The restored copy contained 58 catalog tables and 4,918 spells.
- Responsive home, spell detail and search pages were visually reviewed at desktop and 390px widths. The browser smoke passed at 390px and 1440px without horizontal page overflow.
- GitHub Actions run 43668890772 passed on the fork, including clean MySQL migration, Django tests, deployment checks and the browser smoke test.

## Activation gates

- No VPS deployment has been attempted. Configure a private staging host, backup destination, DNS and access controls before using the production profile.
- Review publication rights for the private sourcebook content before opening the VPS publicly. The code license does not grant rights to the database content.
- Check the availability of legacy uploaded images; the repository does not contain every image named in the original database.
