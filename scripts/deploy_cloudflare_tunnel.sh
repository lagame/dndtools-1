#!/usr/bin/env bash
# First deployment on a VPS that already runs cloudflared and Docker Compose.
set -euo pipefail

cd "$(dirname "$0")/.."

if (( $# > 1 )); then
    echo "Usage: bash scripts/deploy_cloudflare_tunnel.sh [private-sqlite-path]" >&2
    exit 2
fi

command -v python3 >/dev/null || { echo 'Python 3 is required.' >&2; exit 1; }
command -v docker >/dev/null || { echo 'Docker Compose is required.' >&2; exit 1; }
command -v curl >/dev/null || { echo 'curl is required.' >&2; exit 1; }
docker compose version >/dev/null

compose=(docker compose -f compose.yaml -f compose.tunnel.yaml)
if [[ -f .env ]] || [[ -n "$("${compose[@]}" ps -q db 2>/dev/null)" ]]; then
    echo 'Existing D&D Tools installation detected. This script only provisions a new installation; preserve and back up the existing database before updating it.' >&2
    exit 1
fi

sqlite_path=''
if (( $# == 1 )); then
    [[ -f "$1" ]] || { echo 'Private SQLite file not found.' >&2; exit 1; }
    sqlite_path="$(realpath "$1")"
fi

python3 scripts/setup_local.py
python3 - <<'PY'
from pathlib import Path

env = Path('.env')
values = {
    'DND_DEBUG': '0',
    'DND_FORCE_HTTPS': '1',
    'DND_ALLOWED_HOSTS': 'dndtools.quest,www.dndtools.quest',
    'DND_CSRF_TRUSTED_ORIGINS': 'https://dndtools.quest,https://www.dndtools.quest',
    'DND_PUBLIC_HOST': 'dndtools.quest',
}
lines = env.read_text(encoding='utf-8').splitlines()
present = set()
for index, line in enumerate(lines):
    key = line.partition('=')[0]
    if key in values:
        lines[index] = key + '=' + values[key]
        present.add(key)
lines.extend(key + '=' + value for key, value in values.items() if key not in present)
env.write_text('\n'.join(lines) + '\n', encoding='utf-8')
env.chmod(0o600)
PY

"${compose[@]}" config --quiet
"${compose[@]}" up -d --wait db
"${compose[@]}" build app
"${compose[@]}" run --rm app python manage.py migrate --noinput

if [[ -n "$sqlite_path" ]]; then
    mount="${sqlite_path}:/private/dnd.sqlite:ro"
    "${compose[@]}" run --rm --volume "$mount" app python manage.py import_legacy_sqlite --source /private/dnd.sqlite
    "${compose[@]}" run --rm --volume "$mount" app python manage.py import_legacy_sqlite --source /private/dnd.sqlite --apply
    "${compose[@]}" run --rm --volume "$mount" app python manage.py import_legacy_sqlite --source /private/dnd.sqlite --verify
fi

"${compose[@]}" up -d --wait app tunnel_proxy
curl --retry 15 --retry-delay 2 --retry-connrefused --fail --silent --show-error --output /dev/null --header 'Host: dndtools.quest' http://127.0.0.1:8766/
curl --retry 15 --retry-delay 2 --retry-connrefused --fail --silent --show-error --output /dev/null http://127.0.0.1:8766/static/css/modern.css
echo 'Local origin ready on http://127.0.0.1:8766. Update both Cloudflare Tunnel routes to this URL after checking the site.'
