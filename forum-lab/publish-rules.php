<?php
// Add the forum rules once, after a verified forum backup.
if (PHP_SAPI !== 'cli' || (getenv('DND_FORUM_LAB') !== '1' && getenv('DND_FORUM_PRODUCTION') !== '1'))
{
    fwrite(STDERR, "Forum container only.\n");
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
if (!$owner || (int) $owner['user_type'] !== USER_FOUNDER)
{
    throw new RuntimeException('Founder Ronassic was not found.');
}

$result = $db->sql_query("SELECT child.* FROM " . FORUMS_TABLE . " child JOIN " . FORUMS_TABLE
    . " parent ON child.parent_id = parent.forum_id WHERE child.forum_name = 'Apresentações e ajuda'"
    . " AND parent.forum_name = 'Comece aqui'");
$forum = $db->sql_fetchrow($result);
$db->sql_freeresult($result);
if (!$forum)
{
    throw new RuntimeException('Starter forum was not found.');
}

$title = 'Regras do fórum D&D Tools';
$result = $db->sql_query('SELECT topic_id FROM ' . TOPICS_TABLE . ' WHERE forum_id = '
    . (int) $forum['forum_id'] . " AND topic_title = '" . $db->sql_escape($title) . "'");
$existing = $db->sql_fetchfield('topic_id');
$db->sql_freeresult($result);
if ($existing)
{
    echo "Forum rules already exist: topic $existing.\n";
    exit(0);
}

$message = <<<'TEXT'
[b]Bem-vindo ao fórum D&D Tools![/b]

Este espaço guarda conversas sobre D&D 3.5 e RPG para que possam ser encontradas e retomadas no futuro. As regras abaixo valem para tópicos, respostas, chat, mensagens privadas, assinaturas, avatares e perfis.

[b]1. Respeite as pessoas[/b]
Discorde de ideias e interpretações, não ataque quem as escreveu. Não são permitidos assédio, discriminação, ameaças, perseguição, humilhação, provocações repetidas ou divulgação de dados pessoais de outra pessoa.

[b]2. Mantenha a conversa ligada ao RPG[/b]
Fale de regras, cenários, personagens, livros, mesas e da comunidade. Não publique conteúdo sexual explícito. Política partidária, proselitismo religioso e disputas políticas, sociais ou ideológicas do mundo real não são o foco deste fórum. Assuntos sem relação com RPG devem ficar fora das seções de discussão; uma conversa privada também deve respeitar estas regras.

[b]3. Temas sensíveis dependem do contexto[/b]
É possível analisar criticamente uma obra, cenário, personagem, editora, autor ou decisão editorial, inclusive quando a análise tocar questões sociais ou políticas. Mantenha o assunto na obra e no RPG. Mencionar uma raça, classe ou campanha não dá passe livre para atacar grupos reais nem para transformar o tópico em guerra cultural. A moderação considerará o contexto e a continuidade da conversa.

[b]4. Organize o assunto para que outras pessoas o encontrem[/b]
Escolha a seção adequada e dê ao tópico um título que descreva a dúvida ou proposta. Pesquise antes de abrir outro tópico. Se o assunto voltar meses depois, responda no tópico antigo com a informação nova. Evite mensagens repetidas e mudanças bruscas de assunto dentro de um tópico. Para buscar mesa e divulgar eventos, use as áreas próprias.

[b]5. Separe regra, fonte e interpretação[/b]
Em dúvidas de regras, cite livro, edição e página quando souber. Se houver uma ficha no catálogo, inclua o link para ela. Diga qual é o texto da regra, qual é sua interpretação e se a mesa usa alguma regra da casa. Discordâncias são bem-vindas quando ajudam a esclarecer a questão.

[b]6. Cuide dos spoilers e dos direitos de terceiros[/b]
Avise no título ou use a marcação de spoiler para segredos de aventuras e campanhas. Não publique livros digitalizados, páginas inteiras transcritas, arquivos protegidos ou material pessoal de outra pessoa sem permissão. Resumos próprios, referências pontuais e links autorizados ajudam mais a discussão.

[b]7. Sem spam ou autopromoção disfarçada[/b]
Divulgação de projetos, produtos, serviços, canais, links de afiliado e pedidos de curtidas ou votos precisam de autorização da moderação. Eventos de RPG podem ser anunciados na seção própria com data, local e link oficial. Não use mensagens privadas ou o chat para publicidade em massa.

[b]8. Use sua conta com responsabilidade[/b]
Não se passe por outra pessoa nem compartilhe acesso à conta. Publicações anônimas não são permitidas. Proteja suas informações e combine telefone, endereço ou outros dados de contato por canais privados, quando necessário.

[b]9. Ajude a moderação[/b]
Use o botão de denúncia para avisar sobre conteúdo problemático; não transforme a denúncia em briga pública. A equipe pode orientar, editar, mover, ocultar ou remover mensagens e bloquear contas conforme a gravidade e a reincidência. Se discordar de uma decisão, entre em contato com a moderação por mensagem privada.

Estas regras servem para manter um espaço acolhedor e útil. Vale a pena reler o tópico de tempos em tempos: avisaremos aqui quando houver mudanças relevantes.
TEXT;

$user->data = array_merge($user->data, $owner, ['is_registered' => true]);
$auth->acl($user->data);
$user->setup();
$uid = $bitfield = '';
$flags = 7;
generate_text_for_storage($message, $uid, $bitfield, $flags, true, true, true);
$data = [
    'topic_title' => $title, 'topic_time_limit' => 0, 'post_id' => 0,
    'topic_id' => 0, 'forum_id' => (int) $forum['forum_id'], 'icon_id' => 0,
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
$poll = [];
submit_post('post', $title, '', POST_STICKY, $poll, $data);
echo "Forum rules created as a sticky topic.\n";
