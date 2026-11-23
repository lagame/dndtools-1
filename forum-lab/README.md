# Fórum do D&D Tools

O fórum usa phpBB 3.3.19 e Ajax LiteChat 2.1.0 junto ao catálogo. O código e os pacotes públicos ficam no repositório; banco, configuração, senhas, anexos e backups ficam fora do Git. Em produção, o fórum fica em <https://dndtools.quest/forum/>.

## Abrir e usar

- Fórum integrado: <http://127.0.0.1:18766/forum/>. Use este endereço para que links, idioma, tema e recursos estáticos compartilhem a mesma origem do catálogo.
- Catálogo: <http://127.0.0.1:18766/>.
- Caixa de e-mail de teste: <http://127.0.0.1:18025/>. O Mailpit captura e-mails apenas neste laboratório; nenhuma mensagem é entregue a endereços reais.
- O proprietário entra no fórum como `Ronassic`, com a senha que definiu localmente. A senha não está no repositório.
- Uma pessoa nova clica em **Registrar**, aceita os termos, preenche nome, e-mail e senha, resolve o código de confirmação e abre a mensagem de ativação no Mailpit. Depois faz login no fórum. **Redefinir senha** fica na tela de login e também envia um link ao Mailpit.
- Visitantes podem ler os tópicos. O chat exige uma conta ativa. Conversas que precisam continuar consultáveis devem virar tópicos: o chat elimina mensagens antigas após o prazo configurado.
- Visitantes não podem criar tópicos, responder ou enviar mensagens no chat. Novas contas precisam ativar o e-mail; depois disso podem conversar no chat, com intervalo mínimo de 15 segundos entre mensagens. Seus três primeiros posts no fórum passam por moderação. Essas barreiras reduzem spam, mas não garantem bloquear todo bot com IA.
- As regras da comunidade ficam em um tópico fixo em **Comece aqui → Apresentações e ajuda**. O deploy cria o tópico uma vez, assinado por Ronassic; alterações posteriores podem ser feitas pelo próprio fórum.
- Avatares aceitam arquivos GIF, JPEG, PNG, WebP e AVIF de até **512 KiB**. O upload é decodificado, reduzido proporcionalmente para caber em **300 × 300 px** e regravado como WebP sem metadados nem bytes originais anexados. Animações viram imagem estática. A imagem aparece nos posts com no máximo 128 px de lado. A regravação reduz a superfície de ataque dos arquivos servidos, mas não substitui atualização do PHP e das bibliotecas de imagem.
- No primeiro acesso, o fórum gera e guarda uma miniatura WebP de **64 × 64 px** para o chat, o topo e a lista de membros. A página de avatar continua oferecendo a imagem original regravada. Uma troca de avatar usa o novo identificador de versão e gera outra miniatura automaticamente.
- Os botões EN/PT-BR trocam a interface do fórum e do catálogo. A preferência de idioma alterada no painel do usuário do phpBB também se reflete no catálogo. O seletor de tema usa a mesma preferência do navegador nos dois. Textos publicados por membros continuam no idioma em que foram escritos.

## Discussões ligadas às fichas

Nas fichas de magias, talentos, monstros, templates, livros e demais registros do catálogo, a seção **Discutir este registro** mostra os tópicos do phpBB ligados àquela ficha. Uma conta ativa pode abrir uma pergunta, discussão ou sugestão de correção usando o editor, a moderação e as permissões nativas do fórum. Os tópicos ficam no fórum correspondente e têm um link de volta à ficha. Variantes de classes e perícias por livro têm discussões próprias, separadas da ficha principal.

O catálogo fornece ao fórum apenas nome e caminho de **um registro por requisição** em `/forum-record/<tipo>/<id>/`. O phpBB mantém os tópicos, respostas, contas e notificações; o vínculo entre tópico e ficha fica na tabela da extensão `dndtools/discussions`. O proprietário recebe e-mail do phpBB quando outra pessoa abre um tópico ligado a uma ficha ou responde nele. No laboratório, o Mailpit captura esse aviso. A seção usa a origem compartilhada em `127.0.0.1:18766`; o endereço direto da aplicação em `127.0.0.1:8765` não serve o fórum.

