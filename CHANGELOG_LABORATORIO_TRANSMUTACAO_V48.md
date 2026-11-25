# Narabot — V48 Ateliê de Arte do Criador

## Objetivo
Permitir que o próprio proprietário gere a ilustração em qualquer ferramenta de imagem, usando um prompt personalizado criado pelo Narabot, e envie o resultado para a carta pessoal.

## Entregas
- `sistemas/prompt_arte_criador.py`: monta prompt com nome, lore, facção, raridade, afinidades, função, habilidade e metadados da carta.
- Campos da carta são tratados como dados citados, não como instruções ao gerador de imagem.
- `sistemas/arte_upload_criador.py`: valida PNG/JPEG/WEBP, limite 12 MB, dimensões mínimas 500x400, proporção horizontal aproximada 5:4, rejeita imagens corrompidas e normaliza para PNG.
- Página autenticada `/atelie-arte?card_id=<id>`.
- Endpoint autenticado `GET /api/gwent/cartas-geradas/{card_id}/prompt`.
- Endpoint autenticado `POST /api/gwent/cartas-geradas/{card_id}/arte`.
- Endpoint autenticado `GET /api/gwent/cartas-geradas/{card_id}/arte` para servir a arte apenas ao proprietário.
- Catálogo pessoal inclui link para abrir o Ateliê em cada carta.
- Upload associa imagem e manifesto SHA-256 ao proprietário e ao ID permanente da carta.
- Substituição de arte exige ação explícita do criador (`?replace=1`); versões anteriores não são apagadas do armazenamento.
- Nenhum material ou ingrediente do jogo é consumido durante upload.

## Segurança e integridade
- Toda consulta é escopada por `owner_id` e `card_id`.
- Upload exige autenticação e validação de origem.
- Nome de arquivo enviado pelo navegador não é usado como caminho.
- Armazenamento é separado por proprietário e carta, com nome baseado no SHA-256.
- Imagem é decodificada e regravada como PNG, removendo metadados originais.
- A arte é servida por endpoint privado que verifica o diretório permitido.

## Validação executada
- 26 testes direcionados V42–V48: aprovados.
- `py_compile` dos módulos e `site_hub.py`: aprovado.
- `node --check` para JavaScript do Ateliê e Catálogo: aprovado.
- Suíte completa: 151 passed, 148 subtests passed, 6 failed em `tests/test_elden_art_prompts.py` (falhas já identificadas em validações anteriores).

## Limitações
- Não houve teste visual em navegador nem upload por sessão autenticada real.
- Não houve teste de integração contra banco de produção.
- O sistema gera o prompt e recebe a imagem; não chama automaticamente um gerador externo. O criador escolhe e utiliza sua ferramenta de imagem.
- A associação da arte ao motor de batalha deve ser conferida no ambiente real para garantir que todos os clientes exibam a URL privada autenticada corretamente.
