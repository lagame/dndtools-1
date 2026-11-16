# Catalog media restoration — 2026-11-16

The private SQLite snapshot references 68 rulebook covers and 13 race illustrations. All 81 files were absent from both the local and production media volumes. The [previous inventory](image-inventory.md) records the missing paths before this restoration.

The 13 race images and 66 rulebook covers came from the original site's [race](https://dnd.arkalseif.info/media/media/race/) and [rulebook](https://dnd.arkalseif.info/static/media/rulebook/) media archives. Two archived filenames needed mapping to their existing database paths: `serpent_kingdoms.jpg` to `serpent-kingdoms.jpg` and `ghostwalk.jpg` to `ghostwalk3.JPG`. The archived `dragonmarked.jpg` contains GIF data under a JPEG filename; a genuine JPEG cover for ISBN 9780786939336 was obtained from [Open Library](https://covers.openlibrary.org/b/isbn/9780786939336-L.jpg). The `Feats` cover (ISBN 9781887953733) also came from [Open Library](https://covers.openlibrary.org/b/isbn/9781887953733-L.jpg).

Run `py -3 scripts/restore_catalog_media.py --sqlite dnd.sqlite` to reproduce the download locally with the private database. The script validates each image with Pillow and writes a SHA-256 manifest inside the ignored media directory. The images and database are excluded from Git; deploy the two media directories separately to the application's `media_data` volume. Check the actual container mount name before writing: the active Compose volume on this deployment is `dndtools_media_data`.

Before the production copy, a root-only backup of the active media volume was created and checked. The transferred archive and all 81 extracted files were verified with SHA-256. Public checks returned HTTP 200 and matching bytes for all 81 `/media/` URLs and all 81 legacy `/static/media/` URLs. The Serpent Kingdoms legacy URL also returned HTTP 200 on `www` and locally; its page renders the cover. The image inventory audit reported zero missing references after local restoration. Books and races without an image field remain intentionally without a cover or illustration.

The image sources are third-party artwork. Keep the binaries outside the public repository and review publication rights separately.

## Remaining rulebook covers

Six additional covers were matched by title and edition, downloaded, checked as real JPEG/PNG files and visually inspected. The private media restoration script records their source URLs and SHA-256 hashes in its local manifest:

| Book | Source |
| --- | --- |
| Enemies and Allies | [Open Library, ISBN 0786918527](https://openlibrary.org/isbn/0786918527) |
| Player's Handbook 3.0 | [Open Library, ISBN 0786915501](https://openlibrary.org/isbn/0786915501) |
| Dragon Magazine #326 | [Original Magazines, issue 326](https://www.originalmagazines.com/products/dragon-magazine-december-2004-326-the-wandering-monsters-vg); image from WonderClub |
| Dragon Magazine #324 | [Dragon's Trove, issue 324](https://www.dragonstrove.com/products/dragon-magazine-324) |
| Salt and Sea Dogs: The Pirates of Tellene | [Open Library, ISBN 1889182907](https://openlibrary.org/isbn/1889182907) |
| Towers of High Sorcery | [Dragonlance Nexus](https://dragonlancenexus.com/products/towers-of-high-sorcery/) and [Open Library, ISBN 1931567174](https://openlibrary.org/isbn/1931567174) |

The seventh record, `Web`, is an online source rather than a printed book. Its cards and detail page intentionally omit a cover and its placeholder.
