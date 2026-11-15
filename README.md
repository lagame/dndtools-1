# D&D Tools

A community fork of the original D&D Tools catalog, modernized for Python 3.14, Django 5.2 and MySQL 8.4. The public pages keep the original catalog URLs and now use a responsive layout and first-party search. The source code is MIT licensed; rights to individual book content must be assessed separately.

**The database is not in this repository.** To request the private SQLite snapshot, [open an issue](https://github.com/lagame/dndtools-1/issues). We will arrange a private transfer. Never attach the database, a dump, or source scans to an issue or commit.

## Local setup (Windows PowerShell)

Install Git, Python 3 and Docker Desktop. From PowerShell:

```powershell
git clone https://github.com/lagame/dndtools-1.git
cd dndtools-1
py -3 scripts\setup_local.py
docker compose up -d --wait db
docker compose build app
docker compose run --rm app python manage.py migrate --noinput
```

If you have the private SQLite snapshot, import it into the empty MySQL catalog. Use the repaired workspace snapshot distributed privately, rather than the older original file:

```powershell
$privateDb = (Resolve-Path 'C:\path\to\dnd.sqlite').Path
docker compose run --rm --volume "${privateDb}:/private/dnd.sqlite:ro" app python manage.py import_legacy_sqlite --source /private/dnd.sqlite
docker compose run --rm --volume "${privateDb}:/private/dnd.sqlite:ro" app python manage.py import_legacy_sqlite --source /private/dnd.sqlite --apply
docker compose run --rm --volume "${privateDb}:/private/dnd.sqlite:ro" app python manage.py import_legacy_sqlite --source /private/dnd.sqlite --verify
```

The import reads the SQLite file without modifying it, requires an empty MySQL catalog and verifies every content field after writing. It does not import the unrelated HeroForge table. The project also starts without the private data, with an empty catalog.

```powershell
docker compose up -d app
```

Open <http://127.0.0.1:8765/>. For editorial access, create a local admin with `docker compose run --rm app python manage.py createsuperuser`. The generated `.env`, original SQLite, MySQL volume, uploads and backups stay private and out of Git.

## Configuração local em português (Windows)

Você precisa de Git, Python 3 e Docker Desktop. O MySQL roda no Docker, então não precisa instalá-lo separadamente no Windows.

```powershell
git clone https://github.com/lagame/dndtools-1.git
cd dndtools-1
py -3 scripts\setup_local.py
docker compose up -d --wait db
docker compose build app
docker compose run --rm app python manage.py migrate --noinput
```

O comando `setup_local.py` cria um `.env` privado com senhas aleatórias. Se você não tiver o banco, o site abre com o catálogo vazio. Para receber a cópia privada, [abra uma Issue neste fork](https://github.com/lagame/dndtools-1/issues); combinaremos o envio por outro canal. **Não publique o arquivo na Issue ou no GitHub.**

Depois que receber o `dnd.sqlite`:

```powershell
$privateDb = (Resolve-Path 'C:\caminho\para\dnd.sqlite').Path
docker compose run --rm --volume "${privateDb}:/private/dnd.sqlite:ro" app python manage.py import_legacy_sqlite --source /private/dnd.sqlite
docker compose run --rm --volume "${privateDb}:/private/dnd.sqlite:ro" app python manage.py import_legacy_sqlite --source /private/dnd.sqlite --apply
docker compose run --rm --volume "${privateDb}:/private/dnd.sqlite:ro" app python manage.py import_legacy_sqlite --source /private/dnd.sqlite --verify
docker compose up -d app
```

Abra <http://127.0.0.1:8765/>. A primeira importação pode levar alguns minutos. A opção sem `--apply` apenas confere; `--verify` compara o MySQL com o arquivo recebido. Se o banco já contém registros, o importador recusa uma segunda carga.

Para conferir o código após alterações:

```powershell
py -3 scripts\prepare_test_db.py
docker compose run --rm app python manage.py test dnd --keepdb --noinput
docker compose run --rm app python manage.py makemigrations --check --dry-run
```

As [sete magias 3.5 revisadas](docs/reviewed-cantrips-35.md) já estão no snapshot de trabalho. Novas inclusões exigem confirmação da edição e da fonte editorial.

## Private VPS staging and activation

The Compose stack runs MySQL internally, Django/Gunicorn as the application, and Caddy as the optional HTTPS proxy. On a Linux VPS with Docker Compose, clone the fork, run `python3 scripts/setup_local.py`, and edit the private `.env`:

- For **private staging over an SSH tunnel**, set `DND_DEBUG=0`, `DND_FORCE_HTTPS=0`, `DND_ALLOWED_HOSTS=127.0.0.1,localhost`, `DND_PUBLIC_HOST=127.0.0.1:8765` and matching HTTP CSRF origins. Start `db` and `app` without the production profile. The application port binds only to VPS loopback. Connect with `ssh -L 8765:127.0.0.1:8765 user@vps` and browse locally.
- Before **public activation**, review publication rights for the catalog, point a dedicated hostname to the VPS, open ports 80/443, set `DND_DEBUG=0`, `DND_FORCE_HTTPS=1`, `DND_ALLOWED_HOSTS` and `DND_PUBLIC_HOST` to that hostname, and `DND_CSRF_TRUSTED_ORIGINS=https://hostname`. Run the production deployment check and then `docker compose --profile production up -d --build`. Caddy obtains and renews HTTPS certificates. Public activation requires the owner's decision.

For either environment, apply migrations and import the private snapshot as shown above before starting the app. Do **not** publish the MySQL port, `.env`, SQLite file, or SQL dumps. The old third-party contact form is replaced by [project Issues](https://github.com/lagame/dndtools-1/issues).

## Backups and verification

Before each release, save a MySQL dump **outside the repository** and test its restoration into a temporary database:

```powershell
py -3 scripts\backup_mysql.py --output-dir 'C:\Backups\dndtools'
py -3 scripts\verify_mysql_backup.py 'C:\Backups\dndtools\dndtools-mysql-YYYY-MM-DD-HHMMSS.sql.gz'
```

On Linux use `python3` and a private backup directory such as `/var/backups/dndtools`. Protect backups with restricted access and copy them to encrypted off-site storage. `verify_mysql_backup.py` creates and drops only its own temporary restore database. The SQL dump is **not encrypted by the script**. Back up `.env` and uploaded media separately in a protected location. The original SQLite snapshot should remain untouched.

See [modernization status](docs/modernization-status.md) for the verified baseline and remaining activation gates.
