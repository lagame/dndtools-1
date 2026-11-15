# D&D Tools

A community fork of the original D&D Tools catalog, modernized for Python 3.14, Django 5.2 and MySQL 8.4. The public pages keep the original catalog URLs and now use a responsive layout and first-party search. The source code is MIT licensed; rights to individual book content must be assessed separately.

The site is available at [dndtools.quest](https://dndtools.quest/). The redesign in this branch uses the HeroForge visual family with a self-hosted Inter font. Once released, `/privacy/` will explain the site's technical cookies, the browser preference used to dismiss the notice, and how to contact the maintainer. No optional advertising or analytics cookies are active, so the notice is informational; adding such services requires a real choice before they run.

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

A fonte Inter é servida pelo próprio projeto e sua licença OFL está em `dndtools/static/fonts/LICENSE-Inter.txt`. Após publicar esta branch, a página `/privacy/?lang=pt` informará os dados técnicos tratados, o contato do responsável e a duração do armazenamento no navegador.

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

### Publicação pelo Cloudflare Tunnel existente (`dndtools.quest`)

Se o VPS já roda `cloudflared` e Docker Compose, não é preciso instalar outro painel, alterar o Nginx dos demais sites nem ocupar as portas públicas 80/443. O proxy deste projeto escuta **somente** em `127.0.0.1:8766` e serve a aplicação, CSS e arquivos de mídia. Verifique antes de começar que a porta 8766 está livre. A rota atual do túnel em `https://127.0.0.1:443` só deve ser trocada depois da verificação local.

No terminal do VPS, para uma **instalação nova**:

```bash
git clone https://github.com/lagame/dndtools-1.git /opt/dndtools && cd /opt/dndtools && bash scripts/deploy_cloudflare_tunnel.sh
```

O script cria `.env` com senhas aleatórias, configura os dois hosts e HTTPS, sobe MySQL, aplica as migrações e inicia aplicação e proxy. Ele recusa uma instalação já existente para evitar alterações no banco sem backup. Sem o arquivo privado, o catálogo fica vazio. Para carregar o snapshot SQLite **revisado**, transfira-o por um canal privado para o VPS **antes** da instalação e passe o caminho absoluto ao script, por exemplo `bash scripts/deploy_cloudflare_tunnel.sh /root/dnd.sqlite`. Não envie o banco ao GitHub nem por Issue. Os arquivos de mídia ausentes do repositório precisam ser transferidos separadamente, se disponíveis.

Confira no VPS `curl -I -H 'Host: dndtools.quest' http://127.0.0.1:8766/` e `curl -I http://127.0.0.1:8766/static/css/modern.css` (respostas HTTP 200). Depois, no painel **Cloudflare Zero Trust → Networks → Tunnels → túnel existente → Published applications**, edite as rotas de `dndtools.quest` e `www.dndtools.quest`: em ambas, defina **Service URL** como `http://127.0.0.1:8766`. Remova as opções de origem HTTPS/SNI que foram configuradas para `https://127.0.0.1:443`, pois esta nova origem usa HTTP apenas no loopback do VPS. Não altere as rotas dos outros domínios. O HTTPS público continua na Cloudflare; o proxy local informa o esquema externo ao Django. Antes de divulgar o site com o catálogo privado, revise os direitos de publicação desse conteúdo.

Para testar a ligação **GitHub Actions → VPS** sem publicar nada, há o workflow manual **Check VPS connection**. Ele requer os segredos do próprio fork `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY` (chave de deploy dedicada), `VPS_KNOWN_HOSTS` (chave pública do host previamente conferida) e, opcionalmente, `VPS_PORT` (padrão 22). A chave pública da chave de deploy precisa estar autorizada para esse usuário no VPS. Em **Actions → Check VPS connection → Run workflow**, uma execução bem-sucedida confirma SSH, Docker, espaço e estado das portas 8765/8766. Esse workflow não altera o VPS e não usa o banco. Os segredos do HeroForge pertencem ao outro repositório e não são compartilhados automaticamente com este fork.

Para **atualizações depois da instalação inicial**, execute manualmente **Actions → Deploy D&D Tools to VPS → Run workflow** na branch `master`. O workflow exige os mesmos segredos, recusa alterações locais no checkout do VPS e só aceita o commit atual da branch. Antes de atualizar, cria um dump MySQL em `/var/backups/dndtools` e testa sua restauração em um banco temporário. Depois atualiza apenas `/opt/dndtools`, aplica migrações e verifica a página inicial e o CSS pela porta local `8766`. Não altera as rotas do Cloudflare nem os outros projetos do VPS. Se uma migração ou a verificação final falhar, investigue antes de repetir; o backup verificado permanece disponível para recuperação manual.

## Backups and verification

Before each release, save a MySQL dump **outside the repository** and test its restoration into a temporary database:

```powershell
py -3 scripts\backup_mysql.py --output-dir 'C:\Backups\dndtools'
py -3 scripts\verify_mysql_backup.py 'C:\Backups\dndtools\dndtools-mysql-YYYY-MM-DD-HHMMSS.sql.gz'
```

On Linux use `python3` and a private backup directory such as `/var/backups/dndtools`. Protect backups with restricted access and copy them to encrypted off-site storage. `verify_mysql_backup.py` creates and drops only its own temporary restore database. The SQL dump is **not encrypted by the script**. Back up `.env` and uploaded media separately in a protected location. The original SQLite snapshot should remain untouched.

See [modernization status](docs/modernization-status.md) for the verified baseline and remaining activation gates.

The [navigation and filter map](docs/navigation-and-filters.md) lists the old menu entries and their current destinations. The [image inventory](docs/image-inventory.md) and [CSV](docs/image-inventory.csv) identify catalog images still missing from the private media volume. The [2026-11-15 QA report](docs/modernization-qa-2026-11-15.md) records the latest local checks and remaining limits.

The [identity and privacy QA report](docs/identity-privacy-qa-2026-11-15.md) records the visual checks, browser storage behavior and legal details still to confirm before publishing that branch.
