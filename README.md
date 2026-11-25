# D&D Tools

A community fork of the original D&D Tools catalog, modernized for Python 3.14, Django 5.2 and MySQL 8.4. The public pages keep the original catalog URLs and now use a responsive layout and first-party search. The catalog source code is MIT licensed; bundled third-party forum packages retain their own licenses, and rights to individual book content must be assessed separately.

The site is available at [dndtools.quest](https://dndtools.quest/). It uses the HeroForge visual family with a self-hosted Inter font. `/privacy/` explains the site's technical cookies, the browser preference used to dismiss the notice, and how to contact the maintainer. No optional advertising or analytics cookies are active, so the notice is informational; adding such services requires a real choice before they run.

O [fórum phpBB integrado](forum-lab/README.md) funciona em [dndtools.quest/forum](https://dndtools.quest/forum/), com chat, cadastro e temas compartilhados.

**The database is not in this repository.** To request the private SQLite snapshot, [open an issue](https://github.com/lagame/dndtools-1/issues). We will arrange a private transfer. Never attach the database, a dump, or source scans to an issue or commit.

## Contributing

There are two ways to help. To add or correct spells, feats, items, monsters and other catalog records, ask the maintainer for an **editorial invitation**. Submit a proposal in the site's Editorial workspace; the record goes live only after review. Include the confirmed D&D 3.5 source book and page when applicable. Do not paste unverified AI output or copyrighted book text into a proposal.

For code, interface, tests and documentation, use a GitHub pull request. You do not need access to the production server or the private catalog database:

1. On [the project repository](https://github.com/lagame/dndtools-1), click **Fork** in your own GitHub account.
2. In PowerShell, clone **your fork** and create a branch:

   ```powershell
   git clone https://github.com/YOUR_USERNAME/dndtools-1.git
   cd dndtools-1
   git switch -c feat/short-description
   ```

3. Follow [Local setup](#local-setup-windows-powershell) to run the site. Without the private database, the catalog is empty, but the application and automated tests still work.
4. Make a focused change. If you use an AI coding assistant, review its diff, verify any claims about D&D 3.5 against the source, and run the relevant tests. For Django changes, use `py -3 scripts\prepare_test_db.py` followed by `docker compose run --rm app python manage.py test dnd --keepdb --noinput`.
5. Check `git status --short`, stage only the intended files, commit, and push your branch:

   ```powershell
   git add PATH_TO_CHANGED_FILE
   git commit -m "feat(scope): describe the change"
   git push -u origin feat/short-description
   ```

6. On GitHub, click **Compare & pull request** and target `lagame/dndtools-1:master`. Explain what changed and how you checked it. CI runs on pull requests; the maintainer reviews before merging. A merged PR does not deploy automatically.

Never include `.env`, passwords, tokens, database files, backups, uploaded images, or private user data in a commit, PR or Issue. If a task needs the private catalog, arrange access with the maintainer through an [Issue](https://github.com/lagame/dndtools-1/issues), without attaching the data there.

### Direct catalog import for the owner

Only Ronassic, as the owner, can publish a validated file directly. Collaborators with **Add records** permission submit individual proposals for Ronassic's review. Existing direct-import grant values are ignored; they do not authorize publication.

1. As Ronassic, find the resource in the **Editorial workspace** and select **Import records directly**. The importer supports spells, feats, monsters, items, creature templates and each supplemental rules family.
2. Download a filled example for that resource in comma CSV, semicolon CSV (common in Excel on Brazilian settings), or JSON. Replace the fictional values before uploading. Keep the field names and UTF-8 encoding. Every JSON record must declare the matching `resource` (for example, `"resource": "Item"`); a file for another importer is rejected before preview. Each file can contain up to **5,000 records and 40 MiB**. Use an existing D&D 3.5 rulebook in `rulebook` and cite the official book and page in `source_reference`.
3. For related records, enter the exact catalog name or its numeric ID. Use `|` between multiple values in CSV or a JSON array, such as `["General", "Fighter Bonus"]`. JSON uses a top-level list with one object per record. Use `true` / `false` for boolean fields and a decimal point in numeric fields. Use the proposal forms for links that have their own records, such as spell class levels and feat prerequisites.
4. Choose **Preview import**, check the records and confirm publication. Files above 250 records or 1 MiB run in the `editorial_import_worker` Docker service. You can close the page and return through **View your latest queued batch**. Queued previews expire after 24 hours. Smaller previews expire after 20 minutes.
5. For multiple files, finish each batch before uploading the next one. The importer adds new records and rejects duplicates and invalid batches. Each batch commits in a single transaction. The editorial history records the author and source of each entry, and Ronassic receives one email per published batch when SMTP is configured. Ronassic is responsible for checking the cited source and publication rights.

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
docker compose up -d app editorial_import_worker
```

Open <http://127.0.0.1:8765/>. For editorial access, create your own administrator after starting the app:

```powershell
docker compose exec app python manage.py createsuperuser
```

Enter the username, email and a unique password of at least 8 characters at the private terminal prompt, then open <http://127.0.0.1:8765/admin/login/>. No default administrator exists. The generated `.env`, original SQLite, MySQL volume, uploads and backups stay private and out of Git.

## Como contribuir

Há dois caminhos. Para incluir ou corrigir magias, talentos, itens, monstros e outros registros, peça ao mantenedor um **convite editorial**. Envie a proposta pelo Espaço editorial do site; ela só aparece no catálogo após revisão. Informe o livro D&D 3.5 confirmado e a página, quando houver. Confira resultados de IA antes de propor conteúdo e respeite os direitos dos textos dos livros.

Para contribuir com código, interface, testes ou documentação, envie um pull request (PR) pelo GitHub. Não é necessário acesso ao VPS nem ao banco privado:

1. Abra o [repositório do projeto](https://github.com/lagame/dndtools-1) e clique em **Fork** para criar uma cópia na sua conta GitHub.
2. No PowerShell, baixe **o seu fork** e crie uma branch para a mudança:

   ```powershell
   git clone https://github.com/SEU_USUARIO/dndtools-1.git
   cd dndtools-1
   git switch -c feat/descricao-curta
   ```

3. Siga a [configuração local](#configuração-local-em-português-windows) abaixo. Sem o banco privado, o catálogo fica vazio, mas a aplicação e os testes funcionam.
4. Faça uma mudança por PR. Se usar uma ferramenta de *vibe coding*, revise o código que ela gerou, confira fontes de regras 3.5 e rode os testes pertinentes. Para mudanças no Django, execute `py -3 scripts\prepare_test_db.py` e depois `docker compose run --rm app python manage.py test dnd --keepdb --noinput`.
5. Confira `git status --short`, adicione somente os arquivos da mudança e envie sua branch:

   ```powershell
   git add CAMINHO_DO_ARQUIVO_ALTERADO
   git commit -m "feat(scope): describe the change"
   git push -u origin feat/descricao-curta
   ```

6. No GitHub, clique em **Compare & pull request** e escolha `lagame/dndtools-1:master` como destino. Descreva o que mudou e como testou. A CI roda no PR; o mantenedor revisa antes de juntar. Um PR aprovado não publica automaticamente em produção.

Não inclua `.env`, senhas, tokens, banco, backups, imagens enviadas por usuários ou dados privados em commit, PR ou Issue. Se precisar do banco para uma tarefa, combine o acesso por uma [Issue](https://github.com/lagame/dndtools-1/issues), sem anexá-lo lá.

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
docker compose up -d app editorial_import_worker
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

Informe usuário, e-mail e uma senha exclusiva de pelo menos 8 caracteres no terminal. Depois abra <http://127.0.0.1:8765/admin/login/>. O projeto não fornece login ou senha padrão. Se você bloquear a própria conta após cinco tentativas erradas, espere 15 minutos; quem tem acesso ao servidor pode usar `docker compose exec app python manage.py axes_reset_username NOME_DO_USUARIO` para liberar apenas essa conta. A proteção usa o MySQL compartilhado pelos processos da aplicação.

A fonte Inter é servida pelo próprio projeto e sua licença OFL está em `dndtools/static/fonts/LICENSE-Inter.txt`. A página `/privacy/?lang=pt` informa os dados técnicos tratados, o contato do responsável e a duração do armazenamento no navegador.

O seletor **Theme** no cabeçalho oferece cinco visuais responsivos: **Standard** (roxo, inspirado no HeroForge), **Modern** (azul e dourado do projeto), **Simple** (branco, preto e links azuis), **Petroleo** (azul profundo com texto claro e detalhes dourados) e **Dark** (preto puro, superfícies neutras e botões dourados). A escolha fica apenas no `localStorage` deste navegador, sem conta ou cookie adicional, e permanece depois que você o fecha. Quem já usava o antigo Dark continua no mesmo visual, agora chamado Petroleo. No Simple, as próximas páginas não pedem o CSS roxo, a fonte Inter, o favicon nem as imagens de capa e raça; estas são substituídas por texto. A página HTML, os estilos básicos e os scripts necessários à navegação e busca continuam carregando. O pequeno pergaminho de Oghma, fixo perto da borda inferior, abre as ferramentas editoriais do Django; o acesso continua protegido por autenticação.

### Idiomas e colaboração editorial

O catálogo original em inglês permanece nas URLs atuais. O seletor **Language** abre a mesma página em `/pt-br/` e lembra a escolha por até um ano no cookie funcional `django_language`. Sem escolha anterior, a página inicial usa o idioma preferido do navegador. A interface pública tem mensagens em inglês e português; os dados de cada registro permanecem em inglês até que uma tradução integral seja proposta e aprovada. Nesse intervalo, a página em português informa que o conteúdo ainda está no idioma original. Os títulos traduzidos mostram também o nome em inglês, e a pesquisa aceita termos nos dois idiomas para registros com tradução aprovada. O texto da [política de privacidade](dndtools/templates/dnd/privacy.html) descreve essa preferência e os dados editoriais.

Depois de entrar no Admin, abra **Espaço editorial** (ou **Editorial workspace**, se a interface estiver em inglês). O seletor EN/PT-BR da administração acompanha o idioma escolhido no site. O proprietário pode convidar colaboradores por e-mail e conceder, por tipo de registro, permissão para propor inclusão, correção, tradução e remoção. O convite envia automaticamente um código de uso único, válido por sete dias, ao e-mail cadastrado; convites pendentes ou revogados podem ser reenviados pelo formulário de convite. O convidado entra pelo Cloudflare Access com código por e-mail e MFA; ao visitar a administração, é encaminhado à ativação para usar o código do convite uma vez. São códigos diferentes. Convite vencido precisa ser reenviado. Após o Access verificar a identidade, Ronassic e os colaboradores ativos entram automaticamente na sessão Django, sem outra tela de senha. A senha Django do proprietário continua cadastrada e pode ser trocada separadamente. Uma proposta só altera o catálogo quando Ronassic a aprova; a fila exibe a quantidade pendente. A inclusão, edição e exclusão diretas pelo Django Admin ficam restritas ao proprietário, mesmo se alguém conceder permissões Django de modelo a um colaborador por engano; permissões de leitura continuam funcionando. A referência editorial é obrigatória; informe a página do livro quando aplicável. Novos registros vinculados a uma edição ou livro precisam ser D&D 3.5 confirmados. O proprietário deve conferir a fonte antes de aprovar, especialmente nos tipos sem vínculo direto com livro. Não copie textos protegidos sem revisar os direitos de publicação.

O espaço editorial cobre os modelos recuperados de livros, regras, classes, talentos, magias, raças, monstros, itens e seus vínculos. Os 47 tipos disponíveis têm formulário de proposta; os campos de relacionamento mostram nomes legíveis e a busca editorial aceita nomes relacionados sem diferenciar maiúsculas de minúsculas. Há cadastro novo para **templates de criaturas** e para seis tipos antes ausentes: **mistérios de magia das sombras, invocações, poderes psiônicos, auras, manobras e traços monstruosos**. Cada família agora tem campos de regras próprios, filtros e ficha pública; poderes psiônicos também guardam classes e níveis em relações próprias, e traços monstruosos se vinculam a monstros. Escolha primeiro a família no espaço editorial e confira a fonte e a edição 3.5 antes de propor. A aprovação pelo proprietário continua obrigatória. Registros antigos sem detalhes tipados mantêm a URL, os dados e a ficha legada; a equipe pode enriquecê-los à medida que confirmar as fontes, sem preenchimento automático especulativo. O proprietário pode conceder acesso a cada um dos seis tipos separadamente ou a todos. Traços, defeitos e truques de perícia usam categorias de talentos; itens mundanos e alquímicos usam o tipo `MUN` do cadastro de itens. O antigo menu **My D&D** continua planejado porque é uma área pessoal, não um tipo de registro editorial. Colaboradores podem propor remoções quando receberem essa permissão; o registro permanece público até a aprovação do proprietário. A aprovação recusa apagar registros que tenham vínculos dependentes, para evitar perda de conteúdo em cascata. Resolva esses vínculos antes de reenviar a proposta.

Para receber um e-mail a cada proposta, configure **somente no `.env` privado** `DND_EDITORIAL_NOTIFY_EMAIL`, `DND_EMAIL_HOST`, `DND_EMAIL_PORT`, `DND_EMAIL_USER`, `DND_EMAIL_PASSWORD`, `DND_EMAIL_FROM` e `DND_EMAIL_USE_TLS`. Os três valores de destino, servidor e remetente são obrigatórios em produção; se usar Gmail, o usuário e a senha de aplicativo também são obrigatórios. A atualização recusa prosseguir se estiverem ausentes. Teste a entrega antes de convidar pessoas; caso o SMTP falhe, a proposta continua na fila e o colaborador recebe um aviso. Nenhuma credencial deve entrar no Git. Em produção, configure `DND_ACCESS_TEAM_DOMAIN` e `DND_ACCESS_AUD` (uma ou mais tags separadas por vírgula, se os dois hosts usarem aplicações distintas). O Django valida a assinatura, o emissor, a audiência e o vencimento do JWT do Access, além de vincular a sessão ao e-mail autenticado. O Admin precisa continuar protegido no Cloudflare em ambos os hosts.

Para liberar convidados na borda, crie **um grupo Access dedicado ao D&D Tools** com os e-mails exatos dos colaboradores e vincule-o a uma política Allow separada na aplicação Access que protege os dois hosts. Exija MFA nessa política e mantenha a política do proprietário. A lista desejada pode ser consultada no servidor com `docker compose -f compose.yaml -f compose.tunnel.yaml exec -T app python manage.py access_group_members`. Para ativar a sincronização automática no VPS, crie um token de API Cloudflare com permissão de conta `Access: Organizations, Identity Providers, and Groups Write`, limitado à conta correta. Rode como root `python3 /opt/dndtools/scripts/configure_access_sync.py --account-id ID_DA_CONTA --group-id ID_DO_GRUPO` e cole o token somente no prompt oculto; não o ponha na linha de comando, no chat ou no GitHub. O instalador confere o ID, o nome e as regras do grupo, sincroniza os e-mails, grava o token em `/etc/dndtools/access-sync.env` com permissão 600 e habilita o timer de dois minutos. **A sincronização remove do grupo quem não consta no Django como proprietário ou colaborador convidado/ativo.** O token não pode ser limitado a um único grupo: mantenha-o apenas no host e configure prazo/IP quando viável. O token não entra no container web; a política não deve conter regras amplas como Everyone. Confirme o timer com `systemctl is-active dndtools-access-sync.timer` e a execução com `systemctl status dndtools-access-sync.service`. Sem a sincronização, inclua e remova os e-mails manualmente no grupo Access. A revogação desativa a conta Django imediatamente; a retirada da política Access ocorre na próxima sincronização ou edição manual do grupo. Confira a borda e faça um convite completo em ambos os domínios antes de considerar o fluxo validado em produção.

Para convidados que não são membros da conta Cloudflare, adicione **One-time PIN** em **Zero Trust → Integrações → Provedores de identidade** e habilite esse método no aplicativo Access do D&D Tools e no App Launcher. Mantenha o provedor Cloudflare existente para o proprietário; não adicione colaboradores como membros da conta administrativa. A política Allow por e-mail exato e o MFA do aplicativo continuam necessários. Na política Allow do App Launcher, inclua o e-mail do proprietário **ou** o grupo dos colaboradores; deixe o próprio App Launcher acessível antes do MFA para que cada convidado possa cadastrar seu autenticador em **Account → MFA devices**. Teste o login externo no Access antes de publicar; depois da publicação, valide a ativação do convite no Django.

### Importação direta do catálogo pelo proprietário

Somente Ronassic, como proprietário, pode publicar diretamente um arquivo validado. Colaboradores com permissão de **Adicionar registros** enviam propostas individuais para a revisão de Ronassic. Valores antigos da permissão de importação direta são ignorados e não autorizam publicação.

1. Como Ronassic, encontre o tipo de registro na **Área editorial** e clique em **Importar registros diretamente**. A importação aceita magias, talentos, monstros, itens, modelos de criaturas e cada família de regras suplementares.
2. Baixe um exemplo preenchido para o tipo escolhido. Há CSV com vírgula, CSV com ponto e vírgula (comum no Excel em português) e JSON. Troque os dados fictícios, mantenha os nomes dos campos e salve em UTF-8. Cada registro JSON deve declarar o `resource` correspondente (por exemplo, `"resource": "Item"`); um arquivo de outro importador é recusado antes da prévia. Cada arquivo aceita até **5.000 registros e 40 MiB**. Em `rulebook`, indique um livro 3.5 já cadastrado. Em `source_reference`, cite o livro oficial e a página.
3. Use o nome exato ou o ID numérico para registros relacionados. Separe valores múltiplos com `|` no CSV ou use uma lista no JSON, como `["General", "Fighter Bonus"]`. No JSON, a raiz é uma lista com um objeto por registro. Use `true` ou `false` nos campos booleanos e ponto decimal nos campos numéricos. Vínculos com cadastro próprio, como níveis de magia por classe e pré-requisitos de talentos, podem ser propostos pelos formulários correspondentes.
4. Clique em **Ver prévia da importação**, confira os dados e confirme a publicação. Arquivos com mais de 250 registros ou 1 MiB rodam no serviço Docker `editorial_import_worker`. Você pode fechar a página e voltar pelo link **Ver seu lote mais recente na fila**. A prévia dos lotes em fila vale por 24 horas. Para os arquivos menores, vale por 20 minutos.
5. Se tiver vários arquivos, conclua cada lote antes de enviar o próximo. A ferramenta cria registros novos e rejeita lotes inválidos ou duplicados. A publicação grava cada lote em uma única transação. O histórico editorial guarda autor e fonte de cada registro, e Ronassic recebe um e-mail por lote publicado quando o SMTP está configurado. Cabe a Ronassic conferir a informação na fonte e os direitos de publicação.

### Administração em produção

Em produção (`DND_DEBUG=0`), defina `DJANGO_ADMIN_URL` no `.env` privado como um único segmento aleatório de 16 a 64 caracteres ASCII (`A-Z`, `a-z`, `0-9`, `_`, `-`), sem barras. Sem essa variável, a aplicação recusa iniciar. No desenvolvimento local (`DND_DEBUG=1`), a ausência dela mantém `/admin/`. Para uma instalação nova pelo script do túnel, o valor é gerado no `.env` privado; em instalações existentes, configure-o manualmente antes de atualizar. O ícone público de Oghma aponta para essa rota e portanto revela o caminho no HTML: ele não é um segredo nem substitui autenticação e Access.

**Antes de publicar esta branch**, ajuste no Cloudflare Zero Trust as aplicações **Access → Self-hosted** de `dndtools.quest` e `www.dndtools.quest` para cobrir `/<valor de DJANGO_ADMIN_URL>` e `/<valor de DJANGO_ADMIN_URL>/*` em ambos os hosts. A proteção atual de `/admin` não acompanha automaticamente a mudança da rota. Configure uma política **Allow** apenas para a identidade do administrador, com autenticação adicional no provedor de identidade. Em janela anônima, confirme que visitantes sem permissão não veem o login na rota nova e que os autorizados entram; confira também que o catálogo continua público. [As regras de caminho do Access](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/app-paths/) distinguem o caminho base dos subcaminhos. A aplicação continua limitando por nome de usuário e, ao receber `CF-Connecting-IP` de seu próprio proxy `tunnel_proxy` ou loopback, também por IP. Não use `X-Forwarded-For` do cliente para isso. O IP do container do proxy é resolvido dinamicamente, sem lista manual que envelheça. Consulte a [política de privacidade](dndtools/templates/dnd/privacy.html) para os dados guardados nas tentativas. A configuração e o acesso autorizado deste fork foram verificados em 15/11/2026; veja o [registro de QA do Access](docs/cloudflare-access-qa-2026-11-15.md). Cada nova instalação precisa repetir essa verificação.

O HTML do catálogo legado é sanitizado na renderização, incluindo os dados importados antes desta mudança. Tabelas, formatação e links de magias/talentos permanecem; scripts, eventos e URLs JavaScript são removidos. O cabeçalho CSP está em `Report-Only` para observar incompatibilidades sem bloquear recursos, sem coletor de relatórios configurado. A aplicação Docker roda como UID 10001; um serviço de inicialização ajusta somente a propriedade dos volumes de mídia e estáticos. Isso não modifica as portas globais, o Nginx ou os containers dos outros projetos.

Depois de publicar uma versão revisada, crie a conta na própria base de produção pelo terminal privado do VPS com `docker compose exec app python manage.py createsuperuser`. Não coloque usuário, senha, `.env`, banco ou backup no repositório ou nas Issues. Contas existentes com senhas antigas não são alteradas automaticamente; troque essas senhas pela administração assim que houver acesso.

### Cache e atualização do visual

O HTML do catálogo pede revalidação a cada visita. Os CSS e JavaScript usados pelo layout recebem automaticamente `?v=` com um resumo do conteúdo do arquivo. Quando um deles muda, a URL muda; o navegador e a Cloudflare buscam a versão nova sem depender de um *refresh* forçado ou de limpar todo o cache. Os arquivos antigos podem permanecer no cache até expirar sem afetar o HTML novo.

O cache público da Cloudflare foi observado com `CF-Cache-Status: DYNAMIC` no HTML e `HIT` no CSS; uma URL de CSS com nova versão retornou `MISS` e depois `HIT`. Essa verificação vale para a configuração atual. Se for criada uma regra de "Cache Everything" para HTML ou de ignorar parâmetros da URL, será preciso revisá-la. Arquivos privados de mídia enviados depois não recebem esse versionamento automático: para substituí-los, use um nome novo ou remova a URL antiga do cache.

Após uma atualização, confira os dois domínios, a página inicial, o `Cache-Control` do HTML e as URLs `?v=` dos CSS/JS no código da página. O fluxo de deploy faz backup do MySQL e verifica a origem antes de atualizar a aplicação.

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

Para **atualizações depois da instalação inicial**, execute manualmente **Actions → Deploy D&D Tools to VPS → Run workflow** na branch `master`. O workflow exige os mesmos segredos, recusa alterações locais no checkout do VPS e só aceita o commit atual da branch. Antes de atualizar, cria um dump MySQL em `/var/backups/dndtools` e testa sua restauração em um banco temporário. Depois atualiza apenas `/opt/dndtools`, aplica migrações e verifica a página inicial, o CSS, o redirecionamento `www` e os domínios do sitemap pela porta local `8766`. Não altera as rotas do Cloudflare nem os outros projetos do VPS. Se uma migração ou a verificação final falhar, investigue antes de repetir; o backup verificado permanece disponível para recuperação manual.

### Busca e indexação

O [sitemap público](https://dndtools.quest/sitemap.xml) usa `dndtools.quest` e inclui as listas principais e as fichas do catálogo. `www.dndtools.quest` redireciona para o domínio sem `www`. As listas sem filtros e as fichas em inglês têm URL canônica; resultados de pesquisa, listas filtradas e fichas em PT-BR ainda sem tradução completa recebem `noindex`. O `robots.txt` aponta para o sitemap. No **Google Search Console**, selecione a propriedade de domínio `dndtools.quest`, envie `https://dndtools.quest/sitemap.xml` em **Sitemaps** e acompanhe **Páginas**, **Ações manuais** e **Desempenho**. A indexação e a posição nos resultados dependem do processamento do Google e não são garantidas pelo envio do sitemap.

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
