# NARABOT V57 — Auditoria integral do catálogo

## Escopo

Revisão dos 110 modelos estáticos: 95 cartas base, 5 Primordiais e 10 Patentes.

## Correções

- Preenchidas 21 descrições narrativas que estavam vazias.
- Corrigidas descrições narrativas obsoletas de Malenia, Radahn, Maliketh, Messmer e Placidusax.
- Separadas as descrições de ambientação dos textos mecânicos de Especiais, Relíquias e Primordiais.
- Reintroduzidos no dicionário `HABILIDADES` os seis textos mecânicos das Relíquias.
- Corrigidas as habilidades de Névoa de Sellia e Lua Gélida para refletir os handlers reais (marcas de Podridão Escarlate e Geada, não clima).
- A arte das cartas agora usa `preparar_carta()` para exibir exatamente o texto mecânico que o motor apresenta, incluindo habilidades de identidade e ajustes de raridade.
- Removida a indicação de escalonamento de raridade para Chama Negra e Lei da Regressão, que não alteram bônus.
- `VERSAO_ARTES` elevada para 26 para invalidar cache de artes com texto antigo.
- IDs, tipos mecânicos, poderes-base, raridades, custos e regras de batalha foram preservados.

## Testes

- 8 testes focados do catálogo: aprovados.
- 59 testes no total da suíte filtrada (incluindo os 8 focados; excluído o módulo de renderização pesada `test_molduras_faccoes`): aprovados.
- A suíte integral excedeu o limite de execução durante `test_molduras_faccoes`; não declarar a suíte completa aprovada.

## Limitações

- `colizeu.db` não está no pacote; cartas transmutadas, registros persistidos e exemplares dos jogadores não foram auditados.
- Cartas geradas por jogos não fazem parte dos 110 modelos estáticos.
- A facção do NARABOT é uma classificação estratégica própria, não uma filiação canônica automaticamente atribuível a cada personagem.
