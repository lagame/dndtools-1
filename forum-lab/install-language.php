<?php
// Run once after the phpBB database is installed. Safe to repeat on later releases.
define('IN_PHPBB', true);
$phpbb_root_path = '/var/www/html/';
$phpEx = 'php';
require $phpbb_root_path . 'common.' . $phpEx;

$iso = 'pt_br';
$info_file = $phpbb_root_path . 'language/' . $iso . '/iso.txt';
if (!is_readable($info_file)) {
    fwrite(STDERR, "Brazilian Portuguese language pack is missing.\n");
    exit(1);
}

$result = $db->sql_query('SELECT lang_id FROM ' . LANG_TABLE . " WHERE lang_iso = 'pt_br'");
$installed = (bool) $db->sql_fetchrow($result);
$db->sql_freeresult($result);

if (!$installed) {
    $info = file($info_file, FILE_IGNORE_NEW_LINES);
    if (count($info) < 3 || !$info[0] || !$info[1]) {
        fwrite(STDERR, "Brazilian Portuguese language pack metadata is invalid.\n");
        exit(1);
    }

    $db->sql_transaction('begin');
    $db->sql_query('INSERT INTO ' . LANG_TABLE . ' ' . $db->sql_build_array('INSERT', [
        'lang_iso' => $iso,
        'lang_dir' => $iso,
        'lang_english_name' => htmlspecialchars($info[0], ENT_COMPAT),
        'lang_local_name' => htmlspecialchars($info[1], ENT_COMPAT, 'UTF-8'),
        'lang_author' => htmlspecialchars($info[2], ENT_COMPAT, 'UTF-8'),
    ]));
    $language_id = (int) $db->sql_nextid();

    $result = $db->sql_query('SELECT lang_id FROM ' . LANG_TABLE . " WHERE lang_iso = 'en'");
    $english_id = (int) $db->sql_fetchfield('lang_id');
    $db->sql_freeresult($result);

    foreach ([
        PROFILE_LANG_TABLE => 'field_id, lang_name, lang_explain, lang_default_value',
        PROFILE_FIELDS_LANG_TABLE => 'field_id, option_id, field_type, lang_value',
    ] as $table => $columns) {
        $result = $db->sql_query("SELECT $columns FROM $table WHERE lang_id = $english_id");
        while ($row = $db->sql_fetchrow($result)) {
            $row['lang_id'] = $language_id;
            $db->sql_query('INSERT INTO ' . $table . ' ' . $db->sql_build_array('INSERT', $row));
        }
        $db->sql_freeresult($result);
    }

    // The existing founder was created before this pack was available.
    $db->sql_query('UPDATE ' . USERS_TABLE . " SET user_lang = 'pt_br' WHERE username_clean = 'ronassic' AND user_lang = 'en'");
    $db->sql_transaction('commit');
}

$config->set('default_lang', $iso);
fwrite(STDOUT, "Brazilian Portuguese installed and set as forum default.\n");
