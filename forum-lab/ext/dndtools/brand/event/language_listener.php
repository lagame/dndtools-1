<?php
namespace dndtools\brand\event;

use Symfony\Component\EventDispatcher\EventSubscriberInterface;
use phpbb\request\request_interface;

class language_listener implements EventSubscriberInterface
{
    private $request;

    public function __construct(request_interface $request)
    {
        $this->request = $request;
    }

    public static function getSubscribedEvents()
    {
        return [
            'core.user_setup' => 'use_catalog_language',
            'core.ucp_prefs_personal_update_data' => 'save_forum_language',
        ];
    }

    public function use_catalog_language($event)
    {
        $cookie = $this->request->variable('django_language', '', false, request_interface::COOKIE);
        if ($cookie === 'pt-br' || $cookie === 'en-us')
        {
            $event['user_lang_name'] = $cookie === 'pt-br' ? 'pt_br' : 'en';
        }
        elseif (!empty($event['user_data']['user_id']) && $event['user_data']['user_id'] > 1)
        {
            $this->set_language_cookie($event['user_lang_name']);
        }
    }

    public function save_forum_language($event)
    {
        $this->set_language_cookie($event['data']['lang']);
    }

    private function set_language_cookie($forum_language)
    {
        if ($forum_language !== 'pt_br' && $forum_language !== 'en')
        {
            return;
        }
        $language = $forum_language === 'pt_br' ? 'pt-br' : 'en-us';
        setcookie('django_language', $language, [
            'expires' => time() + 31536000,
            'path' => '/',
            'secure' => $this->request->is_secure(),
            'httponly' => true,
            'samesite' => 'Lax',
        ]);
        $this->request->overwrite('django_language', $language, request_interface::COOKIE);
    }
}
