#!/usr/bin/env bash
# Update only this project's VPS stack after verifying a restorable MySQL dump.
set -euo pipefail

target_sha="$1"
[[ "$target_sha" =~ ^[0-9a-f]{40}$ ]]
cd /opt/dndtools
test -f .env
test -f /etc/dndtools/forum/config.php || { echo 'Private phpBB config is missing.' >&2; exit 1; }
test -f /var/lib/dndtools/forum/forum.sqlite || { echo 'Private phpBB database is missing.' >&2; exit 1; }
grep -Fxq 'DND_PUBLIC_HOST=dndtools.quest' .env || { echo 'Set DND_PUBLIC_HOST=dndtools.quest in the private .env before updating.' >&2; exit 1; }
grep -Eq '^DJANGO_ADMIN_URL=[a-zA-Z0-9_-]{16,64}$' .env || { echo 'Set a private DJANGO_ADMIN_URL in .env and protect its path with Cloudflare Access before updating.' >&2; exit 1; }
grep -Eq '^DND_ACCESS_TEAM_DOMAIN=https://[a-z0-9-]+\.cloudflareaccess\.com$' .env || { echo 'Set DND_ACCESS_TEAM_DOMAIN in the private .env before updating.' >&2; exit 1; }
grep -Eq '^DND_ACCESS_AUD=[^[:space:]]+$' .env || { echo 'Set DND_ACCESS_AUD in the private .env before updating.' >&2; exit 1; }
grep -Eq '^DND_EDITORIAL_NOTIFY_EMAIL=[^[:space:]]+@[^[:space:]]+$' .env || { echo 'Set editorial notification email in the private .env before updating.' >&2; exit 1; }
grep -Eq '^DND_EMAIL_HOST=[^[:space:]]+$' .env || { echo 'Set the SMTP host in the private .env before updating.' >&2; exit 1; }
grep -Eq '^DND_EMAIL_FROM=[^[:space:]]+@[^[:space:]]+$' .env || { echo 'Set the SMTP sender in the private .env before updating.' >&2; exit 1; }
if grep -Eq '^DND_EMAIL_HOST=smtp\.gmail\.com$' .env; then
  grep -Eq '^DND_EMAIL_USER=[^[:space:]]+@[^[:space:]]+$' .env || { echo 'Set the Gmail SMTP user in the private .env before updating.' >&2; exit 1; }
  grep -Eq '^DND_EMAIL_PASSWORD=[^[:space:]]+$' .env || { echo 'Set the Gmail app password in the private .env before updating.' >&2; exit 1; }
fi
test -z "$(git status --porcelain)" || { echo 'Working tree has local changes.' >&2; exit 1; }
git fetch --no-tags origin master
test "$(git rev-parse origin/master)" = "$target_sha" || { echo 'Selected SHA is not the current fork master.' >&2; exit 1; }
previous_sha="$(git rev-parse HEAD)"
git merge-base --is-ancestor "$previous_sha" "$target_sha" || { echo 'Deployment must move forward from the installed SHA.' >&2; exit 1; }

install -d -m 700 /var/backups/dndtools
umask 077
backup_file="$(python3 scripts/backup_mysql.py --output-dir /var/backups/dndtools | awk '/^Backup: / { print substr($0, 9) }')"
test -f "$backup_file"
python3 scripts/verify_mysql_backup.py "$backup_file"

# Backups stay private; checked-out public source must be readable by the app user.
umask 022
git switch --detach --quiet "$target_sha"
python3 scripts/backup_forum.py
compose=(docker compose -f compose.yaml -f compose.tunnel.yaml -f compose.forum.prod.yaml)
"${compose[@]}" config --quiet
"${compose[@]}" build app forum
"${compose[@]}" run --rm -T app python - \
  --covers-file /app/dndtools/dnd/legacy_rulebook_covers.json \
  --output-dir /var/www/media < scripts/restore_catalog_media.py
"${compose[@]}" run --rm app python manage.py migrate --noinput
"${compose[@]}" run --rm app python manage.py curate_rulebooks --apply
"${compose[@]}" up -d --wait app forum tunnel_proxy
"${compose[@]}" exec -T -u www-data forum php /usr/local/bin/dndtools-install-language.php
# Compose does not recreate a service when only a bind-mounted Caddyfile changes.
"${compose[@]}" up -d --no-deps --force-recreate --wait tunnel_proxy
curl --retry 15 --retry-delay 2 --retry-all-errors --fail --silent --show-error --output /dev/null --header 'Host: dndtools.quest' http://127.0.0.1:8766/
curl --retry 15 --retry-delay 2 --retry-all-errors --fail --silent --show-error --output /dev/null http://127.0.0.1:8766/static/css/modern.css
curl --retry 15 --retry-delay 2 --retry-all-errors --fail --silent --show-error --output /dev/null --header 'Host: dndtools.quest' http://127.0.0.1:8766/forum/
curl --retry 15 --retry-delay 2 --retry-all-errors --fail --silent --show-error --header 'Host: dndtools.quest' http://127.0.0.1:8766/forum/ | python3 -c 'import sys; assert "<html dir=\"ltr\" lang=\"pt-br\">" in sys.stdin.read(), "Forum language is not Brazilian Portuguese"'
test "$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' --header 'Host: dndtools.quest' http://127.0.0.1:8766/forum/adm/index.php)" = 404
test "$(curl --silent --show-error --output /dev/null --write-out '%{redirect_url}' --header 'Host: www.dndtools.quest' http://127.0.0.1:8766/spells/)" = 'https://dndtools.quest/spells/'
curl --fail --silent --show-error --header 'Host: dndtools.quest' http://127.0.0.1:8766/sitemap.xml |
  python3 -c 'import sys, xml.etree.ElementTree as ET; root=ET.parse(sys.stdin).getroot(); urls=[el.text for el in root.iter() if el.tag.endswith("}loc")]; assert urls and all(url.startswith("https://dndtools.quest/") for url in urls), "Sitemap contains a foreign or insecure URL"'
test "$(git rev-parse HEAD)" = "$target_sha"
printf 'Deployed %s; verified MySQL backup: %s\n' "$target_sha" "$backup_file"
