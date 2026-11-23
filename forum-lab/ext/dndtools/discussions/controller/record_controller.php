<?php
namespace dndtools\discussions\controller;

use Symfony\Component\HttpFoundation\Response;

class record_controller
{
    private $auth;
    private $db;
    private $helper;
    private $template;
    private $user;
    private $table;

    public function __construct($auth, $db, $helper, $template, $user, $table)
    {
        $this->auth = $auth;
        $this->db = $db;
        $this->helper = $helper;
        $this->template = $template;
        $this->user = $user;
        $this->table = $table;
    }

    public function display($kind, $id): Response
    {
        $id = (int) $id;
        $record = \dndtools\discussions\event\posting_listener::record($kind, $id);
        if (!$record)
        {
            throw new \phpbb\exception\http_exception(404, 'NO_FORUM');
        }

        $forum_id = \dndtools\discussions\event\posting_listener::forum_id($this->db, $kind);
        $can_post = $forum_id && $this->user->data['is_registered'] && $this->auth->acl_get('f_post', $forum_id);
        $sql = 'SELECT m.topic_id, m.discussion_type, t.topic_title, t.topic_posts_approved, t.topic_last_post_time,
                    t.topic_visibility, t.topic_poster, t.forum_id
                FROM ' . $this->table . ' m JOIN ' . TOPICS_TABLE . ' t ON t.topic_id = m.topic_id
                WHERE m.record_kind = \'' . $this->db->sql_escape($kind) . '\' AND m.record_id = ' . $id . '
                ORDER BY t.topic_last_post_time DESC';
        $result = $this->db->sql_query_limit($sql, 40);
        while ($row = $this->db->sql_fetchrow($result))
        {
            $fid = (int) $row['forum_id'];
            if (!$this->auth->acl_get('f_read', $fid) || !$this->auth->acl_get('f_list', $fid))
            {
                continue;
            }
            if ((int) $row['topic_visibility'] !== ITEM_APPROVED &&
                (int) $row['topic_poster'] !== (int) $this->user->data['user_id'] &&
                !$this->auth->acl_get('m_approve', $fid))
            {
                continue;
            }
            $this->template->assign_block_vars('discussions', [
                'TITLE' => $row['topic_title'],
                'TYPE' => $row['discussion_type'],
                'REPLIES' => max(0, (int) $row['topic_posts_approved'] - 1),
                'UPDATED' => $this->user->format_date($row['topic_last_post_time']),
                'PENDING' => (int) $row['topic_visibility'] !== ITEM_APPROVED,
                'URL' => '/forum/viewtopic.php?t=' . (int) $row['topic_id'],
            ]);
        }
        $this->db->sql_freeresult($result);

        $this->template->assign_vars([
            'DND_RECORD_NAME' => $record['name'],
            'DND_RECORD_PATH' => $record['path'],
            'DND_CAN_POST' => $can_post,
            'DND_POST_URL' => $can_post ? '/forum/posting.php?mode=post&f=' . $forum_id . '&dnd_kind=' . rawurlencode($kind) . '&dnd_id=' . $id : '',
            'DND_LOGIN_URL' => '/forum/ucp.php?mode=login',
            'DND_REGISTER_URL' => '/forum/ucp.php?mode=register',
            'DND_PT' => $this->user->data['user_lang'] === 'pt_br',
        ]);
        return $this->helper->render('record.html', $record['name'], 200, true);
    }
}
