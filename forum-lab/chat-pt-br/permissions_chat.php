<?php
// Brazilian Portuguese strings for Ajax LiteChat 2.1.0 (GPL-2.0-only).
if (!defined('IN_PHPBB')) { exit; }
if (empty($lang) || !is_array($lang)) { $lang = []; }
$lang = array_merge($lang, [
    'ACL_U_STOKER_CHAT_VIEW' => 'Pode visualizar o chat',
    'ACL_U_STOKER_CHAT_USE' => 'Pode usar o chat',
    'ACL_U_STOKER_CHAT_EDIT' => 'Pode editar as próprias mensagens do chat',
    'ACL_U_STOKER_CHAT_DELETE' => 'Pode excluir as próprias mensagens do chat',
    'ACL_U_STOKER_CHAT_QUOTE' => 'Pode citar mensagens do chat',
    'ACL_U_STOKER_CHAT_LIKE' => 'Pode curtir mensagens do chat',
    'ACL_U_STOKER_CHAT_NOFLOOD' => 'Pode ignorar o intervalo mínimo entre mensagens',
    'ACL_M_STOKER_CHAT_MODERATE' => 'Pode editar e excluir qualquer mensagem do chat',
]);
