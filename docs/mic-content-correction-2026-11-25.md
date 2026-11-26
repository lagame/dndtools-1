# MIC: revisão de texto e apresentação (25/11/2026)

## Fonte e pacotes privados

- Fonte: *Magic Item Compendium (Premium Edition)*, SHA-256 `76e546b44ed188f0d4118799c65d44a2fb781d77182cb46d927f89e7a0942bac`.
- O pacote anterior de aprimoramentos (`v1.3`) continha 32 registros. O pacote final de revisão, `Aprimoramentos v1.5-para-revisao.zip`, tem SHA-256 `c8d6dd021d9e286a09ea391ee8b3a8930a80691e4ddcb688e2824ba7d3a47844`. Os manifestos das versões anteriores e os hashes por registro estão no ZIP privado.
- O pacote anterior de armaduras e escudos específicos foi preservado. `SPECIFIC ARMOR AND SHIELDS - revisado v3.zip` tem SHA-256 `9f51f6f573d227a20eba77f2c94943d5bba02115d10cb563dd34ab955a4bc605`, com manifestos e hashes por registro.
- Nenhum ZIP, PDF, banco, backup ou texto integral do livro foi incluído no Git.

## Achados e correção local

- Stamina, p. 15: a descrição do pacote e do item importado localmente omitia a frase que concede o bônus de resistência nos testes de Fortitude. A frase consta da fonte e já estava no item existente em produção. O pacote e o item **local** foram corrigidos. O tipo `ENH` e o preço `+500 gp` foram preservados.
- Em Linked, Mindarmor, Styptic, Time Buttress e Vanishing, a frase de pré-requisitos estava dentro de `description`. Ela foi separada em `required_feats` e `required_extra`, mantendo as alternativas da fonte. Os pré-requisitos de Stamina já estavam no campo próprio.
- Nos 32 aprimoramentos, os pontos finais de `cost_to_create` e `required_extra` foram normalizados no arquivo. A ficha também passou a tolerar dados legados com ponto, acrescentando somente um ao exibir custo e pré-requisitos.
- O redirecionamento legado `/pt-br/m/` preserva agora o idioma e a URL da ficha responsiva. Testes de EN/PT-BR seguem a rota efetiva em desktop e no alias móvel; a CI executa a mesma suíte.
- A ficha aplica a tradução PT-BR aprovada antes de preparar custo e pré-requisitos. Um teste garante que esses campos e a descrição visual sejam traduzidos sem modificar o item original nem a página EN.
- Os trechos de apresentação em itálico foram separados para `visual_description` nos 28 aprimoramentos que os têm e nos 25 itens específicos. As quatro sinergias sem trecho visual ficaram sem itálico. O texto de Millennial Chainmail que antecedia a descrição do PDF foi retirado da versão privada.
- Após backup local verificado, 54 registros já importados localmente foram corrigidos numa única transação; 54 propostas de correção aprovadas registram a trilha local. A contagem permaneceu em 219 itens, dos quais 91 do MIC. Manifester, Earthplate e a duplicata Armor of the Fallen Leaves seguem fora dessa importação.

## Validação

- CRC e hashes do manifesto: 32/32 aprimoramentos e 25/25 itens específicos. A separação visual preserva todo o texto dos registros, exceto a mudança de ordem da restrição explicativa em Ranged; esta foi mantida no campo de descrição.
- Comparação automatizada de sequências com o texto extraído das páginas do PDF: 32/32 e 25/25 verificados. Alertas residuais referem-se a legendas de ilustrações e a uma referência de página no texto de Ranged; este método auxilia a revisão, mas não prova sozinho a fidelidade editorial integral.
- Prévia de formulário dos 54 registros corrigidos: zero diferenças restantes após a normalização de travessões feita pelo modelo.
- `python manage.py test dnd --noinput` no Docker local: 114 testes, OK.
- HTTP local: Stamina, Time Buttress, Barricade Buckler e Stamina Greater responderam 200 em EN e PT-BR; o efeito de Stamina aparece, os trechos visuais verificados estão em parágrafo itálico e não há ponto duplo nesses exemplos. As URLs legadas `/m/` redirecionam para a mesma ficha responsiva; os testes seguem esse redirecionamento em ambos os idiomas.

## Pendências

- Os pacotes permanecem **para revisão**. Direitos de publicação e campos de Manifester e Earthplate precisam de decisão editorial antes de qualquer importação adicional em produção.
- Traduções PT-BR usam `PublishedTranslation` e aprovação editorial separadas. O importador de itens ainda não recebe traduções no mesmo JSON; um arquivo acompanhante pode ser preparado pela IA e conferido antes de criar as propostas. Nenhuma tradução automática foi publicada.
- Não houve nova importação ou alteração de conteúdo em produção nesta revisão. A correção genérica da pontuação na ficha depende de revisão e implantação do código.
