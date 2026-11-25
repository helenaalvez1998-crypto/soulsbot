# Narabot V73 — Artes personalizadas nas cartas de líder

## Funcionalidade
- Painel administrativo adicionado ao Ateliê para gerenciar a arte dos nove líderes do Gwent.
- Upload, substituição e restauração do retrato padrão por líder.
- Campo opcional de crédito do artista.
- Prévia da arte atual e identificação dos líderes que já possuem arte personalizada.
- A ilustração personalizada é utilizada no preview da carta de comando no construtor de deck para todos os jogadores.

## Persistência e segurança
- Nova tabela `cartas_gwent_lideres_artes`, criada automaticamente pelo schema do banco durante a inicialização.
- Imagem armazenada como BLOB no banco persistente; não depende de arquivos locais efêmeros da hospedagem.
- Endpoints de listagem, upload e remoção protegidos pela mesma lista administrativa do Ateliê.
- Upload protegido por validação de origem, whitelist de IDs de líderes, limite de 8 MB, validação Pillow e normalização para JPEG 1200 × 960 (5:4).
- Revisão SHA-256 usada como token de versão e ETag para evitar cache de imagens antigas.
- Endpoint de imagem exige sessão autenticada.
- Rota estática `/assets/` registrada para servir os retratos padrão existentes quando não houver arte personalizada.

## Interface
- O painel aparece em Ateliê → Ferramentas administrativas do Ateliê.
- Selecionar líder → escolher arquivo → Aplicar arte ao líder.
- Restaurar arte padrão remove a versão personalizada e volta ao retrato original do projeto.
