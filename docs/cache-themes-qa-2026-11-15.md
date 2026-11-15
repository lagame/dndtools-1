# Cache and themes QA — 2026-11-15

## What changed

- Modern CSS and JavaScript URLs now include a short content digest. A changed file gets a new URL, while the unchanged file keeps its cached URL.
- Public HTML responses use `Cache-Control: no-cache, max-age=0, must-revalidate` unless a view already sets a stricter policy. Catalog pages are not cached by the application.
- The header offers Standard (HeroForge purple), Modern (project blue and gold) and Simple (white, black and blue). The selection stays in browser `localStorage` under `dnd_theme_v2` until changed or cleared. Existing `dnd_theme_v1` preferences are migrated to the corresponding appearance. No theme cookie is sent to the server.
- A small Oghma scroll links to Django admin and stays visible while scrolling. It moves above the privacy notice when the notice is open; authentication remains enforced by Django.
- Simple avoids downloading the Standard identity stylesheet, Inter font, favicon and available catalog cover/portrait images on subsequent page loads. Image placeholders explain their absence; the other themes still load images, and no-JavaScript browsers retain image fallbacks.
- The privacy page describes the new local preference in both languages.

## Evidence

- Before these changes, the public HTML returned `CF-Cache-Status: DYNAMIC`; the public CSS returned `HIT` with `Cache-Control: max-age=14400` and a nonzero `Age`.
- On the current Cloudflare configuration, a new CSS query string returned `MISS`, its second request returned `HIT`, and a different query string returned `MISS`. This confirms that query strings are included in the current cache key.
- The local HTML returned a revalidation header and versioned CSS/JS URLs. Django tests verified that changing an asset's bytes changes its URL.
- 17 Django tests, the production Django check and the migration drift check passed. Browser smoke passed at 360, 390, 768 and 1440 px, including theme changes, migration of old preferences, persistence across navigation, fixed admin shortcut with and without the privacy notice, and responsive layout. Screenshots were saved outside Git under the local temporary directory and visually reviewed.
- In fresh Chromium contexts on the local home page, Simple used 9 requests before this change, including the unused identity stylesheet. It now uses 8 requests, without the identity stylesheet, image or font request. Standard used 10 requests including its identity stylesheet and Inter font. This is a request count, not a measured production load-time improvement. A browser test confirms that Simple does not request a catalog image until switching to a visual mode that displays it.

## Release notes

- This work remains on `design/heroforge-family`; the production site has not received these changes.
- Do not add a Cloudflare rule that caches HTML or ignores query strings without revisiting this policy. Media uploads do not receive content digests and should use new filenames when replaced.
- The legal controller identity and Cloudflare account-specific log retention still need confirmation before the privacy review is complete.
