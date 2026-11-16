#!/usr/bin/env bash
# Update only this project's VPS stack after verifying a restorable MySQL dump.
set -euo pipefail

target_sha="$1"
[[ "$target_sha" =~ ^[0-9a-f]{40}$ ]]
cd /opt/dndtools
test -f .env
grep -Eq '^DJANGO_ADMIN_URL=[a-zA-Z0-9_-]{16,64}$' .env || { echo 'Set a private DJANGO_ADMIN_URL in .env and protect its path with Cloudflare Access before updating.' >&2; exit 1; }
grep -Eq '^DND_ACCESS_TEAM_DOMAIN=https://[a-z0-9-]+\.cloudflareaccess\.com$' .env || { echo 'Set DND_ACCESS_TEAM_DOMAIN in the private .env before updating.' >&2; exit 1; }
grep -Eq '^DND_ACCESS_AUD=[^[:space:]]+$' .env || { echo 'Set DND_ACCESS_AUD in the private .env before updating.' >&2; exit 1; }
grep -Eq '^DND_EDITORIAL_NOTIFY_EMAIL=[^[:space:]]+@[^[:space:]]+$' .env || { echo 'Set editorial notification email in the private .env before updating.' >&2; exit 1; }
grep -Eq '^DND_EMAIL_HOST=[^[:space:]]+$' .env || { echo 'Set the SMTP host in the private .env before updating.' >&2; exit 1; }
grep -Eq '^DND_EMAIL_FROM=[^[:space:]]+@[^[:space:]]+$' .env || { echo 'Set the SMTP sender in the private .env before updating.' >&2; exit 1; }
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
compose=(docker compose -f compose.yaml -f compose.tunnel.yaml)
"${compose[@]}" config --quiet
"${compose[@]}" build app
"${compose[@]}" run --rm app python manage.py migrate --noinput
"${compose[@]}" up -d --wait app tunnel_proxy
curl --retry 15 --retry-delay 2 --retry-connrefused --fail --silent --show-error --output /dev/null --header 'Host: dndtools.quest' http://127.0.0.1:8766/
curl --retry 15 --retry-delay 2 --retry-connrefused --fail --silent --show-error --output /dev/null http://127.0.0.1:8766/static/css/modern.css
test "$(git rev-parse HEAD)" = "$target_sha"
printf 'Deployed %s; verified MySQL backup: %s\n' "$target_sha" "$backup_file"
