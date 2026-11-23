<?php
// Apply the local forum's avatar limits once; do not overwrite later ACP choices on startup.
if (PHP_SAPI !== 'cli' || getenv('DND_FORUM_LAB') !== '1')
{
    fwrite(STDERR, "Local forum lab only.\n");
    exit(1);
}

define('IN_PHPBB', true);
$phpbb_root_path = '/var/www/html/';
$phpEx = 'php';
require $phpbb_root_path . 'common.' . $phpEx;

$config->set('avatar_max_width', 300);
$config->set('avatar_max_height', 300);
$config->set('avatar_filesize', 512 * 1024);

echo "Avatar limits: 300 x 300 px, 512 KiB.\n";
