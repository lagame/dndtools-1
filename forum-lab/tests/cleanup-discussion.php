<?php
// Remove only a disposable local QA topic, preserving the rest of the forum.
if (PHP_SAPI !== 'cli' || getenv('DND_FORUM_LAB') !== '1')
{
    exit(1);
}
define('IN_PHPBB', true);
$phpbb_root_path = '/var/www/html/';
$phpEx = 'php';
require $phpbb_root_path . 'common.' . $phpEx;
require_once $phpbb_root_path . 'includes/functions_admin.' . $phpEx;
$id = (int) ($argv[1] ?? 0);
if ($id < 1)
{
    exit(1);
}
$result = $db->sql_query('SELECT topic_title FROM ' . TOPICS_TABLE . ' WHERE topic_id = ' . $id);
$title = $db->sql_fetchfield('topic_title');
$db->sql_freeresult($result);
if (!is_string($title) || !str_starts_with($title, 'Catalog discussion QA '))
{
    throw new RuntimeException('Refusing to delete a non-QA topic.');
}
$db->sql_query('DELETE FROM ' . $table_prefix . 'dnd_record_topics WHERE topic_id = ' . $id);
delete_topics('topic_id', [$id]);
echo "Temporary discussion removed.\n";
