<?php
// Repair legacy founder topics whose cached first-poster name is blank.
if (PHP_SAPI !== 'cli' || (getenv('DND_FORUM_LAB') !== '1' && getenv('DND_FORUM_PRODUCTION') !== '1'))
{
    fwrite(STDERR, "Forum container only.\n");
    exit(1);
}

define('IN_PHPBB', true);
$phpbb_root_path = '/var/www/html/';
$phpEx = 'php';
require $phpbb_root_path . 'common.' . $phpEx;

$result = $db->sql_query("SELECT user_id, username, user_type FROM " . USERS_TABLE . " WHERE username_clean = 'ronassic'");
$owner = $db->sql_fetchrow($result);
$db->sql_freeresult($result);
if (!$owner || (int) $owner['user_type'] !== USER_FOUNDER)
{
    throw new RuntimeException('Founder Ronassic was not found.');
}

$result = $db->sql_query('SELECT t.topic_id, p.poster_id FROM ' . TOPICS_TABLE . ' t JOIN '
    . POSTS_TABLE . ' p ON p.post_id = t.topic_first_post_id WHERE t.topic_poster = '
    . (int) $owner['user_id'] . " AND t.topic_first_poster_name = ''");
$topic_ids = [];
while ($topic = $db->sql_fetchrow($result))
{
    if ((int) $topic['poster_id'] !== (int) $owner['user_id'])
    {
        throw new RuntimeException('Topic author does not match its first post.');
    }
    $topic_ids[] = (int) $topic['topic_id'];
}
$db->sql_freeresult($result);

foreach ($topic_ids as $topic_id)
{
    $db->sql_query('UPDATE ' . TOPICS_TABLE . " SET topic_first_poster_name = '"
        . $db->sql_escape($owner['username']) . "' WHERE topic_id = " . $topic_id
        . " AND topic_first_poster_name = ''");
}
echo 'Repaired ' . count($topic_ids) . " topic author labels.\n";
