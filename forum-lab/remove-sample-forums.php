<?php
// Remove only the verified phpBB installer examples from the backed-up local lab.
if (PHP_SAPI !== 'cli' || getenv('DND_FORUM_LAB') !== '1')
{
    fwrite(STDERR, "Local forum lab only.\n");
    exit(1);
}
define('IN_PHPBB', true);
$phpbb_root_path = '/var/www/html/';
$phpEx = 'php';
require $phpbb_root_path . 'common.' . $phpEx;
require_once $phpbb_root_path . 'includes/functions_admin.' . $phpEx;
require_once $phpbb_root_path . 'includes/functions_acp.' . $phpEx;
require_once $phpbb_root_path . 'includes/acp/acp_forums.' . $phpEx;
$user->session_begin();
$auth->acl($user->data);
$user->setup('acp/forums');

$result = $db->sql_query('SELECT forum_id, forum_name, parent_id FROM ' . FORUMS_TABLE . ' WHERE forum_id IN (1,2) ORDER BY forum_id');
$forums = $db->sql_fetchrowset($result);
$db->sql_freeresult($result);
if (count($forums) !== 2 || $forums[0]['forum_name'] !== 'Your first category'
    || $forums[1]['forum_name'] !== 'Your first forum' || (int) $forums[1]['parent_id'] !== 1)
{
    throw new RuntimeException('The sample forum structure has changed; no deletion performed.');
}
$result = $db->sql_query('SELECT topic_title FROM ' . TOPICS_TABLE . ' WHERE forum_id IN (1,2) ORDER BY topic_title');
$titles = [];
while ($row = $db->sql_fetchrow($result))
{
    $titles[] = $row['topic_title'];
}
$db->sql_freeresult($result);
if ($titles !== ['Catalog discussion prototype', 'Welcome to phpBB3'])
{
    throw new RuntimeException('Sample forum content has changed; no deletion performed.');
}
$manager = new acp_forums();
$errors = $manager->delete_forum(1);
if ($errors)
{
    throw new RuntimeException(implode('; ', $errors));
}
echo "Installer category and prototype removed from local lab.\n";
