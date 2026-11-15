"""Restore a dump to a temporary MySQL database, then remove that database."""

import argparse
import gzip
import re
import secrets
import subprocess
from pathlib import Path


MYSQL = ['docker', 'compose', 'exec', '-T', 'db', 'sh', '-c',
         'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot']


def run_sql(sql):
    subprocess.run(MYSQL, input=sql, text=True, check=True,
                   stdout=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    archive = args.archive.resolve()
    if not archive.is_file():
        parser.error('Archive does not exist.')
    temporary = 'dndtools_restore_' + secrets.token_hex(6)
    created = False
    try:
        run_sql(f'CREATE DATABASE `{temporary}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs;')
        created = True
        command = ['docker', 'compose', 'exec', '-T', 'db', 'sh', '-c',
                   f'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot {temporary}']
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        with gzip.open(archive, 'rb') as source:
            for block in iter(lambda: source.read(1024 * 1024), b''):
                process.stdin.write(block)
        process.stdin.close()
        error = process.stderr.read().decode(errors='replace')
        if process.wait() != 0:
            raise RuntimeError('Restore failed: ' + error[-500:])
        query = (
            'SELECT COUNT(*) FROM information_schema.tables '
            f'WHERE table_schema = "{temporary}" AND table_name LIKE "dnd\\_%"; '
            f'SELECT COUNT(*) FROM `{temporary}`.`dnd_spell`;'
        )
        result = subprocess.run(
            ['docker', 'compose', 'exec', '-T', 'db', 'sh', '-c',
             'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot --batch --skip-column-names'],
            input=query, text=True, capture_output=True, check=True,
        )
        numbers = [int(value) for value in re.findall(r'^\d+$', result.stdout, re.MULTILINE)]
        if len(numbers) != 2 or numbers[0] < 58 or numbers[1] < 1:
            raise RuntimeError('Restored catalog is incomplete: %s' % numbers)
        print('Restore verified:', numbers[0], 'content tables;', numbers[1], 'spells.')
    finally:
        if created:
            run_sql(f'DROP DATABASE `{temporary}`;')


if __name__ == '__main__':
    main()
