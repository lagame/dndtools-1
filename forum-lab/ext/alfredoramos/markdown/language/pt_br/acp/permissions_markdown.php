<?php
/**
 * Brazilian Portuguese strings for the Markdown extension.
 * @license GPL-2.0-only
 */
if (!defined('IN_PHPBB'))
{
    exit;
}

if (empty($lang) || !is_array($lang))
{
    $lang = [];
}

$lang = array_merge($lang, [
    'ACL_F_MARKDOWN' => 'Pode usar Markdown',
    'ACL_U_POST_MARKDOWN' => 'Pode usar Markdown',
    'ACL_U_PM_MARKDOWN' => 'Pode usar Markdown nas mensagens privadas',
    'ACL_U_SIG_MARKDOWN' => 'Pode usar Markdown na assinatura',
]);
