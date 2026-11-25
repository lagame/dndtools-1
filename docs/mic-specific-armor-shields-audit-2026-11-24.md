# Auditoria do pacote Specific Armor and Shields — 24/11/2026

## Escopo e conclusão

- Fonte: *Magic Item Compendium (Premium Edition)*, seção “Specific Armor and Shields”, páginas impressas 16–24. As nove páginas foram extraídas e inspecionadas visualmente.
- Pacote recebido: `SPECIFIC ARMOR AND SHIELDS, MIC pág 16 a 24.zip`, SHA-256 `91e8b7c0bfbaad362e0b29e54a6da1afed7199d619b5ab4e82f5cbc2814a3c13`. O original foi preservado; não houve extração nem importação para o catálogo.
- Os 25 JSONs são legíveis, têm CRC válido, caminhos seguros e nomes distintos dentro do ZIP. Não há manifesto de proveniência ou hashes por registro.
- Os 25 títulos começam nas páginas declaradas. Preço, nível do item, nível de conjurador, CD da aura e componentes numéricos do custo de criação conferem com os blocos da fonte. O nível do item foi conferido, mas nenhum JSON o informa.
- **Pacote não aprovado para importação.** Todos os registros declaram `type: ENH` embora sejam armaduras/escudos específicos completos (`MAG` no modelo atual), e nenhum declara `resource: Item`. Todos omitem `item_level`, `body_slot`, intensidade e escolas da aura e peso. Os 17 registros com ativação indicada no livro também omitem esse campo; nos outros oito, a fonte traz um traço e o campo vazio é adequado. Em 12 registros os pré-requisitos ficaram dentro de `description` em vez de `required_extra`.
- O texto das descrições tem alta sobreposição com a fonte (cobertura de sequências de quatro palavras entre 85,3% e 100%). Isso não comprova integralidade ou direitos de publicação; requer revisão editorial antes de divulgar qualquer texto.

## Conferência por registro

Os números abaixo foram conferidos com o PDF. `CL/CD` significa nível de conjurador e CD da aura. Todos têm os bloqueios estruturais acima.

| Registro do ZIP | Página(s) da fonte | Preço (po) | Nível do item | CL/CD | Catálogo de produção |
|---|---:|---:|---:|---:|---|
| Armor of the Fallen Leaves [Relic] | 16 | 17.350 | 14 | 20/25 | **Duplicata:** item 1, “Armor of the fallen leaves” |
| Barricade Buckler | 16 | 4.165 | 9 | 9/19 | Candidato novo |
| Bearskin Armor | 16 | 14.350 | 14 | 9/19 | Candidato novo |
| Dragonrider Armor | 17 | 18.300 | 15 | 5/17 | Candidato novo |
| Earthplate Armor | 17 | 41.650 | 17 | 9/19 | Candidato novo |
| Electric Eel Hide | 17 | 14.165 | 14 | 9/19 | Candidato novo |
| Exoskeleton Armor | 18 | 21.350 | 15 | 5/17 | Candidato novo |
| Foxhide Armor | 18 | 10.160 | 13 | 9/19 | Candidato novo |
| Ghoul Shell Armor | 18–19 | 10.160 | 13 | 12/21 | Candidato novo |
| Hawkfeather Armor | 19 | 12.175 | 13 | 9/19 | Candidato novo |
| Kyton Armor | 19 | 13.100 | 14 | 11/20 | Candidato novo |
| Millennial Chainmail [Relic] | 20 | 8.150 | 12 | 20/25 | Candidato novo |
| Mithralmist Shirt | 20 | 3.400 | 8 | 6/18 | Candidato novo |
| Overhead Shield | 20 | 24.170 | 15 | 10/20 | Candidato novo |
| Owlfeather Armor | 20 | 8.160 | 12 | 9/19 | Candidato novo |
| Serpent Armor | 20–21 | 12.160 | 13 | 9/19 | Candidato novo |
| Shield of Mercy | 21 | 2.170 | 6 | 5/17 | Candidato novo |
| Shield of the Resolute [Relic] | 21–22 | 5.520 | 10 | 20/25 | Candidato novo |
| Shield of the Severed Hand [Relic] | 22 | 4.657 | 9 | 20/25 | Candidato novo |
| Tigerskin Armor | 22–23 | 17.100 | 14 | 9/19 | Candidato novo |
| Vampire Hide Armor | 23 | 21.175 | 17 | 12/21 | Candidato novo |
| Wight Armor | 23 | 14.175 | 14 | 6/18 | Candidato novo |
| Wight Hide Shield | 23 | 9.159 | 12 | 12/21 | Candidato novo |
| Wrapped Tower | 24 | 6.180 | 10 | 12/21 | Candidato novo |
| Zombie Hide Armor | 24 | 16.165 | 14 | 5/17 | Candidato novo |

