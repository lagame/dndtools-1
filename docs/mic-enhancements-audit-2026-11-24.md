# Auditoria dos aprimoramentos do Magic Item Compendium — 24/11/2026

## Fonte e resultado

- Fonte conferida: *Magic Item Compendium (Premium Edition)*, capítulo Armor Properties, páginas impressas 11–15. Os títulos e blocos de estatísticas dos 32 registros foram localizados no PDF; as páginas 11 e 15 também foram inspecionadas visualmente.
- ZIP original preservado: `Aprimoramentos v1.1.zip` (SHA-256 `e7183c6d2a7fe26eb41b45f839f75561194e9915c263e115975b4831db007db5`).
- ZIP corrigido: `Aprimoramentos v1.2-conferido.zip` (SHA-256 `aaf3be33f610d9a41244a56277c5321bb41284dc61667a0f5f5c32ff2fce1d67`). O próprio ZIP contém `manifest.json` com SHA-256 antes/depois de cada registro.
- Nos 32 registros, preço, nível de conjurador e CD da aura conferem com a fonte. A página e `source_reference` estavam uma página adiante da numeração impressa e foram corrigidos. O tipo é aprimoramento (`ENH`) em todos.
- O catálogo de produção contém 38 itens do livro. Entre os 32 nomes do ZIP, apenas Stamina já existia; foi isolado em `existing-duplicate/`. Nenhum registro deste ZIP foi importado.

## Conferência por registro

| Registro | Pág. impressa | Propriedade | Preço | CL / CD | Situação |
|---|---:|---|---:|---:|---|
| Gilled | 11 | Armor | +6,000 gp | 5 / 17 | Novo, campos validados |
| Hammerblock | 12 | Armor or shield | +2 bônus | 7 / 18 | Novo, campos validados |
| Healing, Greater [Synergy] | 12 | Armor | +24,000 gp | 15 / 22 | Depende do registro base |
| Healing | 12 | Armor | +8,000 gp | 5 / 17 | Novo, campos validados |
| Heartening | 12 | Shield | +2,000 gp | 5 / 17 | Novo, campos validados |
| Landing | 12 | Armor | +4,000 gp | 5 / 17 | Novo, campos validados |
| Linked | 12 | Armor or shield | +6,000 gp | 7 / 18 | Novo, campos validados |
| Magic-Eating | 12 | Armor | +10,000 gp | 16 / 23 | Novo, campos validados |
| Manifester | 12 | Shield | +6,000 gp | 6 / 18 | Novo, campos validados |
| Masking | 12 | Armor | +40,000 gp | 10 / 20 | Novo, campos validados |
| Menacing | 13 | Armor | +30,000 gp | 9 / 19 | Novo, campos validados |
| Mindarmor | 13 | Armor or shield | +3,000 gp | 5 / 17 | Novo, campos validados |
| Mobility | 13 | Light armor | +1 bônus | 5 / 17 | Novo, campos validados |
| Nimbleness | 13 | Armor | +1 bônus | 8 / 19 | Novo, campos validados |
| Quickness | 13 | Armor | +5,000 gp | 5 / 17 | Novo, campos validados |
| Radiant | 13 | Armor | +4 bônus | 9 / 19 | Novo, campos validados |
| Ranged | 13 | Shield | +1 bônus | 5 / 17 | Novo, campos validados |
| Retaliation | 14 | Armor | +2 bônus | 9 / 19 | Novo, campos validados |
| Roaring | 14 | Armor | +3 bônus | 13 / 21 | Novo, campos validados |
| Soulbound, Greater [Synergy] | 14 | Armor or shield | +2 bônus | 18 / 24 | Depende do registro base |
| Soulbound | 14 | Armor or shield | +1 bônus | 6 / 18 | Novo, campos validados |
| Spearblock | 14 | Armor or shield | +2 bônus | 7 / 18 | Novo, campos validados |
| Speed | 14 | Armor or shield | +6,000 gp | 5 / 17 | Novo, campos validados |
| Stamina, Greater [Synergy] | 15 | Armor | +8,000 gp | 15 / 22 | Depende do registro base |
| Stamina, Improved [Synergy] | 15 | Armor | +4,000 gp | 9 / 19 | Depende do registro base |
| Stamina | 15 | Armor | +500 gp | 5 / 17 | Já existe; não importar |
| Styptic | 15 | Armor | +1 bônus | 7 / 18 | Novo, campos validados |
| Time Buttress | 15 | Shield | +5 bônus | 17 / 23 | Novo, campos validados |
| Twilight | 15 | Armor | +1 bônus | 5 / 17 | Novo, campos validados |
| Vanishing | 15 | Armor or shield | +3 bônus | 5 / 17 | Novo, campos validados |
| Variable | 15 | Shield | +1 bônus | 5 / 17 | Novo, campos validados |
| Woodwalk | 15 | Armor | +9,000 gp | 9 / 19 | Novo, campos validados |

## Campos e dependências

- O ZIP revisado declara `resource: Item` em cada JSON e preenche propriedade, intensidade e escola da aura. As ativações presentes no catálogo foram relacionadas pelo nome canônico. As descrições e demais textos foram preservados do ZIP original; a comparação de sequências de quatro palavras com o PDF encontrou cobertura de pelo menos 99% nos trechos, mas isso não prova que os trechos reproduzam o texto integral da fonte.
- `Manifester` declara ativação *Free (mental)* no livro, mas esse valor não existe na tabela atual de tipos de ativação. O campo foi deixado vazio e requer cadastro/revisão antes de publicar o registro completo.
- `Ranged` é apenas para escudos que não sejam escudos de torre. A relação atual permite somente `Shield`; a restrição específica deve ser mantida na revisão editorial.
- Quatro registros de sinergia usam `synergy_prerequisite` e ficam em `dependent-records/`: Healing Greater após Healing; Soulbound Greater após Soulbound; Stamina Improved após o Stamina corrigido; Stamina Greater após Stamina Improved. A prévia de cada dependente deve ser refeita depois de existir seu registro base.
- O importador local validou os 27 registros de `new-records/` como um conjunto, os demais campos dos quatro dependentes individualmente sem a relação ainda indisponível, e os 32 hashes do manifesto. Stamina foi excluído da carga como duplicata. O mesmo JSON `Item` foi recusado no importador `Spell` com motivo específico.
- Nenhum registro do ZIP foi enviado à produção. A publicação dos 27 novos itens e dos quatro dependentes continua pendente de revisão final de direitos e dos campos assinalados acima.

## Rechecagem antes da importação

- O ZIP revisado foi relido sem extração: os 32 arquivos de registro conferem com os hashes do `manifest.json` (27 novos, quatro dependentes e Stamina separado como duplicata). O formulário aceita `.json` ou `.csv`, não o ZIP.
- Em produção, o item 166 foi rechecado por consulta somente de leitura: Stamina está como `ENH`, página 15. A nota histórica do manifesto v1.2 que ainda diz `MAG` ficou desatualizada; este pacote não deve ser tratado como pronto para publicação.
- A ativação *Free (mental)* de Manifester ainda não existe no catálogo de produção. O arquivo de Ranged não menciona a exclusão de escudos de torre, embora essa restrição conste da fonte. Esses campos e a revisão dos textos precisam ser concluídos antes de publicar o lote.
