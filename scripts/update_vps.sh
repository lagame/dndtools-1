#!/usr/bin/env bash
# Update only this project's VPS stack after verifying a restorable MySQL dump.
set -euo pipefail

target_sha="$1"
[[ "$target_sha" =~ ^[0-9a-f]{40}$ ]]
cd /opt/dndtools
test -f .env
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
