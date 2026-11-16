# D&D Tools

A community fork of the original D&D Tools catalog, modernized for Python 3.14, Django 5.2 and MySQL 8.4. The public pages keep the original catalog URLs and now use a responsive layout and first-party search. The source code is MIT licensed; rights to individual book content must be assessed separately.

The site is available at [dndtools.quest](https://dndtools.quest/). It uses the HeroForge visual family with a self-hosted Inter font. `/privacy/` explains the site's technical cookies, the browser preference used to dismiss the notice, and how to contact the maintainer. No optional advertising or analytics cookies are active, so the notice is informational; adding such services requires a real choice before they run.

**The database is not in this repository.** To request the private SQLite snapshot, [open an issue](https://github.com/lagame/dndtools-1/issues). We will arrange a private transfer. Never attach the database, a dump, or source scans to an issue or commit.

## Local setup (Windows PowerShell)

Install Git, Python 3 and Docker Desktop. From PowerShell:

```powershell
git clone https://github.com/lagame/dndtools-1.git
cd dndtools-1
py -3 scripts\setup_local.py
docker compose up -d --wait db
docker compose build app
docker compose run --rm app python manage.py migrate --noinput
```

If you have the private SQLite snapshot, import it into the empty MySQL catalog. Use the repaired workspace snapshot distributed privately, rather than the older original file:

```powershell
$privateDb = (Resolve-Path 'C:\path\to\dnd.sqlite').Path
docker compose run --rm --volume "${privateDb}:/private/dnd.sqlite:ro" app python manage.py import_legacy_sqlite --source /private/dnd.sqlite
docker compose run --rm --volume "${privateDb}:/private/dnd.sqlite:ro" app python manage.py import_legacy_sqlite --source /private/dnd.sqlite --apply
docker compose run --rm --volume "${privateDb}:/private/dnd.sqlite:ro" app python manage.py import_legacy_sqlite --source /private/dnd.sqlite --verify
```

The import reads the SQLite file without modifying it, requires an empty MySQL catalog and verifies every content field after writing. It does not import the unrelated HeroForge table. The project also starts without the private data, with an empty catalog.

```powershell
docker compose up -d app
```

Open <http://127.0.0.1:8765/>. For editorial access, create your own administrator after starting the app:

```powershell
docker compose exec app python manage.py createsuperuser
```

Enter the username, email and a unique password of at least 14 characters at the private terminal prompt, then open <http://127.0.0.1:8765/admin/login/>. No default administrator exists. The generated `.env`, original SQLite, MySQL volume, uploads and backups stay private and out of Git.

## Configuração local em português (Windows)

Você precisa de Git, Python 3 e Docker Desktop. O MySQL roda no Docker, então não precisa instalá-lo separadamente no Windows.

```powershell
git clone https://github.com/lagame/dndtools-1.git
cd dndtools-1
py -3 scripts\setup_local.py
docker compose up -d --wait db
docker compose build app
docker compose run --rm app python manage.py migrate --noinput
```

O comando `setup_local.py` cria um `.env` privado com senhas aleatórias. Se você não tiver o banco, o site abre com o catálogo vazio. Para receber a cópia privada, [abra uma Issue neste fork](https://github.com/lagame/dndtools-1/issues); combinaremos o envio por outro canal. **Não publique o arquivo na Issue ou no GitHub.**

Depois que receber o `dnd.sqlite`:

```powershell
$privateDb = (Resolve-Path 'C:\caminho\para\dnd.sqlite').Path
docker compose run --rm --volume "${privateDb}:/private/dnd.sqlite:ro" app python manage.py import_legacy_sqlite --source /private/dnd.sqlite
docker compose run --rm --volume "${privateDb}:/private/dnd.sqlite:ro" app python manage.py import_legacy_sqlite --source /private/dnd.sqlite --apply
docker compose run --rm --volume "${privateDb}:/private/dnd.sqlite:ro" app python manage.py import_legacy_sqlite --source /private/dnd.sqlite --verify
docker compose up -d app
```

Abra <http://127.0.0.1:8765/>. A primeira importação pode levar alguns minutos. A opção sem `--apply` apenas confere; `--verify` compara o MySQL com o arquivo recebido antes da curadoria, que altera intencionalmente descrições e capas. Se o banco já contém registros, o importador recusa uma segunda carga.

As capas dos livros e as ilustrações das raças também não são distribuídas pelo GitHub. Numa instalação nova, depois de importar o banco, restaure as 81 imagens referenciadas pelo banco e as 45 capas adicionais identificadas no arquivo público antigo e em outras fontes conferidas. Copie-as para o volume privado do Docker:

```powershell
py -3 scripts\restore_catalog_media.py --sqlite $privateDb --covers-file dndtools\dnd\legacy_rulebook_covers.json
docker compose cp dndtools/static/media/rulebook app:/var/www/media/rulebook
docker compose cp dndtools/static/media/race app:/var/www/media/race
docker compose run --rm volume_permissions
docker compose run --rm app python manage.py curate_rulebooks
docker compose run --rm app python manage.py curate_rulebooks --apply
```

O script valida os formatos e gera um manifesto SHA-256 local. O comando de curadoria só altera os 114 livros antigos quando seus IDs e títulos correspondem ao catálogo recuperado; faça um backup privado antes de executá-lo em um banco já utilizado. A fonte online `Web` não possui capa e é exibida sem espaço reservado para imagem. Confira o [relatório da recuperação](docs/media-restoration-2026-11-16.md) para as fontes e os nomes que precisaram de ajuste.

Para entrar na administração, crie sua própria conta local após iniciar o aplicativo:

```powershell
docker compose exec app python manage.py createsuperuser
```

Informe usuário, e-mail e uma senha exclusiva de pelo menos 14 caracteres no terminal. Depois abra <http://127.0.0.1:8765/admin/login/>. O projeto não fornece login ou senha padrão. Se você bloquear a própria conta após cinco tentativas erradas, espere 15 minutos; quem tem acesso ao servidor pode usar `docker compose exec app python manage.py axes_reset_username NOME_DO_USUARIO` para liberar apenas essa conta. A proteção usa o MySQL compartilhado pelos processos da aplicação.

A fonte Inter é servida pelo próprio projeto e sua licença OFL está em `dndtools/static/fonts/LICENSE-Inter.txt`. Após publicar esta branch, a página `/privacy/?lang=pt` informará os dados técnicos tratados, o contato do responsável e a duração do armazenamento no navegador.

O seletor **Theme** no cabeçalho oferece cinco visuais responsivos: **Standard** (roxo, inspirado no HeroForge), **Modern** (azul e dourado do projeto), **Simple** (branco, preto e links azuis), **Petroleo** (azul profundo com texto claro e detalhes dourados) e **Dark** (preto puro, superfícies neutras e botões dourados). A escolha fica apenas no `localStorage` deste navegador, sem conta ou cookie adicional, e permanece depois que você o fecha. Quem já usava o antigo Dark continua no mesmo visual, agora chamado Petroleo. No Simple, as próximas páginas não pedem o CSS roxo, a fonte Inter, o favicon nem as imagens de capa e raça; estas são substituídas por texto. A página HTML, os estilos básicos e os scripts necessários à navegação e busca continuam carregando. O pequeno pergaminho de Oghma, fixo perto da borda inferior, abre as ferramentas editoriais do Django; o acesso continua protegido por autenticação.

### Idiomas e colaboração editorial

O catálogo original em inglês permanece nas URLs atuais. O seletor **Language** abre a mesma página em `/pt-br/` e lembra a escolha por até um ano no cookie funcional `django_language`. Sem escolha anterior, a página inicial usa o idioma preferido do navegador. A interface pública tem mensagens em inglês e português; os dados de cada registro permanecem em inglês até que uma tradução integral seja proposta e aprovada. Nesse intervalo, a página em português informa que o conteúdo ainda está no idioma original. Os títulos traduzidos mostram também o nome em inglês, e a pesquisa aceita termos nos dois idiomas para registros com tradução aprovada. O texto da [política de privacidade](dndtools/templates/dnd/privacy.html) descreve essa preferência e os dados editoriais.

Depois de entrar no Admin, abra **Editorial workspace**. O proprietário pode convidar colaboradores por e-mail e conceder, por tipo de registro, permissão para propor inclusão, correção, tradução e remoção. Convites geram código de uso único com validade de sete dias, apresentado apenas uma vez; entregue-o por um canal privado. O colaborador ativa a conta após passar pelo Cloudflare Access e definir senha. Uma proposta só altera o catálogo quando Ronassic a aprova; a fila exibe a quantidade pendente. A inclusão, edição e exclusão diretas pelo Django Admin ficam restritas ao proprietário, mesmo se alguém conceder permissões Django de modelo a um colaborador por engano; permissões de leitura continuam funcionando. A referência editorial é obrigatória; informe a página do livro quando aplicável. Novos registros vinculados a uma edição ou livro precisam ser D&D 3.5 confirmados. O proprietário deve conferir a fonte antes de aprovar, especialmente nos tipos sem vínculo direto com livro. Não copie textos protegidos sem revisar os direitos de publicação.

O espaço editorial cobre os modelos recuperados de livros, regras, classes, talentos, magias, raças, monstros, itens e seus vínculos. Há cadastro novo para **templates de criaturas** e para seis tipos antes ausentes: **mistérios de magia das sombras, invocações, poderes psiônicos, auras, manobras e traços monstruosos**. Eles têm listagem, pesquisa, formulário de proposta e página pública após aprovação. O proprietário pode conceder acesso a cada um dos seis tipos separadamente ou a todos. Traços, defeitos e truques de perícia usam categorias de talentos; itens mundanos e alquímicos usam o tipo `MUN` do cadastro de itens. O antigo menu **My D&D** continua planejado porque é uma área pessoal, não um tipo de registro editorial. Colaboradores podem propor remoções quando receberem essa permissão; o registro permanece público até a aprovação do proprietário. A aprovação recusa apagar registros que tenham vínculos dependentes, para evitar perda de conteúdo em cascata. Resolva esses vínculos antes de reenviar a proposta.

Para receber um e-mail a cada proposta, configure **somente no `.env` privado** `DND_EDITORIAL_NOTIFY_EMAIL`, `DND_EMAIL_HOST`, `DND_EMAIL_PORT`, `DND_EMAIL_USER`, `DND_EMAIL_PASSWORD`, `DND_EMAIL_FROM` e `DND_EMAIL_USE_TLS`. Os três valores de destino, servidor e remetente são obrigatórios em produção; se usar Gmail, o usuário e a senha de aplicativo também são obrigatórios. A atualização recusa prosseguir se estiverem ausentes. Teste a entrega antes de convidar pessoas; caso o SMTP falhe, a proposta continua na fila e o colaborador recebe um aviso. Nenhuma credencial deve entrar no Git. Em produção, configure `DND_ACCESS_TEAM_DOMAIN` e `DND_ACCESS_AUD` (uma ou mais tags separadas por vírgula, se os dois hosts usarem aplicações distintas). O Django valida a assinatura, o emissor, a audiência e o vencimento do JWT do Access, além de vincular a sessão ao e-mail autenticado. O Admin precisa continuar protegido no Cloudflare em ambos os hosts.

Para liberar convidados na borda, crie **um grupo Access dedicado ao D&D Tools** com os e-mails exatos dos colaboradores e vincule-o a uma política Allow separada na aplicação Access que protege os dois hosts. Exija MFA nessa política e mantenha a política do proprietário. A lista desejada pode ser consultada no servidor com `docker compose -f compose.yaml -f compose.tunnel.yaml exec -T app python manage.py access_group_members`. A sincronização opcional em `scripts/sync_access_group.py` roda **no host**, com `DND_CF_ACCOUNT_ID`, `DND_CF_GROUP_ID`, `DND_CF_GROUP_NAME` e `DND_CF_API_TOKEN` em `/etc/dndtools/access-sync.env` protegido por root; use primeiro sem `--apply` para verificar a diferença. Os arquivos `scripts/systemd/dndtools-access-sync.*` permitem conferir a cada dois minutos. A API exige a permissão de conta `Access: Organizations, Identity Providers, and Groups Write`; o token não pode ser limitado a um único grupo, portanto restrinja-o à conta correta, mantenha-o apenas no host e configure prazo/IP quando viável. O script confere o ID e o nome do grupo dedicado antes de alterar seus membros. O token nunca deve entrar no container web e a política não deve conter regras amplas como Everyone. Sem a sincronização, inclua e remova os e-mails manualmente no grupo Access. A revogação desativa a conta Django imediatamente; a retirada da política Access ocorre na próxima sincronização ou edição manual do grupo. Revise a configuração da borda e teste um convite em ambos os domínios antes de publicar esta branch.

Para convidados que não são membros da conta Cloudflare, adicione **One-time PIN** em **Zero Trust → Integrações → Provedores de identidade** e habilite esse método no aplicativo Access do D&D Tools e no App Launcher. Mantenha o provedor Cloudflare existente para o proprietário; não adicione colaboradores como membros da conta administrativa. A política Allow por e-mail exato e o MFA do aplicativo continuam necessários. Na política Allow do App Launcher, inclua o e-mail do proprietário **ou** o grupo dos colaboradores; deixe o próprio App Launcher acessível antes do MFA para que cada convidado possa cadastrar seu autenticador em **Account → MFA devices**. Teste o login externo no Access antes de publicar; depois da publicação, valide a ativação do convite no Django.

### Administração em produção

Em produção (`DND_DEBUG=0`), defina `DJANGO_ADMIN_URL` no `.env` privado como um único segmento aleatório de 16 a 64 caracteres ASCII (`A-Z`, `a-z`, `0-9`, `_`, `-`), sem barras. Sem essa variável, a aplicação recusa iniciar. No desenvolvimento local (`DND_DEBUG=1`), a ausência dela mantém `/admin/`. Para uma instalação nova pelo script do túnel, o valor é gerado no `.env` privado; em instalações existentes, configure-o manualmente antes de atualizar. O ícone público de Oghma aponta para essa rota e portanto revela o caminho no HTML: ele não é um segredo nem substitui autenticação e Access.

**Antes de publicar esta branch**, ajuste no Cloudflare Zero Trust as aplicações **Access → Self-hosted** de `dndtools.quest` e `www.dndtools.quest` para cobrir `/<valor de DJANGO_ADMIN_URL>` e `/<valor de DJANGO_ADMIN_URL>/*` em ambos os hosts. A proteção atual de `/admin` não acompanha automaticamente a mudança da rota. Configure uma política **Allow** apenas para a identidade do administrador, com autenticação adicional no provedor de identidade. Em janela anônima, confirme que visitantes sem permissão não veem o login na rota nova e que os autorizados entram; confira também que o catálogo continua público. [As regras de caminho do Access](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/app-paths/) distinguem o caminho base dos subcaminhos. A aplicação continua limitando por nome de usuário e, ao receber `CF-Connecting-IP` de seu próprio proxy `tunnel_proxy` ou loopback, também por IP. Não use `X-Forwarded-For` do cliente para isso. O IP do container do proxy é resolvido dinamicamente, sem lista manual que envelheça. Consulte a [política de privacidade](dndtools/templates/dnd/privacy.html) para os dados guardados nas tentativas. A configuração e o acesso autorizado deste fork foram verificados em 15/11/2026; veja o [registro de QA do Access](docs/cloudflare-access-qa-2026-11-15.md). Cada nova instalação precisa repetir essa verificação.

O HTML do catálogo legado é sanitizado na renderização, incluindo os dados importados antes desta mudança. Tabelas, formatação e links de magias/talentos permanecem; scripts, eventos e URLs JavaScript são removidos. O cabeçalho CSP está em `Report-Only` para observar incompatibilidades sem bloquear recursos, sem coletor de relatórios configurado. A aplicação Docker roda como UID 10001; um serviço de inicialização ajusta somente a propriedade dos volumes de mídia e estáticos. Isso não modifica as portas globais, o Nginx ou os containers dos outros projetos.

Depois de publicar uma versão revisada, crie a conta na própria base de produção pelo terminal privado do VPS com `docker compose exec app python manage.py createsuperuser`. Não coloque usuário, senha, `.env`, banco ou backup no repositório ou nas Issues. Contas existentes com senhas antigas não são alteradas automaticamente; troque essas senhas pela administração assim que houver acesso.

### Cache e atualização do visual

O HTML do catálogo pede revalidação a cada visita. Os CSS e JavaScript usados pelo layout recebem automaticamente `?v=` com um resumo do conteúdo do arquivo. Quando um deles muda, a URL muda; o navegador e a Cloudflare buscam a versão nova sem depender de um *refresh* forçado ou de limpar todo o cache. Os arquivos antigos podem permanecer no cache até expirar sem afetar o HTML novo.

O cache público da Cloudflare foi observado com `CF-Cache-Status: DYNAMIC` no HTML e `HIT` no CSS; uma URL de CSS com nova versão retornou `MISS` e depois `HIT`. Essa verificação vale para a configuração atual. Se for criada uma regra de "Cache Everything" para HTML ou de ignorar parâmetros da URL, será preciso revisá-la. Arquivos privados de mídia enviados depois não recebem esse versionamento automático: para substituí-los, use um nome novo ou remova a URL antiga do cache.

Após uma atualização, confira os dois domínios, a página inicial, o `Cache-Control` do HTML e as URLs `?v=` dos CSS/JS no código da página. O fluxo de deploy já faz backup do MySQL e verifica a origem; ele não deve ser executado até a revisão visual e de privacidade ficar concluída.

Para conferir o código após alterações:

```powershell
py -3 scripts\prepare_test_db.py
docker compose run --rm app python manage.py test dnd --keepdb --noinput
docker compose run --rm app python manage.py makemigrations --check --dry-run
```

As [sete magias 3.5 revisadas](docs/reviewed-cantrips-35.md) já estão no snapshot de trabalho. Novas inclusões exigem confirmação da edição e da fonte editorial.

## Private VPS staging and activation

The Compose stack runs MySQL internally, Django/Gunicorn as the application, and Caddy as the optional HTTPS proxy. On a Linux VPS with Docker Compose, clone the fork, run `python3 scripts/setup_local.py`, and edit the private `.env`:

- For **private staging over an SSH tunnel**, set `DND_DEBUG=0`, `DND_FORCE_HTTPS=0`, `DND_ALLOWED_HOSTS=127.0.0.1,localhost`, `DND_PUBLIC_HOST=127.0.0.1:8765`, a private `DJANGO_ADMIN_URL` of 16-64 characters, and matching HTTP CSRF origins. Start `db` and `app` without the production profile. The application port binds only to VPS loopback. Connect with `ssh -L 8765:127.0.0.1:8765 user@vps` and browse locally.
- Before **public activation**, review publication rights for the catalog, point a dedicated hostname to the VPS, open ports 80/443, set `DND_DEBUG=0`, `DND_FORCE_HTTPS=1`, `DND_ALLOWED_HOSTS` and `DND_PUBLIC_HOST` to that hostname, and `DND_CSRF_TRUSTED_ORIGINS=https://hostname`. Run the production deployment check and then `docker compose --profile production up -d --build`. Caddy obtains and renews HTTPS certificates. Public activation requires the owner's decision.

For either environment, apply migrations and import the private snapshot as shown above before starting the app. Do **not** publish the MySQL port, `.env`, SQLite file, or SQL dumps. The old third-party contact form is replaced by [project Issues](https://github.com/lagame/dndtools-1/issues).

### Publicação pelo Cloudflare Tunnel existente (`dndtools.quest`)

Se o VPS já roda `cloudflared` e Docker Compose, não é preciso instalar outro painel, alterar o Nginx dos demais sites nem ocupar as portas públicas 80/443. O proxy deste projeto escuta **somente** em `127.0.0.1:8766` e serve a aplicação, CSS e arquivos de mídia. Verifique antes de começar que a porta 8766 está livre. A rota atual do túnel em `https://127.0.0.1:443` só deve ser trocada depois da verificação local.

No terminal do VPS, para uma **instalação nova**:

```bash
git clone https://github.com/lagame/dndtools-1.git /opt/dndtools && cd /opt/dndtools && bash scripts/deploy_cloudflare_tunnel.sh
```

Antes de uma instalação nova, disponibilize no shell privado as variáveis `DND_ACCESS_TEAM_DOMAIN`, `DND_ACCESS_AUD`, `DND_EDITORIAL_NOTIFY_EMAIL`, `DND_EMAIL_HOST` e `DND_EMAIL_FROM`; configure também porta, usuário e senha SMTP se o provedor exigir. O script cria `.env` com senhas aleatórias, configura os dois hosts e HTTPS, sobe MySQL, aplica as migrações e inicia aplicação e proxy. Ele recusa uma instalação já existente para evitar alterações no banco sem backup. Sem o arquivo privado, o catálogo fica vazio. Para carregar o snapshot SQLite **revisado**, transfira-o por um canal privado para o VPS **antes** da instalação e passe o caminho absoluto ao script, por exemplo `bash scripts/deploy_cloudflare_tunnel.sh /root/dnd.sqlite`. Não envie o banco ao GitHub nem por Issue. Os arquivos de mídia ausentes do repositório precisam ser transferidos separadamente, se disponíveis.

Confira no VPS `curl -I -H 'Host: dndtools.quest' http://127.0.0.1:8766/` e `curl -I http://127.0.0.1:8766/static/css/modern.css` (respostas HTTP 200). Depois, no painel **Cloudflare Zero Trust → Networks → Tunnels → túnel existente → Published applications**, edite as rotas de `dndtools.quest` e `www.dndtools.quest`: em ambas, defina **Service URL** como `http://127.0.0.1:8766`. Remova as opções de origem HTTPS/SNI que foram configuradas para `https://127.0.0.1:443`, pois esta nova origem usa HTTP apenas no loopback do VPS. Não altere as rotas dos outros domínios. O HTTPS público continua na Cloudflare; o proxy local informa o esquema externo ao Django. Antes de divulgar o site com o catálogo privado, revise os direitos de publicação desse conteúdo.

Para testar a ligação **GitHub Actions → VPS** sem publicar nada, há o workflow manual **Check VPS connection**. Ele requer os segredos do próprio fork `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY` (chave de deploy dedicada), `VPS_KNOWN_HOSTS` (chave pública do host previamente conferida) e, opcionalmente, `VPS_PORT` (padrão 22). A chave pública da chave de deploy precisa estar autorizada para esse usuário no VPS. Em **Actions → Check VPS connection → Run workflow**, uma execução bem-sucedida confirma SSH, Docker, espaço e estado das portas 8765/8766. Esse workflow não altera o VPS e não usa o banco. Os segredos do HeroForge pertencem ao outro repositório e não são compartilhados automaticamente com este fork.

Para **atualizações depois da instalação inicial**, execute manualmente **Actions → Deploy D&D Tools to VPS → Run workflow** na branch `master`. O workflow exige os mesmos segredos, recusa alterações locais no checkout do VPS e só aceita o commit atual da branch. Antes de atualizar, cria um dump MySQL em `/var/backups/dndtools` e testa sua restauração em um banco temporário. Depois atualiza apenas `/opt/dndtools`, aplica migrações e verifica a página inicial e o CSS pela porta local `8766`. Não altera as rotas do Cloudflare nem os outros projetos do VPS. Se uma migração ou a verificação final falhar, investigue antes de repetir; o backup verificado permanece disponível para recuperação manual.

O catálogo de livros permite filtrar por título, descrição, edição, tipo, ano e conteúdo catalogado. A atualização classifica os 114 livros recuperados e acrescenta resumos próprios somente aos 53 sem descrição, depois do backup verificado. As listas HTML oferecem até 5.000 itens por página. Não há API pública de exportação do catálogo: o JSON de sugestões retorna no máximo oito nomes e links por consulta, e o sitemap XML contém somente URLs. Como o catálogo é público, os registros visíveis ainda podem ser copiados das páginas individuais; paginação não é proteção contra coleta automatizada.

## Backups and verification

Before each release, save a MySQL dump **outside the repository** and test its restoration into a temporary database:

```powershell
py -3 scripts\backup_mysql.py --output-dir 'C:\Backups\dndtools'
py -3 scripts\verify_mysql_backup.py 'C:\Backups\dndtools\dndtools-mysql-YYYY-MM-DD-HHMMSS.sql.gz'
```

On Linux use `python3` and a private backup directory such as `/var/backups/dndtools`. Protect backups with restricted access and copy them to encrypted off-site storage. `verify_mysql_backup.py` creates and drops only its own temporary restore database. The SQL dump is **not encrypted by the script**. Back up `.env` and uploaded media separately in a protected location. The original SQLite snapshot should remain untouched.

See [modernization status](docs/modernization-status.md) for the verified baseline and remaining activation gates.

The [navigation and filter map](docs/navigation-and-filters.md) lists the old menu entries and their current destinations. The [image inventory](docs/image-inventory.md) and [CSV](docs/image-inventory.csv) record the 81 catalog images that were missing on 2026-11-15; the [restoration report](docs/media-restoration-2026-11-16.md) records their recovery. The binaries are not in Git. After obtaining the private SQLite snapshot, run `py -3 scripts/restore_catalog_media.py --sqlite dnd.sqlite --covers-file dndtools/dnd/legacy_rulebook_covers.json` (or `python3` on Linux) to restore 81 existing references and 45 newly matched covers locally. Transfer `dndtools/static/media/rulebook/` and `dndtools/static/media/race/` to the deployment's media volume separately. The [2026-11-15 QA report](docs/modernization-qa-2026-11-15.md) records the earlier local checks and limits.

The [identity and privacy QA report](docs/identity-privacy-qa-2026-11-15.md) records the visual checks, browser storage behavior and legal details still to confirm before publishing that branch.

The [cache and themes QA report](docs/cache-themes-qa-2026-11-15.md) records the cache observation, responsive theme checks and release caveats.
