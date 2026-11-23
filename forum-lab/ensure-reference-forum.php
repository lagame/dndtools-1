<?php
// Idempotently provide the forum used by catalog books and items.
if (PHP_SAPI !== 'cli' || (getenv('DND_FORUM_LAB') !== '1' && getenv('DND_FORUM_PRODUCTION') !== '1'))
{
    fwrite(STDERR, "Forum maintenance command only.\n");
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

function forum_id($name, $parent_id, $type)
{
    global $db;
    $sql = 'SELECT forum_id FROM ' . FORUMS_TABLE . " WHERE forum_name = '" . $db->sql_escape($name) .
        "' AND parent_id = " . (int) $parent_id . ' AND forum_type = ' . (int) $type;
    $result = $db->sql_query($sql);
    $id = (int) $db->sql_fetchfield('forum_id');
    $db->sql_freeresult($result);
    return $id;
}

$parent_id = forum_id('Personagens e opções', 0, FORUM_CAT);
$source_id = forum_id('Magias e talentos', $parent_id, FORUM_POST);
if (!$parent_id || !$source_id)
{
    throw new RuntimeException('Expected category or permission source forum is missing.');
}

$name = 'Livros, itens e referências';
$forum_id = forum_id($name, $parent_id, FORUM_POST);
if (!$forum_id)
{
    $data = [
        'parent_id' => $parent_id, 'forum_type' => FORUM_POST, 'forum_status' => ITEM_UNLOCKED,
        'forum_parents' => '', 'forum_name' => $name, 'forum_link' => '',
        'forum_link_track' => false,
        'forum_desc' => 'Discuta suplementos, equipamentos, fontes e referências do catálogo.',
        'forum_desc_uid' => '', 'forum_desc_options' => 7, 'forum_desc_bitfield' => '',
        'forum_rules' => '', 'forum_rules_uid' => '', 'forum_rules_options' => 7,
        'forum_rules_bitfield' => '', 'forum_rules_link' => '', 'forum_image' => '',
        'forum_style' => 0, 'display_subforum_list' => true,
        'display_subforum_limit' => false, 'display_on_index' => true,
        'show_active' => false, 'forum_topics_per_page' => 0, 'enable_indexing' => true,
        'enable_icons' => true, 'enable_prune' => false,
        'enable_post_review' => true, 'enable_quick_reply' => true,
        'enable_shadow_prune' => false, 'prune_days' => 7,
        'prune_viewed' => 7, 'prune_freq' => 1, 'prune_old_polls' => false,
        'prune_announce' => false, 'prune_sticky' => false,
        'prune_shadow_days' => 7, 'prune_shadow_freq' => 1,
        'forum_password' => '', 'forum_password_confirm' => '',
        'forum_password_unset' => false,
    ];
    $manager = new acp_forums();
    $errors = $manager->update_forum_data($data);
    if ($errors)
    {
        throw new RuntimeException(implode('; ', $errors));
    }
    $forum_id = (int) $data['forum_id'];
}

$result = $db->sql_query('SELECT COUNT(*) AS permission_count FROM ' . ACL_GROUPS_TABLE . ' WHERE forum_id = ' . $forum_id);
$permission_count = (int) $db->sql_fetchfield('permission_count');
$db->sql_freeresult($result);
if (!$permission_count && !copy_forum_permissions($source_id, $forum_id))
{
    throw new RuntimeException('Could not copy forum permissions.');
}
$cache->destroy('sql', FORUMS_TABLE);
$auth->acl_clear_prefetch();
echo $name . ': ' . $forum_id . "\n";
