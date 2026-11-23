<?php
// Read-only production/lab audit of Markdown availability for a regular member.
if (PHP_SAPI !== 'cli' || (getenv('DND_FORUM_LAB') !== '1' && getenv('DND_FORUM_PRODUCTION') !== '1'))
{
    fwrite(STDERR, "Forum container only.\n");
    exit(1);
}

define('IN_PHPBB', true);
$phpbb_root_path = '/var/www/html/';
$phpEx = 'php';
require $phpbb_root_path . 'common.' . $phpEx;

if (!$phpbb_container->get('ext.manager')->is_enabled('alfredoramos/markdown'))
{
    throw new RuntimeException('Markdown extension is disabled.');
}
foreach (['allow_markdown', 'allow_post_markdown', 'allow_pm_markdown', 'allow_sig_markdown'] as $key)
{
    if (empty($config[$key]))
    {
        throw new RuntimeException("Markdown setting is disabled: $key");
    }
}

$result = $db->sql_query_limit('SELECT * FROM ' . USERS_TABLE
    . ' WHERE user_type = ' . USER_NORMAL . ' AND user_allow_markdown = 1 ORDER BY user_id', 1);
$member = $db->sql_fetchrow($result);
$db->sql_freeresult($result);
if (!$member)
{
    throw new RuntimeException('No active regular member with Markdown enabled.');
}

$auth->acl($member);
if (!$auth->acl_get('u_post_markdown'))
{
    throw new RuntimeException('Regular member lacks Markdown posting permission.');
}

$forum_name = 'Magias e talentos';
$result = $db->sql_query('SELECT forum_id FROM ' . FORUMS_TABLE
    . " WHERE forum_name = '" . $db->sql_escape($forum_name) . "' AND forum_type = " . FORUM_POST);
$forum_id = (int) $db->sql_fetchfield('forum_id');
$db->sql_freeresult($result);
if (!$forum_id || !$auth->acl_get('f_markdown', $forum_id))
{
    throw new RuntimeException('Regular member lacks Markdown permission in the catalog discussion forum.');
}

echo "Markdown extension, board settings, regular member preference and posting permissions: OK.\n";
