# Security hardening QA — 2026-11-15

## Scope

- The fixed Oghma shortcut now has the neutral accessible name `Oghma`. Its destination remains visible in public HTML, so the new route is not a secret.
- `DJANGO_ADMIN_URL` supplies a single Django admin path segment. Only local debug mode falls back to `/admin/`. Production refuses to start without a 16–64 character value. The admin cache policy follows that route.
- Axes keeps the five-attempt, 15-minute username lockout and adds a separate IP lockout when `CF-Connecting-IP` arrives through loopback or the Docker DNS address of this project's `tunnel_proxy`. Missing, malformed or untrusted headers leave username-only protection in place. The proxy address is refreshed every 30 seconds. Successful-login access logging remains disabled.
- All 27 catalog templates that rendered legacy `|safe` HTML now use one `nh3` sanitizer at the rendering boundary. The importer copies the private SQLite data into MySQL unchanged, including cached HTML. This covers existing rows without altering catalog data. The local catalog audit counted 10,833 cached HTML fragments. Tables, paragraphs, headings, links, the `caps`/errata classes, and selected formatting properties are preserved; scripts, event handlers and unsafe URL schemes are removed. All 1,946 observed cached links were relative.
- `django-csp` adds a `Content-Security-Policy-Report-Only` header. There is no report collector or enforcement yet. Legacy inline handlers and Django admin resources need inspection before enforcement.
- The application runs as UID/GID 10001 with all capabilities dropped and `no-new-privileges`. A one-shot root helper adjusts ownership only for this project's named static and media volumes before the app starts. It does not access the MySQL volume or other projects.
- The privacy page now discloses that validated IPs can be stored with failed admin login attempts.

## Validation

- Docker image build succeeded with `nh3` and `django-csp`.
- 24 Django tests passed, including the trusted-peer and IP lockout paths, custom route cache/CSP behavior, and an XSS regression using a previously imported HTML field.
- Production `check --deploy --fail-level WARNING` passed with an explicit test admin route. With `DND_DEBUG=0` and an empty `DJANGO_ADMIN_URL`, startup failed as intended.
- With a test custom route, its login returned HTTP 200 and `Cache-Control: no-store`; `/admin/login/` returned HTTP 404.
- `makemigrations --check --dry-run` found no model changes.
- The local app responded with HTTP 200 for home and spells; its process ran as UID 10001 and could write to the static and media volumes.
- Browser smoke passed at 360, 390, 768 and 1440 px on the local app.

## Release gate

Do not deploy this branch until Cloudflare Access protects the configured custom path and its subpaths on both public hostnames. The old `/admin` rules do not move with Django's route. Verify blocked unauthenticated access and authorized access from a private browser session. The project cannot assert the Cloudflare account configuration from code. Do not publish the private `.env` or database. Production has not been deployed from this branch.

## References

- [Cloudflare Access application paths](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/app-paths/)
- [Cloudflare `CF-Connecting-IP`](https://developers.cloudflare.com/fundamentals/reference/http-headers/)
- [nh3 sanitizer options](https://nh3.readthedocs.io/en/stable/)
- [django-csp report-only configuration](https://django-csp.readthedocs.io/en/latest/configuration.html)
