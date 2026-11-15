# Production release QA — 2026-11-15

## Published version

- PRs #1 and #2 were merged into the fork's `master` branch.
- GitHub Actions deployment [43766962194](https://github.com/lagame/dndtools-1/actions/runs/43766962194) succeeded for commit `8a09e3c5b4a4f5bf9e4567282acc9f00985171d2`. A read-only SSH check confirmed the installed commit and clean production checkout.
- The deployment created a private MySQL backup and restored it to a disposable database before updating: 58 content tables and 4,918 spells verified.
- The initial deployment stopped before application replacement because private checkout permissions prevented the non-root user from reading source. PR #2 corrected that issue and added restricted-source CI coverage; see [permission regression QA](deploy-permissions-qa-2026-11-15.md).

## Verification

- Both public hostnames returned HTTP 200 with the D&D Tools catalog. HTML requested revalidation, and the CSP Report-Only header was present.
- Standard, Modern and Simple switched successfully at 360, 390, 768 and 1440 px without page overflow. The selected Simple theme survived a reload. Desktop home and mobile/desktop catalog screenshots were stored privately outside Git.
- The public Absorbing Shield detail displayed relation/prerequisite names without generic `Model object (ID)` labels. Read-only production rendering also verified the class-variant and monster administration lists.
- Fresh unauthenticated browser checks required Cloudflare Access for the old and replacement admin base/login paths on both hostnames. Direct origin checks verified the replacement login, `no-store` responses and HTTP 404 for the obsolete Django route.
- MySQL retained 4,918 spells and the owner's active administrator account. The application ran as UID 10001 and could write its static/media volumes. Production environment permissions remained `0600`.
- HeroForge, the Bianca portfolio and Cursai each returned HTTP 200 after deployment. All five unrelated Docker container identities matched the pre-deploy snapshot; Nginx configuration validation passed.
- Both pre-merge CI checks passed, including 26 Django tests, migration drift, deployment checks and browser smoke. A separate restrictive-context Docker test verified that UID 10001 could read all 378 source/static files.
- The subsequent admin workspace release PR #3 passed both CI runs and deployed as `192d824df34994dc4100d54353b147d9bb62f1e8`. Its verified MySQL backup restore preserved 58 catalog tables and 4,918 spells.
- The admin workspace stylesheet, dashboard and direct catalog links are live. The new admin login route returns HTTP 200 with `no-store` at the origin, while the old `/admin/login/` path returns 404. Cloudflare Access redirects remain active on both hosts.
- The Menu label computes to 13.12 px, matching Theme, in all three public themes. Both public hosts and the five unrelated Docker containers passed their post-release checks.

## Scope and follow-up

- No database, environment file, password, private key, authentication code or backup is included in Git.
- New administration workspace styling remains preserved locally for a separate iteration. This release includes the narrowly scoped correction of catalog labels.
- Infrastructure log/backup retention and legal data-controller details still need operational review. This technical release does not certify legal compliance.
