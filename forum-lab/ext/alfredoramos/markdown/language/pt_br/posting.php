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
    'MARKDOWN_STATUS_FORMAT' => '<a href="%1$s">Markdown</a> está <em>%2$s</em>',
    'MARKDOWN_IS_ON' => 'ativado',
    'MARKDOWN_IS_OFF' => 'desativado',
    'DISABLE_MARKDOWN' => 'Desativar Markdown',
]);
