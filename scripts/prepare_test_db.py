"""Grant the app user access to a separate MySQL database for Django tests."""

import re
import subprocess
from pathlib import Path


def main():
    values = {}
    for line in Path('.env').read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip()
    database = values['DND_DB_NAME']
    user = values['DND_DB_USER']
    if not all(re.fullmatch(r'[A-Za-z0-9_]+', value) for value in (database, user)):
        raise SystemExit('Database and user names must contain only letters, numbers or underscores.')
    test_database = 'test_' + database
    sql = (
        f'CREATE DATABASE IF NOT EXISTS `{test_database}` CHARACTER SET utf8mb4 '
        'COLLATE utf8mb4_0900_as_cs;\n'
        f"GRANT ALL PRIVILEGES ON `{test_database}`.* TO '{user}'@'%';\n"
    )
    subprocess.run(
        ['docker', 'compose', 'exec', '-T', 'db', 'sh', '-c',
         'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot'],
        input=sql, text=True, check=True,
    )
    print('Test database is ready:', test_database)


if __name__ == '__main__':
    main()
