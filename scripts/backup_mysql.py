"""Create a consistent private MySQL dump outside the repository."""

import argparse
import gzip
import hashlib
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    output_dir = args.output_dir.resolve()
    repository = Path(__file__).resolve().parents[1]
    if output_dir == repository or repository in output_dir.parents:
        parser.error('Backups must be stored outside the repository.')
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%Y-%m-%d-%H%M%S')
    output = output_dir / ('dndtools-mysql-' + timestamp + '.sql.gz')
    partial = output.with_suffix(output.suffix + '.partial')
    if output.exists() or partial.exists():
        parser.error('A backup with this timestamp already exists.')
    command = [
        'docker', 'compose', 'exec', '-T', 'db', 'sh', '-c',
        'MYSQL_PWD="$MYSQL_PASSWORD" exec mysqldump --single-transaction '
        '--quick --no-tablespaces --set-gtid-purged=OFF '
        '-u "$MYSQL_USER" "$MYSQL_DATABASE"',
    ]
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors)
        try:
            with partial.open('xb') as destination, gzip.GzipFile(fileobj=destination, mode='wb') as compressed:
                for block in iter(lambda: process.stdout.read(1024 * 1024), b''):
                    compressed.write(block)
            if process.wait() != 0:
                errors.seek(0)
                raise RuntimeError('mysqldump failed: ' + errors.read().decode(errors='replace')[-500:])
            with gzip.open(partial, 'rb') as source:
                header = source.read(128)
                if b'MySQL dump' not in header:
                    raise RuntimeError('Dump header is missing.')
                for _ in iter(lambda: source.read(1024 * 1024), b''):
                    pass
            partial.rename(output)
        except Exception:
            process.kill()
            process.wait()
            partial.unlink(missing_ok=True)
            raise
    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    print('Backup:', output)
    print('Bytes:', output.stat().st_size)
    print('SHA-256:', checksum)


if __name__ == '__main__':
    main()
