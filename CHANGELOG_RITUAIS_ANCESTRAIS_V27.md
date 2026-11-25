# V27 — Rituais Ancestrais

## Entregue
- Novo ritual `coroa_do_haligtree`: três exemplares específicos Lendários (Maliketh, Messmer e Gurranq/Clérigo Bestial) + 250 Fragmentos.
- Resultado: um exemplar Mítico do Cavaleiro Consagrado do Haligtree, no poder mínimo da raridade.
- Execução transacional: valida propriedade, IDs distintos, ingredientes, deck ativo e saldo antes do consumo.
- Sacrifício e custo registrados em `cartas_convergencias` e `cartas_movimentacoes`.
- Página web autenticada `/rituais-ancestrais` e API GET/POST correspondentes.
- Primordiais e Singulares não são ingredientes nem resultados; nenhum poder ou habilidade dessas raridades foi alterado.

## Limitações
- Sem teste de integração contra banco real neste ambiente; `aiosqlite` precisa estar instalado.
- Sem teste visual em navegador/Discord nem implantação em produção.
- A página usa a mesma confirmação explícita e fluxo de seleção de exemplares da página de Linhagens.
