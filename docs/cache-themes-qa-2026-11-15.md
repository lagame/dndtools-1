# Cache and themes QA — 2026-11-15

## What changed

- Modern CSS and JavaScript URLs now include a short content digest. A changed file gets a new URL, while the unchanged file keeps its cached URL.
- Public HTML responses use `Cache-Control: no-cache, max-age=0, must-revalidate` unless a view already sets a stricter policy. Catalog pages are not cached by the application.
- The header offers Modern (HeroForge purple), Simple (white, black and blue) and Classic (original blue and gold). The selection stays in browser `localStorage` under `dnd_theme_v1` until changed or cleared. No theme cookie is sent to the server.
- The privacy page describes the new local preference in both languages.

## Evidence

- Before these changes, the public HTML returned `CF-Cache-Status: DYNAMIC`; the public CSS returned `HIT` with `Cache-Control: max-age=14400` and a nonzero `Age`.
- On the current Cloudflare configuration, a new CSS query string returned `MISS`, its second request returned `HIT`, and a different query string returned `MISS`. This confirms that query strings are included in the current cache key.
- The local HTML returned a revalidation header and versioned CSS/JS URLs. Django tests verified that changing an asset's bytes changes its URL.
- 17 Django tests, the production Django check and the migration drift check passed. Browser smoke passed at 360, 390, 768 and 1440 px, including theme changes, persistence across navigation and responsive layout. Screenshots were saved outside Git under the local temporary directory and visually reviewed.

## Release notes

- This work remains on `design/heroforge-family`; the production site has not received these changes.
- Do not add a Cloudflare rule that caches HTML or ignores query strings without revisiting this policy. Media uploads do not receive content digests and should use new filenames when replaced.
- The legal controller identity and Cloudflare account-specific log retention still need confirmation before the privacy review is complete.
