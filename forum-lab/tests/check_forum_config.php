<?php
// Read-only checks for the local lab; run after the forum has been initialized.
if (PHP_SAPI !== 'cli' || getenv('DND_FORUM_LAB') !== '1')
{
    fwrite(STDERR, "Local forum lab only.\n");
    exit(1);
}

define('IN_PHPBB', true);
$phpbb_root_path = '/var/www/html/';
$phpEx = 'php';
require $phpbb_root_path . 'common.' . $phpEx;

$expected = [
    'avatar_max_width' => 300,
    'avatar_max_height' => 300,
    'avatar_filesize' => 512 * 1024,
    'require_activation' => 1,
    'enable_confirm' => 1,
];
foreach ($expected as $key => $value)
{
    if ((int) $config[$key] !== $value)
    {
        throw new RuntimeException("Unexpected forum setting: $key");
    }
}
if ((int) $config['new_member_post_limit'] < 3)
{
    throw new RuntimeException('First posts must enter the new-member moderation flow.');
}

$result = $db->sql_query('SELECT group_id FROM ' . GROUPS_TABLE . " WHERE group_name = 'NEWLY_REGISTERED'");
$new_member_group = (int) $db->sql_fetchfield('group_id');
$db->sql_freeresult($result);
if (!$new_member_group)
{
    throw new RuntimeException('New-member group is missing.');
}

$forum_count = 0;
$result = $db->sql_query('SELECT forum_id FROM ' . FORUMS_TABLE . ' WHERE forum_type = 1');
while ($row = $db->sql_fetchrow($result))
{
    $forum_id = (int) $row['forum_id'];
    if ($auth->acl_get('f_post', $forum_id) || $auth->acl_get('f_reply', $forum_id))
    {
        throw new RuntimeException("Guest can post in forum $forum_id");
    }
    $forum_count++;
}
$db->sql_freeresult($result);
if (!$forum_count)
{
    throw new RuntimeException('No discussion forums found.');
}
foreach (['Encontre uma mesa', 'Eventos de RPG'] as $name)
{
    $sql = 'SELECT COUNT(*) AS forum_count FROM ' . FORUMS_TABLE . ' child JOIN ' . FORUMS_TABLE
        . " parent ON child.parent_id = parent.forum_id WHERE parent.forum_name = 'Comunidade e eventos'"
        . " AND child.forum_name = '" . $db->sql_escape($name) . "' AND child.forum_type = 1";
    $result = $db->sql_query($sql);
    $found = (int) $db->sql_fetchfield('forum_count');
    $db->sql_freeresult($result);
    if ($found !== 1)
    {
        throw new RuntimeException("Missing community forum: $name");
    }
}

$sql = 'SELECT COUNT(*) AS count FROM ' . ACL_GROUPS_TABLE . ' ag JOIN ' . ACL_ROLES_TABLE
    . ' ar ON ar.role_id = ag.auth_role_id WHERE ag.group_id = ' . $new_member_group
    . " AND ar.role_name = 'ROLE_FORUM_NEW_MEMBER'";
$result = $db->sql_query($sql);
$moderated_forums = (int) $db->sql_fetchfield('count');
$db->sql_freeresult($result);
if ($moderated_forums !== $forum_count)
{
    throw new RuntimeException('New-member moderation role is missing on a forum.');
}

$sql = 'SELECT ag.auth_setting FROM ' . ACL_GROUPS_TABLE . ' ag JOIN ' . ACL_OPTIONS_TABLE
    . ' ao ON ao.auth_option_id = ag.auth_option_id WHERE ag.group_id = ' . $new_member_group
    . " AND ag.forum_id = 0 AND ao.auth_option = 'u_stoker_chat_use'";
$result = $db->sql_query($sql);
$chat_setting = $db->sql_fetchfield('auth_setting');
$db->sql_freeresult($result);
if ($chat_setting === false || (int) $chat_setting !== ACL_YES)
{
    throw new RuntimeException('Activated new members cannot use the chat.');
}
if ($auth->acl_get('u_stoker_chat_use'))
{
    throw new RuntimeException('Guests can send chat messages.');
}
if ((int) $config['stoker_chat_flood_interval'] < 15)
{
    throw new RuntimeException('Chat flood interval is too short.');
}

echo "Avatar limits, e-mail activation, CAPTCHA, guest restrictions, moderated posts and chat pacing checked in $forum_count forums.\n";
