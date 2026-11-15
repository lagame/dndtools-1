# Non-root deployment permissions — 2026-11-15

## Failure

Deployment run 43766289819 verified a restorable MySQL backup (58 content tables, 4,918 spells), then stopped during the migration command with a permission error reading Django settings. It did not reach the application replacement step.

The backup's `umask 077` remained active during Git checkout. Newly checked-out code had private filesystem modes, which Docker preserved when copying source into the image. The new UID 10001 could not read those files.

## Correction

- Keep backup creation private, then switch to `umask 022` before checking out public source.
- Explicitly grant read/traversal permissions to the source inside the image before switching to the unprivileged user. This remains necessary for files created by the interrupted deployment.
- Build CI from deliberately restricted source modes so the existing migration, security and browser checks cover this deployment condition.
- No changes to global VPS networking, other projects, credentials or catalog content are required.

## Local regression check

A Docker build context containing only tracked public files was created with directories set to `0700` and files to `0600`. The corrected image built successfully, and UID 10001 read all 378 source/static files. CI also builds from restricted source modes before running the full checks.
