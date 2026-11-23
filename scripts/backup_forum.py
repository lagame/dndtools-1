"""Back up the private phpBB database and uploaded content before a release."""
import argparse
import os
from pathlib import Path
import shutil
import sqlite3
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-dir', type=Path, default=Path('/var/lib/dndtools/forum'))
    parser.add_argument('--output-dir', type=Path, default=Path('/var/backups/dndtools'))
    args = parser.parse_args()

    source = args.source_dir / 'forum.sqlite'
    if not source.is_file():
        parser.error('Forum database is missing.')
    destination = args.output_dir / ('forum-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    destination.mkdir(mode=0o700, parents=True)
    with sqlite3.connect(f'file:{source}?mode=ro', uri=True) as original:
        with sqlite3.connect(destination / 'forum.sqlite') as backup:
            original.backup(backup)
            if backup.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('Forum backup failed integrity check.')
            if backup.execute("SELECT count(*) FROM phpbb_users WHERE username_clean = 'ronassic'").fetchone()[0] != 1:
                raise RuntimeError('Forum backup is missing Ronassic.')
    os.chmod(destination / 'forum.sqlite', 0o600)
    for name in ('files', 'store', 'avatars'):
        folder = args.source_dir / name
        if folder.is_dir():
            shutil.copytree(folder, destination / name)
    print(f'Forum backup verified: {destination}')


if __name__ == '__main__':
    main()