## Catálogo e importador

- Consulta somente de leitura à produção: 166 itens no total; nesta faixa de páginas do MIC, existe apenas o item 1, “Armor of the fallen leaves” (`MAG`, p. 16). Preço, nível do item, CL, aura, ativação e peso desse registro coincidem com a fonte. A diferença do sufixo `[Relic]` fez a comparação literal não detectar a duplicata.
- Consulta local: 165 itens; a mesma duplicata apareceu na busca aproximada. Não há outro nome idêntico ou semelhante entre os 25 e os itens cadastrados (limiar de similaridade 0,82), nem outro item do MIC nas páginas 16–24 em produção. Isso não substitui revisão manual de sinônimos.
- A validação local do primeiro JSON, como recebido, devolveu “JSON records must declare resource”. Uma simulação em memória com `resource: Item` e `type: MAG` passou para os 25, inclusive para a duplicata; a validação atual usa nome exato e livro. **Nenhum registro foi salvo** nesses testes.
- As citações `source_reference` dos quatro registros que atravessam páginas devem incluir ambas as páginas. `page` continua sendo a página inicial.
- Os 12 registros sem `required_extra` são: Armor of the Fallen Leaves, Earthplate, Electric Eel Hide, Exoskeleton, Foxhide, Ghoul Shell, Shield of the Resolute, Shield of the Severed Hand, Vampire Hide, Wight Hide Shield, Wrapped Tower e Zombie Hide. Os textos de pré-requisito aparecem em `description`; devem ser revisados e separados conforme os campos do catálogo.

## Condições antes de publicação

Conferir manualmente descrições, requisitos e direitos de publicação. Revalidar cada JSON e a prévia após as decisões editoriais. O pacote original não deve ser enviado ao formulário de importação; a versão corrigida continua apenas para revisão.

## Correção privada para revisão

- Criado na área de trabalho `SPECIFIC ARMOR AND SHIELDS - revisado 2026-11-24.zip`, SHA-256 `303bbc0d63d9d67e4f775017cb02cfe2e2482f63f851143191003766ed3f630e`. O ZIP original permaneceu intacto e **nenhum conteúdo do livro entrou no Git**.
- `manifest.json` registra SHA-256 original e corrigido de cada um dos 25 arquivos e os campos alterados. O pacote separa 23 arquivos em `candidates-review-required/`, Earthplate em `manual-review/` e a duplicata em `existing-duplicate/`.
- Os 25 JSONs agora declaram `resource: Item` e `type: MAG`, e incluem nível do item, espaço, aura, escolas, peso e a ativação quando há ação. Quatro referências foram ampliadas para duas páginas. Em 23 arquivos, o talento de criação foi relacionado pelo nome único do catálogo e os demais requisitos foram postos em `required_extra` sem exceder 64 caracteres. Os valores de `cost_to_create` perderam apenas o ponto final, que a página do item acrescenta ao renderizar. As descrições mecânicas não foram reescritas; em dez arquivos, somente a frase de pré-requisitos foi movida da descrição para os campos próprios.
- Earthplate permanece separado porque a condição alternativa “Bind Elemental **ou** Craft Magic Arms and Armor” não cabe integralmente no campo atual e não pode ser convertida em vínculos simples sem alterar o sentido. O texto integral está preservado na descrição. A duplicata permanece separada para comparação e não deve ser importada.
- O ZIP copiado foi reaberto: CRC íntegro, 25 hashes do manifesto iguais aos arquivos extraídos e SHA-256 igual ao da cópia de trabalho. Os 24 candidatos, inclusive Earthplate, passaram juntos pela validação **em memória** do importador local (`validated_rows`); nenhum registro foi salvo. Esta validação técnica não autoriza publicação. Ainda faltam revisão visual da separação entre descrição visual e regras, revisão dos textos e direitos de publicação.
