<?php
// Enable the catalog discussion and Markdown extensions after a verified forum backup.
if (PHP_SAPI !== 'cli' || (getenv('DND_FORUM_LAB') !== '1' && getenv('DND_FORUM_PRODUCTION') !== '1'))
{
    fwrite(STDERR, "Forum container only.\n");
    exit(1);
}

define('IN_PHPBB', true);
$phpbb_root_path = '/var/www/html/';
$phpEx = 'php';
require $phpbb_root_path . 'common.' . $phpEx;

$extensions = $phpbb_container->get('ext.manager');
foreach (['dndtools/discussions', 'alfredoramos/markdown'] as $name)
{
    if (!$extensions->is_enabled($name))
    {
        if (!$extensions->is_available($name))
        {
            throw new RuntimeException("Extension unavailable: $name");
        }
        $extensions->enable($name);
    }
    fwrite(STDOUT, "Enabled: $name\n");
}
$cache->purge();
