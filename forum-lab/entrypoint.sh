#!/bin/sh
set -eu

if [ "${DND_FORUM_PRODUCTION:-0}" != 1 ]; then
    mkdir -p /var/lib/phpbb/store
    cp -an /var/www/html/store/. /var/lib/phpbb/store/
    mv /var/www/html/store /var/www/html/store-distribution
    ln -s /var/lib/phpbb/store /var/www/html/store
    if [ -s /var/lib/phpbb/config.php ]; then
        cp /var/lib/phpbb/config.php /var/www/html/config.php
        chown www-data:www-data /var/www/html/config.php
        chmod 640 /var/www/html/config.php
    fi
    chown -R www-data:www-data /var/lib/phpbb
    exec docker-php-entrypoint "$@"
fi

test -r /var/www/html/config.php || { echo 'Private phpBB config.php is missing.' >&2; exit 1; }
admin_dir="$(php -r 'define("IN_PHPBB", true); require "/var/www/html/config.php"; echo $phpbb_adm_relative_path;')"
admin_dir="${admin_dir%/}"
printf '%s' "$admin_dir" | grep -Eq '^acp-[0-9a-f]{18,32}$' || { echo 'Invalid private phpBB admin directory.' >&2; exit 1; }
if [ -d /var/www/html/adm ]; then
    mv /var/www/html/adm "/var/www/html/$admin_dir"
fi
test -d "/var/www/html/$admin_dir" || { echo 'phpBB admin directory is missing.' >&2; exit 1; }
test -s /var/lib/phpbb/forum.sqlite || { echo 'Forum database is missing.' >&2; exit 1; }
exec docker-php-entrypoint "$@"
