"""Restore catalog thumbnails from the original public media archive.

The database and downloaded images stay outside Git. Run from the repository root:
    python scripts/restore_catalog_media.py --sqlite dnd.sqlite
"""

import argparse
import hashlib
import io
import json
import re
import sqlite3
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request, urlopen

from PIL import Image


ARCHIVE = {
    'rulebook': 'https://dnd.arkalseif.info/static/media/rulebook/',
    'race': 'https://dnd.arkalseif.info/media/media/race/',
}
ALIASES = {
    'serpent-kingdoms.jpg': 'serpent_kingdoms.jpg',
    'ghostwalk3.JPG': 'ghostwalk.jpg',
}
SOURCE_OVERRIDES = {
    '9781887953733_p0_v1_s260x420.jpg':
        'https://covers.openlibrary.org/b/isbn/9781887953733-L.jpg',
    # The archived dragonmarked.jpg contains GIF data despite its .jpg name.
    'dragonmarked.jpg':
        'https://covers.openlibrary.org/b/isbn/9780786939336-L.jpg',
}
MAX_IMAGE_BYTES = 2_000_000


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.hrefs.extend(value for key, value in attrs if key == 'href')


def fetch(url):
    request = Request(url, headers={'User-Agent': 'DNDTools-media-recovery/1.0'})
    with urlopen(request, timeout=20) as response:
        data = response.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f'File exceeds {MAX_IMAGE_BYTES} bytes: {url}')
    return data


def archive_files(directory):
    parser = Links()
    parser.feed(fetch(directory).decode('utf-8', errors='replace'))
    files = {}
    for href in parser.hrefs:
        name = unquote(urlsplit(href).path.rsplit('/', 1)[-1])
        match = re.fullmatch(r'(.+\.(?:jpe?g|png|gif))_\d{10}', name, re.I)
        if match:
            files[match.group(1)] = urljoin(directory, href)
    return files


def image_info(data, name):
    with Image.open(io.BytesIO(data)) as image:
        image.verify()
    with Image.open(io.BytesIO(data)) as image:
        expected = 'PNG' if name.lower().endswith('.png') else 'JPEG'
        if image.format != expected or not all(image.size):
            raise ValueError(f'Unexpected image format or size: {name}')
        return list(image.size)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sqlite', type=Path)
    parser.add_argument('--covers-file', type=Path,
                        help='JSON map of legacy book IDs to archived cover filenames')
    parser.add_argument('--output-dir', type=Path,
                        default=Path('dndtools/static/media'))
    args = parser.parse_args()

    if not args.sqlite and not args.covers_file:
        parser.error('Pass --sqlite, --covers-file, or both.')
    references = set()
    if args.sqlite:
        db = sqlite3.connect('file:' + args.sqlite.resolve().as_posix() + '?mode=ro',
                             uri=True)
        try:
            for table in ('dnd_rulebook', 'dnd_race'):
                references.update(row[0].removeprefix('media/') for row in db.execute(
                    f"SELECT image FROM {table} WHERE image IS NOT NULL AND image != ''"))
        finally:
            db.close()
    if args.covers_file:
        covers = json.loads(args.covers_file.read_text(encoding='utf-8'))
        references.update('rulebook/' + name for name in covers.values())

    indexes = {kind: archive_files(url) for kind, url in ARCHIVE.items()}
    manifest = []
    for reference in sorted(references):
        path = PurePosixPath(reference)
        if (len(path.parts) != 2 or path.parts[0] not in ARCHIVE
                or path.name in ('.', '..')):
            raise ValueError(f'Unexpected catalog image path: {reference}')
        source_name = ALIASES.get(path.name, path.name)
        source = indexes[path.parts[0]].get(source_name)
        source = SOURCE_OVERRIDES.get(path.name, source)
        if not source:
            raise ValueError(f'No matching archived image: {reference}')
        target = args.output_dir.joinpath(*path.parts)
        if target.is_file():
            data = target.read_bytes()
            status = 'existing'
        else:
            data = fetch(source)
            status = 'restored'
        size = image_info(data, path.name)
        if status == 'restored':
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        manifest.append({'path': reference, 'source': source,
                         'sha256': hashlib.sha256(data).hexdigest(),
                         'bytes': len(data), 'size': size})
        print(f'{status}: {reference} ({size[0]}x{size[1]})')

    manifest_name = ('catalog-media-covers-manifest.json' if args.covers_file and not args.sqlite
                     else 'catalog-media-manifest.json')
    manifest_path = args.output_dir / manifest_name
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Validated {len(manifest)} images; manifest: {manifest_path}')


if __name__ == '__main__':
    main()
