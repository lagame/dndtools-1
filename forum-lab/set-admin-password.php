<?php
// Run inside the phpBB container. Read the new password from stdin, never argv.
define('IN_PHPBB', true);
$phpbb_root_path = '/var/www/html/';
$phpEx = 'php';
require $phpbb_root_path . 'common.' . $phpEx;

$password = fgets(STDIN);
if ($password === false) {
    fwrite(STDERR, "No password supplied.\n");
    exit(1);
}
$password = rtrim($password, "\r\n");
if (strlen($password) < 8 || strlen($password) > 128) {
    fwrite(STDERR, "Password must contain 8 to 128 bytes.\n");
    exit(1);
}

$sql = 'SELECT user_id, user_type FROM ' . USERS_TABLE . " WHERE username_clean = 'ronassic'";
$result = $db->sql_query($sql);
$account = $db->sql_fetchrow($result);
$db->sql_freeresult($result);
if (!$account || (int) $account['user_type'] !== USER_FOUNDER) {
    fwrite(STDERR, "Ronassic founder account was not found.\n");
    exit(1);
}

$hash = $phpbb_container->get('passwords.manager')->hash($password);
unset($password);
$sql = 'UPDATE ' . USERS_TABLE . " SET user_password = '" . $db->sql_escape($hash) .
    "' WHERE user_id = " . (int) $account['user_id'];
$db->sql_query($sql);
if ($db->sql_affectedrows() !== 1) {
    fwrite(STDERR, "Password update was not confirmed.\n");
    exit(1);
}
fwrite(STDOUT, "Ronassic password updated.\n");
