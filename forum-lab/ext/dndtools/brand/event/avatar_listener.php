<?php
namespace dndtools\brand\event;

use Symfony\Component\EventDispatcher\EventSubscriberInterface;

class avatar_listener implements EventSubscriberInterface
{
    private $template;
    private $user;

    public function __construct($template, $user)
    {
        $this->template = $template;
        $this->user = $user;
    }

    public static function getSubscribedEvents()
    {
        return [
            'core.page_header_after' => 'header_avatar',
            'core.memberlist_modify_memberrow' => 'member_avatar',
        ];
    }

    public function header_avatar($event)
    {
        $avatar = $this->thumbnail($this->user->data, 20);
        if ($avatar !== '')
        {
            $this->template->assign_var('CURRENT_USER_AVATAR', $avatar);
        }
    }

    public function member_avatar($event)
    {
        $memberrow = $event['memberrow'];
        $memberrow['DND_AVATAR_THUMB'] = $this->thumbnail($event['row'], 32);
        $event['memberrow'] = $memberrow;
    }

    private function thumbnail($row, $size)
    {
        if (empty($row['user_avatar']) || ($row['user_avatar_type'] ?? '') !== 'avatar.driver.upload')
        {
            return '';
        }
        $url = '/forum/download/file.php?avatar=' . rawurlencode($row['user_avatar']) . '&thumb=1';
        return '<img class="avatar" src="' . htmlspecialchars($url, ENT_QUOTES, 'UTF-8')
            . '" width="' . $size . '" height="' . $size . '" alt="">';
    }
}
