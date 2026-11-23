<?php
// Activated members can chat; their first forum posts remain moderated.
if (PHP_SAPI !== 'cli' || (getenv('DND_FORUM_LAB') !== '1' && getenv('DND_FORUM_PRODUCTION') !== '1'))
{
    fwrite(STDERR, "Forum container only.\n");
    exit(1);
}

define('IN_PHPBB', true);
$phpbb_root_path = '/var/www/html/';
$phpEx = 'php';
require $phpbb_root_path . 'common.' . $phpEx;
if ((int) $config['require_activation'] !== 1 || (int) $config['new_member_post_limit'] < 3)
{
    throw new RuntimeException('Email activation and moderation must remain enabled.');
}

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
        'auth_setting' => ACL_YES,
        'auth_role_id' => 0,
    ]));
}
elseif ((int) $current !== ACL_YES)
{
    $db->sql_query('UPDATE ' . ACL_GROUPS_TABLE . ' SET auth_setting = ' . ACL_YES
        . ' WHERE ' . $where);
}

$config->set('stoker_chat_flood_interval', 15);
$auth->acl_clear_prefetch();
echo "Activated members can chat; first forum posts remain moderated; chat flood interval is 15 seconds.\n";
