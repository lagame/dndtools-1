# Cloudflare Access configuration QA — 2026-11-15

## Applied configuration

- Created the self-hosted application `DND Tools - Oghma` in the existing Cloudflare account after the owner activated Zero Trust Free.
- Added eight destinations: the current admin base path and its subpaths, plus the configured replacement base path and its subpaths, on both public hostnames. Public catalog paths are outside this application.
- Associated an Allow policy for the maintainer's exact email address. No Everyone or Bypass rule was added.
- Set the application session to one hour. Enabled the authenticator-app MFA capability and required it specifically for this application, with a one-hour verification duration. Global MFA enforcement and account-wide traffic blocking remain disabled.
- Enabled the App Launcher with a separate exact-email Allow policy so the owner can enroll the first authenticator. This enrollment portal does not waive the admin application's MFA requirement.
- Added `DJANGO_ADMIN_URL` only to the private VPS environment file after backing up that file. Its permissions are `0600`. No application restart or deployment was performed. The private path value, account identifiers and credentials are intentionally absent from this report.

## Verified

- Reopened the saved application and confirmed the destinations and the persisted authenticator-app MFA requirement.
- The owner enrolled and verified an authenticator-app MFA device, completed the protected admin sign-in, and reached the Django administration using a password entered privately.
- A read-only database check confirmed the owner's active staff/superuser account. A fresh MySQL backup was restored to a temporary database before account creation, preserving 58 content tables and 4,918 spells.
- In a fresh browser context, both public home pages returned HTTP 200 and the catalog title.
- On both hostnames, the old and replacement admin base paths and login subpaths redirected to the Cloudflare Access sign-in page. The configured identity provider is Cloudflare.
- The existing HeroForge, Bianca portfolio and Cursai home pages each returned HTTP 200 after the Access configuration.
- No database, private environment file, key, authentication code or backup was added to Git.

## Release handoff

- The owner explicitly authorized publication of the reviewed public-site changes. Additional administration workspace changes are deferred to a separate iteration.
- The replacement Django route becomes active only after the reviewed code is deployed. Its current Access protection was verified independently of deployment; verify the route again after release.
- Merge the reviewed PR and use the manual deployment workflow with its verified MySQL backup. Verify the deployed commit, both hostnames, protected administration and the existing VPS sites afterward.
- Infrastructure log/backup retention and the legal data-controller review remain operational follow-up work; this report does not certify legal compliance.
