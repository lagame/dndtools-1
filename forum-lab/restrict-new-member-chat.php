<?php
// New users can read chat, but must complete moderated forum posts before sending.
if (PHP_SAPI !== 'cli' || getenv('DND_FORUM_LAB') !== '1')
{
    fwrite(STDERR, "Local forum lab only.\n");
    exit(1);
}

define('IN_PHPBB', true);
$phpbb_root_path = '/var/www/html/';
$phpEx = 'php';
require $phpbb_root_path . 'common.' . $phpEx;

$result = $db->sql_query('SELECT group_id FROM ' . GROUPS_TABLE . " WHERE group_name = 'NEWLY_REGISTERED'");
$group_id = (int) $db->sql_fetchfield('group_id');
$db->sql_freeresult($result);
$result = $db->sql_query('SELECT auth_option_id FROM ' . ACL_OPTIONS_TABLE
    . " WHERE auth_option = 'u_stoker_chat_use'");
$option_id = (int) $db->sql_fetchfield('auth_option_id');
$db->sql_freeresult($result);
if (!$group_id || !$option_id)
{
    throw new RuntimeException('New-member group or LiteChat permission is missing.');
}

$where = 'group_id = ' . $group_id . ' AND forum_id = 0 AND auth_option_id = ' . $option_id
    . ' AND auth_role_id = 0';
$result = $db->sql_query('SELECT auth_setting FROM ' . ACL_GROUPS_TABLE . ' WHERE ' . $where);
$current = $db->sql_fetchfield('auth_setting');
$db->sql_freeresult($result);
if ($current === false)
{
    $db->sql_query('INSERT INTO ' . ACL_GROUPS_TABLE . ' ' . $db->sql_build_array('INSERT', [
        'group_id' => $group_id,
        'forum_id' => 0,
        'auth_option_id' => $option_id,
        'auth_setting' => ACL_NEVER,
        'auth_role_id' => 0,
    ]));
}
elseif ((int) $current !== ACL_NEVER)
{
    $db->sql_query('UPDATE ' . ACL_GROUPS_TABLE . ' SET auth_setting = ' . ACL_NEVER
        . ' WHERE ' . $where);
}

$auth->acl_clear_prefetch();
echo "New members cannot send chat messages until their initial posts are approved.\n";
