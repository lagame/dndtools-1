<?php
// Run only in the backed-up local forum lab: DND_FORUM_LAB=1 php seed-forums.php
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

$structure = [
    'Comece aqui' => [
        'Apresentações e ajuda' => 'Conheça a comunidade, peça orientação e aprenda a usar o fórum e o catálogo.',
    ],
    'Regras e fontes' => [
        'Dúvidas de regras' => 'Debata D&D 3.5 com livro, página e contexto da dúvida.',
        'Correções do catálogo' => 'Indique erros, fontes e edições nas fichas do D&D Tools.',
    ],
    'Personagens e opções' => [
        'Classes e builds' => 'Planeje personagens e combinações de classes com objetivo e nível claros.',
        'Magias e talentos' => 'Converse sobre magias, talentos, pré-requisitos e interações.',
        'Livros, itens e referências' => 'Discuta suplementos, equipamentos, fontes e referências do catálogo.',
    ],
    'Bestiário e mesas' => [
        'Monstros e templates' => 'Discuta criaturas, templates, encontros e fontes oficiais.',
        'Campanhas e encontros' => 'Compartilhe ideias de mesa, relatos e dúvidas de mestres e jogadores.',
    ],
    'Comunidade e eventos' => [
        'Encontre uma mesa' => 'Procure jogadores ou mestres para mesas presenciais e online de D&D 3.5.',
        'Eventos de RPG' => 'Divulgue encontros, convenções e atividades de RPG com data e local.',
    ],
];

function find_forum($name, $parent_id)
{
    global $db;
    $sql = "SELECT forum_id FROM " . FORUMS_TABLE . " WHERE forum_name = '" . $db->sql_escape($name) . "' AND parent_id = " . (int) $parent_id;
    $result = $db->sql_query($sql);
    $row = $db->sql_fetchrow($result);
    $db->sql_freeresult($result);
    return $row ? (int) $row['forum_id'] : 0;
}

function create_forum($name, $description, $parent_id, $type, $permissions_from)
{
    $existing = find_forum($name, $parent_id);
    if ($existing)
    {
        global $db;
        $result = $db->sql_query('SELECT COUNT(*) AS permission_count FROM ' . ACL_GROUPS_TABLE . ' WHERE forum_id = ' . $existing);
        $permission_count = (int) $db->sql_fetchfield('permission_count');
        $db->sql_freeresult($result);
        if (!$permission_count && !copy_forum_permissions($permissions_from, $existing))
        {
            throw new RuntimeException('Could not copy forum permissions for ' . $name);
        }
        return $existing;
    }
    $data = [
        'parent_id' => $parent_id, 'forum_type' => $type, 'forum_status' => ITEM_UNLOCKED,
        'forum_parents' => '', 'forum_name' => $name, 'forum_link' => '',
        'forum_link_track' => false, 'forum_desc' => $description,
        'forum_desc_uid' => '', 'forum_desc_options' => 7, 'forum_desc_bitfield' => '',
        'forum_rules' => '', 'forum_rules_uid' => '', 'forum_rules_options' => 7,
        'forum_rules_bitfield' => '', 'forum_rules_link' => '', 'forum_image' => '',
        'forum_style' => 0, 'display_subforum_list' => true,
        'display_subforum_limit' => false, 'display_on_index' => true,
        'show_active' => false,
        'forum_topics_per_page' => 0, 'enable_indexing' => true,
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
    if (!copy_forum_permissions($permissions_from, $data['forum_id']))
    {
        throw new RuntimeException('Could not copy forum permissions for ' . $name);
    }
    echo $name . ': ' . $data['forum_id'] . "\n";
    return (int) $data['forum_id'];
}

$category_permissions_from = find_forum('Comece aqui', 0) ?: 1;
$forum_permissions_from = find_forum('Apresentações e ajuda', $category_permissions_from) ?: 2;
foreach ($structure as $category => $forums)
{
    $category_id = create_forum($category, '', 0, FORUM_CAT, $category_permissions_from);
    foreach ($forums as $name => $description)
    {
        create_forum($name, $description, $category_id, FORUM_POST, $forum_permissions_from);
    }
}
$cache->destroy('sql', FORUMS_TABLE);
$auth->acl_clear_prefetch();
