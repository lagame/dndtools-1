<?php
namespace dndtools\discussions\event;

use Symfony\Component\EventDispatcher\EventSubscriberInterface;

class posting_listener implements EventSubscriberInterface
{
    private $auth;
    private $db;
    private $request;
    private $template;
    private $user;
    private $table;
    private $root_path;

    private const FORUMS = [
        'spell' => 'Magias e talentos', 'feat' => 'Magias e talentos',
        'monster' => 'Monstros e templates', 'creature_template' => 'Monstros e templates',
        'character_class' => 'Classes e builds', 'character_class_variant' => 'Classes e builds',
        'race' => 'Classes e builds', 'skill' => 'Classes e builds',
        'skill_variant' => 'Classes e builds', 'item' => 'Livros, itens e referências',
        'rulebook' => 'Livros, itens e referências', 'supplemental' => 'Livros, itens e referências',
        'rule' => 'Dúvidas de regras', 'deity' => 'Dúvidas de regras',
        'language' => 'Dúvidas de regras',
    ];

    public function __construct($auth, $db, $request, $template, $user, $table, $root_path)
    {
        $this->auth = $auth;
        $this->db = $db;
        $this->request = $request;
        $this->template = $template;
        $this->user = $user;
        $this->table = $table;
        $this->root_path = $root_path;
    }

    public static function getSubscribedEvents()
    {
        return [
            'core.posting_modify_template_vars' => 'keep_record_context',
            'core.posting_modify_submit_post_before' => 'validate_record_context',
            'core.posting_modify_submit_post_after' => 'link_topic',
            'core.viewtopic_modify_page_title' => 'show_record_link',
        ];
    }

    public static function forum_id($db, $kind)
    {
        $name = self::FORUMS[$kind] ?? null;
        if (!$name) return 0;
        $sql = 'SELECT forum_id FROM ' . FORUMS_TABLE . " WHERE forum_name = '" . $db->sql_escape($name) . "' AND forum_type = " . FORUM_POST;
        $result = $db->sql_query($sql);
        $id = (int) $db->sql_fetchfield('forum_id');
        $db->sql_freeresult($result);
        return $id;
    }

    public static function record($kind, $id)
    {
        if (!isset(self::FORUMS[$kind]) || $id < 1) return null;
        $host = getenv('DND_FORUM_CATALOG_HOST') ?: 'localhost';
        $url = 'http://app:8765/forum-record/' . rawurlencode($kind) . '/' . (int) $id . '/';
        $context = stream_context_create(['http' => [
            'header' => "Host: $host\r\nX-Forwarded-Proto: https\r\n",
            'timeout' => 3, 'ignore_errors' => true,
        ]]);
        $body = @file_get_contents($url, false, $context);
        if ($body === false || !str_contains($http_response_header[0] ?? '', ' 200 ')) return null;
        $record = json_decode($body, true);
        if (!is_array($record) || !is_string($record['name'] ?? null) ||
            !is_string($record['path'] ?? null) || !str_starts_with($record['path'], '/') ||
            str_starts_with($record['path'], '//')) return null;
        return $record;
    }

    private function context()
    {
        $kind = $this->request->variable('dnd_kind', '');
        $id = $this->request->variable('dnd_id', 0);
        $type = $this->request->variable('dnd_type', 'discussion');
        return [$kind, $id, $type];
    }

    public function keep_record_context($event)
    {
        if ($event['mode'] !== 'post') return;
        [$kind, $id, $type] = $this->context();
        if (!$kind || !$id) return;
        $hidden_fields = $event['s_hidden_fields'] . build_hidden_fields([
            'dnd_kind' => $kind, 'dnd_id' => $id, 'dnd_type' => $type,
        ]);
        $event['s_hidden_fields'] = $hidden_fields;
        $page_data = $event['page_data'];
        $page_data['S_HIDDEN_FIELDS'] = $hidden_fields;
        $event['page_data'] = $page_data;
    }

    public function validate_record_context($event)
    {
        if ($event['mode'] !== 'post') return;
        [$kind, $id, $type] = $this->context();
        if (!$kind && !$id) return;
        if (!in_array($type, ['question', 'discussion', 'correction'], true) ||
            !self::record($kind, $id) || self::forum_id($this->db, $kind) !== (int) $event['forum_id'])
        {
            throw new \phpbb\exception\http_exception(400, 'INVALID_FORM');
        }
    }

    public function link_topic($event)
    {
        if (!in_array($event['mode'], ['post', 'reply', 'quote'], true)) return;
        [$kind, $id, $type] = $this->context();
        $topic_id = (int) ($event['data']['topic_id'] ?? $event['topic_id']);
        if (!$topic_id) return;
        if ($event['mode'] === 'post' && $kind && $id)
        {
            $sql = 'INSERT INTO ' . $this->table . ' ' . $this->db->sql_build_array('INSERT', [
                'topic_id' => $topic_id, 'record_kind' => $kind,
                'record_id' => $id, 'discussion_type' => $type,
            ]);
            $this->db->sql_query($sql);
        }
        $result = $this->db->sql_query('SELECT record_kind, record_id FROM ' . $this->table . ' WHERE topic_id = ' . $topic_id);
        $row = $this->db->sql_fetchrow($result);
        $this->db->sql_freeresult($result);
        if ($row) $this->notify_owner($topic_id, $row, $event['mode']);
    }

    private function notify_owner($topic_id, $row, $mode)
    {
        $result = $this->db->sql_query("SELECT user_id, username, user_email, user_lang FROM " . USERS_TABLE . " WHERE username_clean = 'ronassic'");
        $owner = $this->db->sql_fetchrow($result);
        $this->db->sql_freeresult($result);
        if (!$owner || !$owner['user_email'] || (int) $owner['user_id'] === (int) $this->user->data['user_id']) return;
        $record = self::record($row['record_kind'], (int) $row['record_id']);
        if (!$record) return;
        $lang = $owner['user_lang'] === 'pt_br' ? 'pt_br' : 'en';
        require_once $this->root_path . 'includes/functions_messenger.php';
        $messenger = new \messenger(false);
        $messenger->template('record_activity', $lang, $this->root_path . 'ext/dndtools/discussions/language/' . $lang . '/email');
        $messenger->to($owner['user_email'], $owner['username']);
        $messenger->assign_vars([
            'RECORD_NAME' => $record['name'],
            'AUTHOR' => $this->user->data['username'],
            'ACTION' => $lang === 'pt_br' ? ($mode === 'post' ? 'novo tópico' : 'nova resposta') : ($mode === 'post' ? 'new topic' : 'new reply'),
            'TOPIC_URL' => generate_board_url() . '/viewtopic.php?t=' . $topic_id,
        ]);
        $messenger->send(NOTIFY_EMAIL);
    }

    public function show_record_link($event)
    {
        $topic_id = (int) ($event['topic_data']['topic_id'] ?? 0);
        if (!$topic_id) return;
        $result = $this->db->sql_query('SELECT record_kind, record_id FROM ' . $this->table . ' WHERE topic_id = ' . $topic_id);
        $row = $this->db->sql_fetchrow($result);
        $this->db->sql_freeresult($result);
        if (!$row) return;
        $record = self::record($row['record_kind'], (int) $row['record_id']);
        if ($record)
        {
            $is_pt = $this->user->data['user_lang'] === 'pt_br';
            $path = $is_pt ? '/pt-br' . $record['path'] : $record['path'];
            $this->template->assign_vars(['DND_LINKED_RECORD_NAME' => $record['name'], 'DND_LINKED_RECORD_URL' => $path, 'DND_PT' => $is_pt]);
        }
    }
}
