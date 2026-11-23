<?php
// Temporary local test account helper. Never ship or run on production.
if (PHP_SAPI !== 'cli' || getenv('DND_FORUM_LAB') !== '1')
{
    fwrite(STDERR, "Local forum lab only.\n");
    exit(1);
}

define('IN_PHPBB', true);
$phpbb_root_path = '/var/www/html/';
$phpEx = 'php';
require $phpbb_root_path . 'common.' . $phpEx;
require_once $phpbb_root_path . 'includes/functions_user.' . $phpEx;

$action = $argv[1] ?? '';
$username = $argv[2] ?? '';
if (!preg_match('/^chatqa_[a-f0-9]{8}$/', $username))
{
    throw new RuntimeException('Invalid temporary username.');
}

if ($action === 'create')
{
    $password = rtrim(stream_get_contents(STDIN), "\r\n");
    if (strlen($password) < 12)
    {
        throw new RuntimeException('Missing test password.');
    }
    $result = $db->sql_query("SELECT group_id FROM " . GROUPS_TABLE . " WHERE group_name = 'REGISTERED'");
    $group_id = (int) $db->sql_fetchfield('group_id');
    $db->sql_freeresult($result);
    if (!$group_id)
    {
        throw new RuntimeException('Registered group not found.');
    }
    $user_id = user_add([
        'username' => $username,
        'user_password' => $phpbb_container->get('passwords.manager')->hash($password),
        'user_email' => $username . '@example.test',
        'group_id' => $group_id,
        'user_type' => USER_NORMAL,
        'user_lang' => 'pt_br',
        'user_ip' => '127.0.0.1',
    ]);
    unset($password);
    if (!is_int($user_id))
    {
        throw new RuntimeException('Test user was not created.');
    }
    echo "Created temporary user.\n";
}
elseif ($action === 'delete')
{
    $result = $db->sql_query("SELECT user_id FROM " . USERS_TABLE . " WHERE username_clean = '" . $db->sql_escape($username) . "'");
    $user_id = (int) $db->sql_fetchfield('user_id');
    $db->sql_freeresult($result);
    if ($user_id)
    {
        user_delete('remove', $user_id);
    }
    echo "Temporary user removed.\n";
}
else
{
    throw new RuntimeException('Use create or delete.');
}
