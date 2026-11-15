# Cloudflare Access configuration QA — 2026-11-15

## Applied configuration

- Created the self-hosted application `DND Tools - Oghma` in the existing Cloudflare account after the owner activated Zero Trust Free.
- Added eight destinations: the current admin base path and its subpaths, plus the configured replacement base path and its subpaths, on both public hostnames. Public catalog paths are outside this application.
- Associated an Allow policy for the maintainer's exact email address. No Everyone or Bypass rule was added.
- Set the application session to one hour. Enabled the authenticator-app MFA capability and required it specifically for this application, with a one-hour verification duration. Global MFA enforcement and account-wide traffic blocking remain disabled.
- Added `DJANGO_ADMIN_URL` only to the private VPS environment file after backing up that file. Its permissions are `0600`. No application restart or deployment was performed. The private path value, account identifiers and credentials are intentionally absent from this report.

## Verified

- Reopened the saved application and confirmed the destinations and the persisted authenticator-app MFA requirement.
- In a fresh browser context, both public home pages returned HTTP 200 and the catalog title.
- On both hostnames, the old and replacement admin base paths and login subpaths redirected to the Cloudflare Access sign-in page. The configured identity provider is Cloudflare.
- The existing HeroForge, Bianca portfolio and Cursai home pages each returned HTTP 200 after the Access configuration.
- No database, private environment file, key, authentication code or backup was added to Git.

## Still required before release

- The owner must complete the Cloudflare identity login and authenticator enrollment/verification. Authorized access has not yet been verified end to end.
- The replacement Django route becomes active only after the reviewed code is deployed. Its current Access protection was verified independently of deployment.
- Complete the remaining privacy/publication review, merge the draft PR when approved, and use the manual deployment workflow with its verified MySQL backup.
