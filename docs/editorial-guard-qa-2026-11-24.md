# Editorial guard and production correction — 24 November 2026

## Scope and observed production state

- Before editing, the working branch was `fix/admin-password-minimum` at `48bb6ca`; the only untracked path was `.vscode/`, which was preserved. Production was checked independently at `2758bc8e1ad5d57df5db54b7aeb53141cc06a01a`, with a clean tree and running app, MySQL, import worker, forum and tunnel proxy. This code change is not deployed.
- Commit `48bb6ca` introduced two short, fictional password literals in a boundary test. The test now constructs the values at runtime and still checks rejection below eight characters and acceptance at eight. No real credential was found in that commit's changed files; GitHub secret scanning currently has zero open and zero resolved alerts. This does not establish the status of the separate GitGuardian alert or prove the whole history contains no secrets.
- A later GitGuardian email also flagged commit `1605567`. Its relevant password values were fixtures in tests that use `force_login`, not production credentials. The owner and editor fixtures now generate their passwords at test runtime, without changing the authorization assertions. A fresh local build and all 110 Django tests passed. The historical commits remain in Git, and the GitGuardian portal incident status has not been verified; the email alone does not show whether the incidents were dismissed.
- The deployed password minimum is eight characters. No password was changed and no password policy was modified in this patch.

## Production data correction

- Before correcting Stamina, a private MySQL backup was restored into a temporary database and verified: `dndtools-mysql-2026-11-24-195725.sql.gz`, SHA-256 `7995842bcf2eb177156db711547f01db531e29ac0fae99bad378420f65690631`, 73 tables and 4,918 spells. Item 166 was then updated in one guarded transaction from magic item to armor enhancement, printed page 15, with the book's price and item statistics. Its original description was retained. The public detail and both catalog filters were checked.
- Before revoking direct import grants, a second private MySQL backup was independently restored and verified: `dndtools-mysql-2026-11-24-200037.sql.gz`, SHA-256 `f5018be1bff0d40f5de2878f3cf72bd643bf2f0f28b85c55b248cec9cc7c8100`, again 73 tables and 4,918 spells. Three non-owner `can_import` grants were set to false in one transaction. Proposal permissions were preserved. No import batch was pending.
- Final read-only production check: item 166 is `Stamina ENH`, page 15, price 500 gp; zero non-owner direct-import grants and zero pending import batches; both public hostnames returned HTTP 200. Production still runs the previous code until the new guard is deployed.

## Code and validation

- Direct import now requires the exact configured owner username and email, plus active superuser status. The invitation form and grant admin no longer offer direct-import permission; collaborators continue to submit proposals for owner approval. The persisted `can_import` field remains for compatibility and no migration is needed.
- Each JSON import record must identify its catalog `resource`. A file declaring `Feat` in the `Spell` importer stops before preview or publication with a localized explanation. Downloadable JSON and CSV examples include `resource`; CSV files without the column remain accepted for compatibility.
- The editorial header has one page heading, language links and a visible POST sign-out/switch-account action. With Cloudflare Access enabled, it redirects through its session logout URL.
- `docker compose run --rm -T app python manage.py test dnd --noinput --verbosity 1`: 105 passed after rebuilding the image. The first run against the previous image failed one owner test; a later run with `--keepdb` also exposed stale test-database site data. The fresh-image, fresh-database run passed.
- `makemigrations --check --dry-run`: no changes. `check --deploy --fail-level WARNING`: no issues. `git diff --check`: passed. Local Playwright review covered editorial dashboard, invitation, create and import at 390 and 1440 px in PT-BR and EN, plus the mobile sign-out path; pages had one main heading, visible account exit and no horizontal overflow. Production UI with this patch remains unverified until deployment.

## Remaining work

- Review the 31 candidate enhancements in the separate MIC ZIP and resolve its activation and shield restrictions before publishing; the 32nd record, Stamina, is already in production and excluded from the load. Source and per-record findings are in `mic-enhancements-audit-2026-11-24.md`.
- Run CI on the proposed code branch and, if deployment is approved, confirm the guarded backup, published SHA and live staff flows. The private Cloudflare Access sign-out flow needs a real account switch check after deployment.
- Other documented backlog: the `My D&D` personal area, outstanding image sources in `image-inventory.md`, and source/rights decisions for the cantrips in `reviewed-cantrips-35.md`.
