"""Copy the recovered catalog from a read-only SQLite snapshot into MySQL."""

import itertools
import sqlite3
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


class Command(BaseCommand):
    help = 'Preview, import, or verify the private legacy SQLite catalog.'

    def add_arguments(self, parser):
        parser.add_argument('--source', required=True, type=Path)
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument('--apply', action='store_true')
        mode.add_argument('--verify', action='store_true')

    def handle(self, *args, **options):
        source_path = options['source'].resolve()
        if not source_path.is_file():
            raise CommandError('SQLite source file does not exist.')
        if connection.vendor != 'mysql':
            raise CommandError('The destination must be MySQL.')

        source = sqlite3.connect('file:' + source_path.as_posix() + '?mode=ro', uri=True)
        try:
            if source.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise CommandError('Source SQLite integrity check failed.')
            if source.execute('PRAGMA foreign_key_check').fetchone():
                raise CommandError('Source SQLite has broken foreign keys.')
            tables = [row[0] for row in source.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'dnd_%' ORDER BY name"
            )]
            target_tables = {name for name in connection.introspection.table_names() if name.startswith('dnd_')}
            if set(tables) != target_tables:
                raise CommandError('Content table mismatch: missing=%s extra=%s' % (
                    sorted(set(tables) - target_tables), sorted(target_tables - set(tables))))

            columns = {}
            counts = {}
            with connection.cursor() as target:
                for table in tables:
                    columns[table] = [row[1] for row in source.execute(
                        'PRAGMA table_info("%s")' % table)]
                    target_columns = [col.name for col in connection.introspection.get_table_description(target, table)]
                    if set(columns[table]) != set(target_columns):
                        raise CommandError('%s column mismatch: source=%s target=%s' % (
                            table, columns[table], target_columns))
                    counts[table] = source.execute('SELECT COUNT(*) FROM "%s"' % table).fetchone()[0]

            self.stdout.write('Source: %d content tables, %d rows, %d spells.' % (
                len(tables), sum(counts.values()), counts['dnd_spell']))
            if options['verify']:
                self._verify(source, tables, columns, counts)
                return
            if not options['apply']:
                self.stdout.write('Dry run only. Pass --apply to import into an empty MySQL catalog.')
                return

            with transaction.atomic():
                with connection.cursor() as target:
                    for table in tables:
                        target.execute('SELECT COUNT(*) FROM %s' % connection.ops.quote_name(table))
                        if target.fetchone()[0]:
                            raise CommandError('Destination catalog is not empty: %s' % table)
                    for table in self._dependency_order(source, tables):
                        if not counts[table]:
                            continue
                        self_columns = [row[3] for row in source.execute(
                            'PRAGMA foreign_key_list("%s")' % table) if row[2] == table]
                        self_indexes = {col: columns[table].index(col) for col in self_columns}
                        pending = {col: [] for col in self_columns}
                        quoted_table = connection.ops.quote_name(table)
                        quoted_cols = ', '.join(connection.ops.quote_name(col) for col in columns[table])
                        sql = 'INSERT INTO %s (%s) VALUES (%s)' % (
                            quoted_table, quoted_cols, ', '.join(['%s'] * len(columns[table])))
                        reader = source.execute('SELECT %s FROM "%s" ORDER BY CAST(id AS INTEGER)' % (
                            ', '.join('"%s"' % col for col in columns[table]), table))
                        while batch := reader.fetchmany(500):
                            if self_columns:
                                for row in batch:
                                    for col, index in self_indexes.items():
                                        if row[index] is not None:
                                            pending[col].append((row[index], row[columns[table].index('id')]))
                                batch = [tuple(None if col in self_indexes else value
                                               for col, value in zip(columns[table], row)) for row in batch]
                            target.executemany(sql, batch)
                        for col, updates in pending.items():
                            if updates:
                                target.executemany('UPDATE %s SET %s = %%s WHERE id = %%s' % (
                                    quoted_table, connection.ops.quote_name(col)), updates)
                        self.stdout.write('%s: %d rows' % (table, counts[table]))
                self._verify(source, tables, columns, counts)
            self.stdout.write(self.style.SUCCESS('Catalog imported and verified.'))
        finally:
            source.close()

    @staticmethod
    def _dependency_order(source, tables):
        dependencies = {table: {
            row[2] for row in source.execute('PRAGMA foreign_key_list("%s")' % table)
            if row[2] in tables and row[2] != table
        } for table in tables}
        ordered = []
        while len(ordered) < len(tables):
            ready = sorted(table for table in tables if table not in ordered and not dependencies[table])
            if not ready:
                raise CommandError('Content tables contain a foreign key cycle.')
            ordered.extend(ready)
            for deps in dependencies.values():
                deps.difference_update(ready)
        return ordered

    def _verify(self, source, tables, columns, counts):
        with connection.cursor() as target:
            for table in tables:
                quoted = connection.ops.quote_name(table)
                col_names = ', '.join(connection.ops.quote_name(col) for col in columns[table])
                target.execute('SELECT COUNT(*) FROM %s' % quoted)
                actual = target.fetchone()[0]
                if actual != counts[table]:
                    raise CommandError('%s row count differs: %d vs %d' % (table, counts[table], actual))
                left = source.execute('SELECT %s FROM "%s" ORDER BY CAST(id AS INTEGER)' % (col_names, table))
                target.execute('SELECT %s FROM %s ORDER BY id' % (col_names, quoted))
                for index, (source_row, target_row) in enumerate(itertools.zip_longest(left, target)):
                    if source_row is None or target_row is None:
                        raise CommandError('%s row %d is missing.' % (table, index))
                    for column, old, new in zip(columns[table], source_row, target_row):
                        if self._value(old) != self._value(new):
                            raise CommandError('%s row %d column %s differs.' % (table, index, column))
        self.stdout.write(self.style.SUCCESS('Verified every row and column in %d content tables.' % len(tables)))

    @staticmethod
    def _value(value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode('utf-8')
        return str(value)
