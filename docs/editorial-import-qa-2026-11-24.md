# Importação editorial • QA de 24/11/2026

> Registro histórico da implementação inicial. A política posterior restringe a importação direta a Ronassic; veja [a validação atual](editorial-guard-qa-2026-11-24.md). Os resultados abaixo descrevem apenas aquela versão.

## Escopo

- A permissão por recurso começa desativada para permissões existentes. Para importar, um colaborador precisa de convite ativo, permissão de inclusão e permissão de importação no mesmo recurso.
- A prévia é privada e vinculada à conta, ao tipo de registro e ao conteúdo conferido. A confirmação revalida esses dados. A publicação cria todos os registros e suas entradas de auditoria na mesma transação.
- Cada tipo oferece exemplos fictícios em CSV com vírgula, CSV com ponto e vírgula e JSON. O README descreve o uso em inglês e português.

## Validação local

- `docker compose run --rm --no-deps app python manage.py test dnd --noinput` passou com 92 testes. O Django criou e descartou o banco MySQL de teste. O teste dos exemplos baixou, abriu a prévia e publicou em banco de teste os 33 arquivos, abrangendo os 11 tipos. Outro teste confirmou que duas publicações simultâneas geram um único registro.
- Os testes cobriram a rejeição de arquivos inválidos, uploads acima dos limites, falta de CSRF, acesso sem convite ou permissão, referência que mudou após a prévia, edição diferente de 3.5 e reversão de todo o lote. A auditoria e o aviso por e-mail foram verificados com o backend de e-mail em memória.
- `docker compose build app` compilou as traduções PT-BR. `makemigrations --check --dry-run` e `check --deploy --fail-level WARNING` passaram.
- A consulta ao OSV não retornou alertas para os 17 pacotes Python instalados na imagem local. A consulta cobre somente as versões Python consultadas.

## Revisão

A revisão corrigiu a possível troca de relações entre a prévia e a confirmação, a disputa entre publicações simultâneas e a regressão que deixava de registrar o verificador ao aprovar uma correção de magia. Também corrigiu o modelo suplementar com tipo em branco e a resposta a níveis psiônicos inválidos.

O importador confere o livro cadastrado e sua edição. O responsável pela publicação ainda precisa conferir livro, página e direitos de publicação na fonte original.