Após inicializar um laboratório novo e fazer backup do banco do fórum, habilite a extensão com `docker exec -u www-data dndtools-forum_lab-1 php bin/phpbbcli.php extension:enable dndtools/discussions`. O script de categorias `forum-lab/seed-forums.php` cria a área **Livros, itens e referências** caso ainda não exista. Para conferir o fluxo no laboratório existente, rode `python forum-lab/tests/smoke_discussions.py`: ele cria uma conta e um tópico temporários, verifica editor, ligação e mobile, e remove ambos ao final. Esta integração está em avaliação **somente local**; a ativação da extensão e o teste de publicação em produção ficam para uma etapa separada.

## Rodar e conferir

No PowerShell, na raiz do projeto:

```powershell
docker compose -f compose.yaml -f compose.forum.local.yaml up -d --build
$env:DND_QA_OUTPUT = Join-Path $env:LOCALAPPDATA 'dndtools\qa'
python forum-lab/tests/check_chat_translation.py
python forum-lab/tests/smoke_visual.py
python forum-lab/tests/smoke_chat.py
python forum-lab/tests/smoke_avatar.py
python forum-lab/tests/smoke_discussions.py
docker cp forum-lab/tests/check_forum_config.php dndtools-forum_lab-1:/tmp/dndtools-check-forum-config.php
docker exec -e DND_FORUM_LAB=1 dndtools-forum_lab-1 php /tmp/dndtools-check-forum-config.php
```

O volume `dndtools_forum_lab_data` contém o banco e a configuração desta instalação. O comando acima reinicia uma instalação **já inicializada**; não instala um fórum vazio automaticamente. Os scripts de categorias e tópicos exigem `DND_FORUM_LAB=1` e só podem ser usados após conferência dos dados locais. Antes de instalar o chat, foi salvo um backup privado em `%LOCALAPPDATA%\dndtools\forum-backups\20261122-before-litechat`.

O Dockerfile verifica o SHA-256 do ZIP do LiteChat (`22e4af7c297b256a6caf56127b18203be5b5e03f944d87b4efa0c52e75182503`) e do pacote de idioma. Esse hash fixa o arquivo recebido para builds repetíveis; não é uma assinatura independente do autor. A pequena correção em `patches/litechat-base-path.patch` adapta o avatar padrão ao caminho `/forum/`.

Depois de inicializar um laboratório novo, aplique uma vez os limites de avatar com `docker cp forum-lab/configure-avatar.php dndtools-forum_lab-1:/tmp/dndtools-configure-avatar.php` e `docker exec -e DND_FORUM_LAB=1 -u www-data dndtools-forum_lab-1 php /tmp/dndtools-configure-avatar.php`. Não execute isso a cada inicialização: ajustes posteriores feitos no ACP devem ser preservados.

Após instalar o LiteChat em um laboratório novo, habilite o chat para contas ativadas com `docker cp forum-lab/configure-chat.php dndtools-forum_lab-1:/tmp/dndtools-configure-chat.php` e `docker exec -e DND_FORUM_LAB=1 -u www-data dndtools-forum_lab-1 php /tmp/dndtools-configure-chat.php`. O script preserva a moderação inicial e pode ser repetido. Antes de qualquer alteração no banco, salve e verifique um backup privado. Em produção, o workflow executa esse ajuste automaticamente.

## Atualizar a produção

O banco local foi importado uma vez por transferência privada após revisão dos endereços. **Atualizações normais não copiam o banco local novamente.** Faça commit do código no `master` do fork e execute o workflow **Deploy D&D Tools to VPS** no GitHub Actions. Pela CLI:

```powershell
gh workflow run deploy-vps.yml --repo lagame/dndtools-1 --ref master
```

O workflow conecta ao VPS, verifica um backup do MySQL e cria outro do banco e arquivos do fórum em `/var/backups/dndtools/` antes de atualizar os containers. O SMTP, o banco e o `config.php` do phpBB permanecem privados no VPS. Confira o resultado do workflow e abra a página do fórum depois do deploy. A conta do fórum é independente do acesso editorial do Django; não há login único.

A ativação por e-mail, a moderação inicial e o bloqueio de postagens anônimas estão ativos. Revise periodicamente a fila de moderação, os relatos dos usuários e os logs. Regras adicionais de desafio ou limitação de requisições no Cloudflare para cadastro e login podem reduzir automação sem bloquear a leitura pública.
