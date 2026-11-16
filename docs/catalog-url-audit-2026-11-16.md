# Auditoria de endereços no catálogo — 16/11/2026

## Escopo e método

Varredura somente de leitura de todas as colunas textuais das 70 tabelas da cópia SQLite privada e das 79 tabelas do MySQL em produção. Procuramos URLs com esquema, nomes de domínio sem esquema e marcadores de HTML ativo (`script`, `iframe`, eventos e `javascript:`). Também revisamos as referências de URL no código, os templates públicos e o sanitizador de HTML. Não foram acessados os domínios encontrados.

## Resultados

- Um endereço com domínio aleatório apareceu apenas em `dnd_rulebook.official_url` do livro 67, *Fiendish Codex II*. O mesmo registro trazia `year=psvo`. Todas as cinco cópias SQLite examinadas já continham esse par. O campo `official_url` não é exibido pela ficha pública nem usado em requisições de rede do aplicativo.
- Após backup e teste de restauração do MySQL, a correção em produção limpou somente os dois campos desse registro. A leitura posterior confirmou `official_url=''`, `year=NULL` e zero ocorrências do domínio nas colunas textuais do MySQL.
- O MySQL local também recebeu a mesma correção pontual depois de um backup privado restaurado em banco temporário. A leitura posterior confirmou zero ocorrências no campo `official_url` local.
- Os demais domínios identificados nos dados de produção foram `dndtools.eu` (130 ocorrências em `body`/`body_html` de uma notícia antiga), `www.wizards.com` (50 ocorrências, principalmente nos 46 campos `official_url` dos livros), `d20srd.org` (duas ocorrências do mesmo texto de talento) e `example.com` (dois campos do registro padrão `django_site`). Os totais incluem cópias de HTML gerado e não representam links distintos.
- O filtro `safe_catalog_html` retira `href` externo, imagens e scripts de conteúdo legado. Um teste direto confirmou a remoção de links externos e HTML ativo. Descrições dos livros são escapadas no template. O campo `official_url` não é renderizado nas páginas públicas.
- O código contém algumas referências externas legítimas em documentação, licenças e templates móveis históricos; as fontes de cantrips guardam URLs de referência que não são carregadas pelo catálogo. O registro `example.com` é um placeholder do Django Sites; não há uso direto de `Site.objects` no código do projeto.

## Limites e acompanhamento

A busca cobre texto legível e padrões comuns de URL. Não prova ausência de dados ofuscados ou de links maliciosos em serviços externos. Os links históricos da Wizards e do domínio antigo do projeto não foram visitados nem tiveram disponibilidade conferida. A cópia SQLite original permanece intocada; o importador/curador deve corrigir o registro legado em novas instalações.
