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
    'ALLOW_MARKDOWN' => 'Permitir Markdown',
    'ALLOW_POST_MARKDOWN' => 'Permitir Markdown nas mensagens',
    'ALLOW_PM_MARKDOWN' => 'Permitir Markdown nas mensagens privadas',
    'ALLOW_SIG_MARKDOWN' => 'Permitir Markdown nas assinaturas',
]);
