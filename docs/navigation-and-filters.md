# Navegação e filtros do catálogo

Inventário conferido contra `d603f04:dndtools/templates/dnd/menu.html`, os menus móveis antigos, as rotas atuais e o catálogo local. A navegação é definida em `dnd/navigation.py` e aparece na mesma ordem no desktop e no celular. O nome de cada edição é obtido do banco; a página de Edições também permite chegar a todas as linhas editoriais existentes.

## Correspondência dos acessos antigos

| Acesso anterior | Local na navegação atual | Destino / situação |
| --- | --- | --- |
| Rulebooks → All | Rulebooks → All rulebooks | `/rulebooks/` |
| Rulebooks → Editions | Rulebooks → Editions | `/rulebooks/editions/` |
| 3.5 Core, Supplements, Dragonlance, Eberron, Forgotten Realms | Rulebooks → Editions → D&D 3.5 | Página própria de cada edição, com ID e slug lidos do banco; Dragonlance usa o slug real `dragonlance` |
| Books 3.0 (constante antiga sem item visível) | Rulebooks → Editions → D&D 3.0 | Páginas das quatro linhas 3.0 presentes no banco |
| Rulebooks → Rules | Rulebooks → Rules | `/rules/`; condições em `/rules/conditions/` |
| Character Options → Classes | Character Options → Classes | `/classes/` |
| Character Options → Feats, Feat Categories, Traits, Flaws, Skill Tricks | Character Options → Feats → Feat categories | `/feats/`, `/feats/categories/`, `/feats/categories/trait/`, `/feats/categories/flaw/`, `/feats/categories/skill-trick/` |
| Character Options → Skills | Character Options → Skills | `/skills/`; lista por livro em `/skills/by-rulebooks/` |
| Character Options → Deities, Languages | Character Options → Deities, Languages | `/deities/`, `/languages/` |
| Magic → Spells | Magic → Spells | `/spells/`; lista por livro em `/spells/by-rulebooks/` |
| Magic → Schools, Descriptors, Domains | Magic → Spell schools, Descriptors, Domains | `/spells/schools/`, `/spells/descriptors/`, `/spells/domains/` |
| Magic → Shadow Casting, Invocations, Psionics, Auras, Maneuvers | Magic → itens com selo Planned | Eram apenas anúncios sem rota; continuam sem página funcional |
| Bestiary → Races, Race Types, Monsters | Bestiary → Races / Monsters | `/races/`, `/races/types/`, `/monsters/` |
| Bestiary → Monstrous Types | Bestiary → Monsters → Monster types | `/monsters/types/`; os registros já existiam, com páginas de detalhe |
| Bestiary → Monstrous Traits, Templates | Bestiary → itens com selo Planned | Eram apenas anúncios sem rota |
| Items → Magical | Items → Magical items | `/items/` |
| Items → Mundane / Alchemical | Items → item com selo Planned | Era apenas anúncio sem rota |
| My D&D | My D&D com selo Planned | Nunca houve área funcional nesse menu |
| Contacts → Contact Us, News, Staff | Contacts → Contact us, News, Staff | `/contacts/`, `/`, `/contacts/staff/` |
| Android | Contacts → Android | `/contacts/android/`; o texto antigo não consta do snapshot, e a página informa a lacuna |

O menu móvel antigo também continha **Spells by rulebooks** e **Skills by rulebooks**. As páginas públicas correspondentes agora existem e os endereços `/m/...` redirecionam para elas, preservando os parâmetros de consulta. Races, Monsters e Items by rulebook continuam disponíveis nas respectivas seções.

Na página de cada livro, os links contextuais para magias, talentos, classes, perícias, itens e raças do livro continuam no bloco “In this rulebook”. Links de edição e verificação só aparecem para a equipe autenticada. As páginas de detalhe mantêm seus caminhos e breadcrumbs.

## Busca

`/search/` consulta os tipos de conteúdo listados em `dnd/search.py`, inclusive edições, condições, escolas, descritores, categorias e tipos de criatura. Nome exato, início do nome, parte do nome e texto descritivo têm esta prioridade, nessa ordem. A comparação usa a collation MySQL `utf8mb4_0900_ai_ci`, portanto não diferencia maiúsculas nem acentos. Os resultados exibem tipo, livro e edição quando o modelo possui esses relacionamentos. A seleção de uma categoria pagina de 30 em 30 no servidor. As sugestões usam apenas nomes, começam com dois caracteres, aguardam 250 ms e descartam respostas antigas. Não foram inventados sinônimos ou traduções: o banco não tem campo canônico para eles.

## Filtros

Em `/spells/`, filtros diferentes são combinados com **E**. Várias escolhas do mesmo campo (níveis, descritores ou edições) são combinadas com **OU**. Classe e nível pertencem ao mesmo registro `SpellClassLevel`; domínio e nível seguem a mesma regra em `SpellDomainLevel`. O nível **0** é válido. “All” ou campo vazio não impõe restrição; “Not specified” seleciona vínculos ou metadados ausentes nos campos em que essa opção aparece. Livro, linha editorial (`DndEdition`), sistema 3.0/3.5 e publicação básica (`core`) são filtros distintos. O banco não contém campos separados e confiáveis para “cenário” e “tipo de publicação” além dessa linha editorial e do indicador `core`.

Magias permitem filtrar nome, classe, nível, escola, subescola, descritor, componentes, tempo de execução, livro, edição, sistema, tipo básico, domínio, alcance, duração e descrição. O parâmetro `sort` ordena por nome, livro, escola ou nível de classe. A URL contém escolhas, ordenação e paginação; aplicar ou remover filtros volta à página 1. O painel mostra os filtros ativos, permite remover cada seleção e limpar tudo. Consulta inválida apresenta erro explícito e a lista sem filtros, em vez de aparentar zero resultados.

Livros, classes, talentos, criaturas, raças, itens, perícias, idiomas, regras, domínios, descritores e divindades mantêm seus filtros próprios definidos em `dnd/filters.py`. O painel compartilhado mostra contagem, seleções ativas e ações para remover e limpar. Os modelos incorretos dos filtros de classes, monstros e raças foram corrigidos. As opções vazias antes rotuladas “Unknown” agora dizem “All”, pois não aplicam restrição; seleções múltiplas não duplicam registros. O filtro legado ainda usa `django_filters2`; valores inválidos exibem erro e não são aplicados parcialmente. Esse componente deve ser substituído gradualmente para permitir semântica uniforme de “Not specified” em todas as categorias.

Os filtros textuais do catálogo, inclusive pré-requisitos dos talentos, aplicam a collation MySQL `utf8mb4_0900_ai_ci` na consulta. Assim, maiúsculas e acentos não alteram a correspondência, mesmo que as colunas estejam na collation original sensível a maiúsculas. A busca global e os filtros de magia usam a mesma collation.

## Referências visuais

A estrutura usa grupos e subgrupos do catálogo local, inspirada no [guia de navegação do Mintlify](https://www.mintlify.com/docs/organize/navigation). A busca e a separação dos filtros de magia foram comparadas com a [página de magias do D&D Beyond](https://www.dndbeyond.com/spells); os campos de D&D 5e não foram importados como regras de D&D 3.5.
