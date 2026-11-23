<?php
// Populate the backed-up local lab only. Review content before any production use.
if (PHP_SAPI !== 'cli' || getenv('DND_FORUM_LAB') !== '1')
{
    fwrite(STDERR, "Local forum lab only.\n");
    exit(1);
}

define('IN_PHPBB', true);
$phpbb_root_path = '/var/www/html/';
$phpEx = 'php';
require $phpbb_root_path . 'common.' . $phpEx;
require_once $phpbb_root_path . 'includes/functions_posting.' . $phpEx;
require_once $phpbb_root_path . 'includes/functions_content.' . $phpEx;
$user->session_begin();

$result = $db->sql_query("SELECT * FROM " . USERS_TABLE . " WHERE username_clean = 'ronassic'");
$owner = $db->sql_fetchrow($result);
$db->sql_freeresult($result);
if (!$owner || (int) $owner['user_type'] != USER_FOUNDER)
{
    throw new RuntimeException('Local founder Ronassic was not found.');
}
$user->data = array_merge($user->data, $owner, ['is_registered' => true]);
$auth->acl($user->data);
$user->setup();

$welcomeMessage = <<<'TEXT'
[b]Começando por mim:[/b]

Sou o Ronassic, administrador por aqui e entusiasta de longa data do D&D 3.5. Costumo alternar entre o escudo do mestre e a ficha de jogador, mas passo boa parte do tempo mergulhado nos livros de regras, testando interações mecânicas, builds e trocando ideias sobre narração.

A ideia deste fórum surgiu quando trouxemos o D&D Tools de volta. O pessoal do nosso grupo do WhatsApp se empolgou bastante, fomos adicionando mais recursos ao projeto e criar este espaço acabou sendo um movimento natural.

A proposta é que os dois ambientes se complementem: o [b]grupo do WhatsApp[/b] continua sendo o lugar ideal para o papo do dia a dia e para tirar dúvidas rápidas; já o [b]fórum[/b] é voltado para discussões mais aprofundadas, análises de regras, builds, relatos de mesa e tudo aquilo que vale a pena deixar organizado e fácil de pesquisar meses ou anos depois, sem se perder no fluxo do chat.

Seja bem-vindo(a)! Agora é a sua vez: há quanto tempo joga e o que mais curte no sistema?

