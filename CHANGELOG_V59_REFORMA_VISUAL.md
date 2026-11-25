# NARABOT V59 — Reforma visual

## Escopo
- Nova camada visual compartilhada em `site/narabot-visual-v59.css`.
- Aplicada ao portal principal e a seis páginas auxiliares.
- Unifica cores, superfícies, navegação, botões, formulários, painéis, tabelas e estados de foco.
- Ajusta responsividade em telas pequenas e respeita `prefers-reduced-motion`.

## Segurança da alteração
- Não altera JavaScript, APIs, banco de dados, identificadores, regras de combate ou lógica de negócio.
- Mantém `style.css` e `elden-ui.css`; a nova folha é carregada depois delas como camada de apresentação.

## Validação
- Conferência estática de inclusão do CSS nas páginas HTML.
- Conferência estrutural de chaves CSS.
- A validação visual final deve ser feita no navegador em desktop e celular, pois o pacote não inclui uma captura real do ambiente em execução.