[url=https://chat.whatsapp.com/EYOrv7ZcCWVHEw6CTPFHBe]Entre no nosso grupo de D&D 3.5 no WhatsApp[/url].
TEXT;

$signature = <<<'TEXT'
[b]Ronassic[/b] · 37 anos de RPG · ex-administrador do SpellBrasil
[url=https://dndtools.quest/]D&D Tools[/url] · [url=https://chat.whatsapp.com/EYOrv7ZcCWVHEw6CTPFHBe]Comunidade D&D 3.5 no WhatsApp[/url]
TEXT;

$topics = [
    ['Comece aqui', 'Apresentações e ajuda', 'Bem-vindo ao fórum D&D Tools', $welcomeMessage],
    ['Regras e fontes', 'Dúvidas de regras', 'Como formular uma dúvida de regras', "Ao abrir uma dúvida, informe: (1) a edição, (2) o livro e a página, (3) a situação concreta na mesa, (4) sua interpretação e (5) o ponto exato que precisa de resposta.\n\nSe a dúvida envolver uma magia, talento ou monstro que está no catálogo, você pode incluir o link dessa página. Diferencie texto da regra, interpretação e regra da casa. Responda no tópico existente quando o mesmo assunto voltar; assim a discussão acumula histórico útil."],
    ['Regras e fontes', 'Correções do catálogo', 'Como sugerir uma correção do catálogo', "Encontrou um erro em uma página do catálogo, como a de uma magia, talento, monstro ou livro? Abra um tópico com o link dessa página e conte o que está errado e como você acha que deveria ficar. Se souber, cite o livro e a página para facilitar a conferência; se não souber, descreva o problema assim mesmo.\n\nSe já houver uma discussão sobre o mesmo erro, responda nela. Este espaço serve para verificar a correção juntos. A mudança no catálogo passa pela revisão editorial antes de aparecer para todos. Evite reproduzir páginas inteiras dos livros."],
    ['Personagens e opções', 'Classes e builds', 'Como pedir ajuda para uma build', "Para receber respostas úteis, informe sistema e edição, nível atual e final, livros permitidos, objetivo do personagem, atributos e restrições da mesa. Diga se busca eficiência, tema ou equilíbrio entre os dois.\n\nUse um tópico por personagem ou conceito. Quando testar uma sugestão, volte ao tópico para contar o resultado e registrar a conclusão para quem vier depois."],
    ['Personagens e opções', 'Magias e talentos', 'Como discutir uma magia ou um talento', "Abra o tópico com o nome exato da magia ou do talento. Se ela estiver no D&D Tools, inclua o link da página no catálogo. Informe livro, edição e página; se houver versões 3.0 e 3.5, diga qual a mesa usa.\n\nDescreva o personagem ou a situação concreta: nível, classe, atributos, talentos já escolhidos, alvo e momento da ação. Separe o que está escrito na fonte da sua interpretação. Para uma interação entre duas regras, cite as duas fontes e explique qual resultado está em dúvida.\n\nExemplo de pergunta útil: 'Meu personagem já escolheu o talento X, mas ficou sem um pré-requisito. Quais efeitos isso tem nesta edição?' Uma pergunta assim permite respostas com referência verificável, sem transcrever páginas inteiras. Quando a mesa decidir, registre a solução no mesmo tópico."],
    ['Bestiário e mesas', 'Monstros e templates', 'Discutindo monstros e templates', "Identifique o monstro ou template, a edição e o livro. Explique se sua dúvida é sobre aplicação de regras, ajuste de encontro, interpretação ou fonte.\n\nAo propor uma combinação, detalhe criatura base, modificadores e nível de desafio esperado. Se houver uma página desse monstro ou template no catálogo, compartilhe o link para manter a conversa ligada às regras."],
    ['Bestiário e mesas', 'Campanhas e encontros', 'Como compartilhar um encontro', "Este tópico é só um guia. Para contar uma ideia de cena, combate ou armadilha, abra um tópico novo nesta seção com um título que mostre a proposta — por exemplo, 'Emboscada de yuan-ti num templo em ruínas'.\n\nConte o que torna a ideia interessante: nível aproximado do grupo, criaturas ou obstáculos, cenário e gancho. Se já jogou, diga como foi e o que mudaria. Não precisa preencher formulário nem ter tudo pronto.\n\nSe mencionar uma criatura que está no catálogo, pode incluir o link da página para quem quiser consultar as regras. Se a dúvida principal for sobre como uma regra funciona, use a seção Dúvidas de regras.\n\nQuando alguém testar sua ideia, pode responder no tópico dela. Assim as variações e experiências ficam juntas e fáceis de encontrar depois."],
    ['Comunidade e eventos', 'Encontre uma mesa', 'Procurando mesa ou jogadores?', "Abra um tópico novo com um título que diga se você procura mesa, jogadores ou mestre. Conte se a mesa é online ou presencial, sua cidade ou fuso horário, dias disponíveis e o estilo de jogo que procura.\n\nQuando encontrar o grupo, atualize o tópico para ninguém ficar esperando resposta. Combine dados de contato por mensagem privada, sem publicar telefone pessoal."],
    ['Comunidade e eventos', 'Eventos de RPG', 'Divulgue seu evento de RPG', "Tem um encontro, convenção ou atividade de RPG para compartilhar? Abra um tópico novo com o nome do evento, data, cidade ou link da transmissão, programação e endereço oficial para inscrição.\n\nSe mudar o horário ou a inscrição, atualize o tópico. Depois do evento, volte para contar como foi!"],
];

$previousTitles = ['Como compartilhar um encontro' => 'Como registrar um encontro para reutilizar depois'];
$refreshTitles = [
    'Bem-vindo ao fórum D&D Tools',
    'Como formular uma dúvida de regras',
    'Como sugerir uma correção do catálogo',
    'Como discutir uma magia ou um talento',
    'Discutindo monstros e templates',
    'Como compartilhar um encontro',
];

foreach ($topics as [$category, $forum_name, $title, $message])
{
    $result = $db->sql_query("SELECT child.forum_id FROM " . FORUMS_TABLE . " child JOIN " . FORUMS_TABLE . " parent ON child.parent_id = parent.forum_id WHERE child.forum_name = '" . $db->sql_escape($forum_name) . "' AND parent.forum_name = '" . $db->sql_escape($category) . "'");
    $forum_id = (int) $db->sql_fetchfield('forum_id');
    $db->sql_freeresult($result);
    if (!$forum_id)
    {
        throw new RuntimeException('Missing forum ' . $category . ' / ' . $forum_name);
    }
    $lookupTitle = $title;
    $sql = "SELECT topic_id FROM " . TOPICS_TABLE . " WHERE forum_id = " . (int) $forum_id . " AND topic_title = '" . $db->sql_escape($lookupTitle) . "'";
    $result = $db->sql_query($sql);
    $existing = $db->sql_fetchfield('topic_id');
    $db->sql_freeresult($result);
    if (!$existing && isset($previousTitles[$title]))
    {
        $lookupTitle = $previousTitles[$title];
        $sql = "SELECT topic_id FROM " . TOPICS_TABLE . " WHERE forum_id = " . (int) $forum_id . " AND topic_title = '" . $db->sql_escape($lookupTitle) . "'";
        $result = $db->sql_query($sql);
        $existing = $db->sql_fetchfield('topic_id');
        $db->sql_freeresult($result);
    }
    if ($existing && !in_array($title, $refreshTitles, true))
    {
        echo $title . ": already present\n";
        continue;
    }
    $result = $db->sql_query('SELECT forum_name, forum_parents FROM ' . FORUMS_TABLE . ' WHERE forum_id = ' . (int) $forum_id);
    $forum = $db->sql_fetchrow($result);
    $db->sql_freeresult($result);
    if (!$forum)
    {
        throw new RuntimeException('Missing forum ' . $forum_id);
    }
    $uid = $bitfield = '';
    $flags = 7;
    generate_text_for_storage($message, $uid, $bitfield, $flags, true, true, true);
    $poll = [];
    $data = [
        'topic_title' => $title, 'topic_time_limit' => 0, 'post_id' => 0,
        'topic_id' => 0, 'forum_id' => $forum_id, 'icon_id' => 0,
        'poster_id' => (int) $owner['user_id'], 'enable_sig' => true,
        'enable_bbcode' => true, 'enable_smilies' => true, 'enable_urls' => true,
        'enable_indexing' => true, 'message_md5' => md5($message),
        'forum_parents' => $forum['forum_parents'], 'forum_name' => $forum['forum_name'],
        'notify' => false, 'notify_set' => false, 'poster_ip' => '127.0.0.1',
        'post_edit_locked' => 0, 'bbcode_bitfield' => $bitfield,
        'bbcode_uid' => $uid, 'message' => $message,
        'attachment_data' => [], 'filename_data' => [],
        'topic_status' => ITEM_UNLOCKED, 'force_approved_state' => ITEM_APPROVED,
    ];
    if ($existing)
    {
        $result = $db->sql_query('SELECT p.*, t.topic_title, t.topic_type, t.topic_status, t.topic_visibility, t.topic_first_post_id, t.topic_last_post_id, t.topic_posts_approved, t.topic_posts_unapproved, t.topic_posts_softdeleted, t.topic_attachment FROM ' . POSTS_TABLE . ' p JOIN ' . TOPICS_TABLE . ' t ON t.topic_id = p.topic_id WHERE p.topic_id = ' . (int) $existing . ' AND p.post_id = t.topic_first_post_id');
        $post = $db->sql_fetchrow($result);
        $db->sql_freeresult($result);
        if (!$post || (int) $post['poster_id'] !== (int) $owner['user_id'])
        {
            throw new RuntimeException('Guide post does not belong to Ronassic.');
        }
        if ($post['post_checksum'] !== md5($message) || !$post['enable_sig'] || $post['topic_title'] !== $title)
        {
            $data = array_merge($data, [
                'post_id' => (int) $post['post_id'], 'topic_id' => (int) $existing,
                'topic_title' => $title, 'topic_first_post_id' => (int) $post['topic_first_post_id'],
                'topic_last_post_id' => (int) $post['topic_last_post_id'],
                'topic_posts_approved' => (int) $post['topic_posts_approved'],
                'topic_posts_unapproved' => (int) $post['topic_posts_unapproved'],
                'topic_posts_softdeleted' => (int) $post['topic_posts_softdeleted'],
                'topic_attachment' => (int) $post['topic_attachment'],
                'topic_status' => (int) $post['topic_status'],
                'topic_visibility' => (int) $post['topic_visibility'],
                'post_visibility' => (int) $post['post_visibility'],
                'poster_ip' => $post['poster_ip'],
                'post_edit_reason' => '', 'post_edit_user' => (int) $owner['user_id'],
            ]);
            submit_post('edit', $title, '', (int) $post['topic_type'], $poll, $data);
            echo $title . ": updated\n";
        }
        else
        {
            echo $title . ": already current\n";
        }
        continue;
    }
    submit_post('post', $title, '', POST_STICKY, $poll, $data);
    echo $title . ": created\n";
}

$uid = $bitfield = '';
$flags = 7;
generate_text_for_storage($signature, $uid, $bitfield, $flags, true, true, false, false, false, false, true, 'sig');
$db->sql_query('UPDATE ' . USERS_TABLE . " SET user_sig = '" . $db->sql_escape($signature) . "', user_sig_bbcode_uid = '" . $db->sql_escape($uid) . "', user_sig_bbcode_bitfield = '" . $db->sql_escape($bitfield) . "' WHERE user_id = " . (int) $owner['user_id']);
$titles = array_map(function ($topic) use ($db) { return "'" . $db->sql_escape($topic[2]) . "'"; }, $topics);
$db->sql_query('UPDATE ' . POSTS_TABLE . ' SET enable_sig = 1 WHERE poster_id = ' . (int) $owner['user_id'] . ' AND post_id IN (SELECT topic_first_post_id FROM ' . TOPICS_TABLE . ' WHERE topic_title IN (' . implode(',', $titles) . '))');
echo "Ronassic signature updated.\n";
