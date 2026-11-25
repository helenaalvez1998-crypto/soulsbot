# Gwent V8 — motor, economia, multiplayer e apresentação

## Escopo desta atualização

Esta versão foi construída sobre o ZIP completo enviado pelo usuário. Ela consolida o Gwent como único jogo de cartas ativo, completa fluxos essenciais da coleção e melhora a apresentação do site e das cartas.

## Auditoria do catálogo e balanceamento inicial

- Catálogo estático validado: 70 cartas únicas, sendo 59 unidades e 11 especiais.
- Distribuição das unidades por facção: 21 Ordem de Ferro, 17 Errantes do Véu e 21 Conclave Arcano.
- Faixas de poder atuais por raridade: Comum 3–5, Rara 5–6, Épica 5–7, Lendária 6–8 e Primordial 8.
- Todas as habilidades encontradas no catálogo estão mapeadas para handlers do motor.
- Isso é uma auditoria estrutural e numérica, não prova de equilíbrio competitivo: o balanceamento final ainda exige partidas reais e ajustes com base em taxa de vitória por facção/carta.

## Motor de batalha

- Embaralhamento seguro no servidor antes da distribuição das 10 cartas iniciais e 2 cartas de reserva.
- Validação de deck com exatamente 12 IDs únicos no motor.
- Poder efetivo centralizado: poder base + bônus − clima + resistência, com piso de 1.
- Placar por fileira exposto pela API para manter a interface idêntica ao cálculo do servidor.
- Unidades que sobrevivem no campo são movidas ao descarte ao fim de cada rodada, inclusive na rodada final.
- Histórico recente de ações persistido no snapshot da partida.
- Ação de concessão/abandono disponível mesmo fora do turno.
- Efeito de Queima Estratégica seleciona unidades pela força efetiva após clima.
- MMR alterado de bônus fixo para Elo de soma zero (K=32); empates não alteram MMR.

## Progressão e economia

- Entrega automática e idempotente dos kits iniciais no primeiro acesso autenticado ao site.
- Sincronização de cartas por jogos aprovados e liberação de patentes conforme o nível de XP.
- Mercado no site: pacotes de três cartas, preço de 120 Denários, limite de três em 24 horas, pity e Primordiais únicas.
- Forja de cartas com Almas, sem permitir forja de cartas Primordiais.
- Conversão de duplicatas em Almas e atualização de saldo após compra/forja.

## Multiplayer e segurança

- Ações permanecem transacionais no SQLite e são validadas pelo estado persistido.
- A interface pode reabrir partidas em andamento após reconexão; o navegador consulta o estado atualizado.
- Detalhes da partida mostram o nome/facção/líder do adversário.
- Imagens de cartas do adversário são autorizadas quando a carta faz parte de uma partida do usuário, evitando imagens quebradas para cartas que ele não possui.
- Ações de API exigem autenticação e validação de origem; heartbeat de presença do site foi implementado com expiração de 75 segundos.
- Corrigidos os handlers de origem/heartbeat ausentes no bot e removida a chamada para um broadcast inexistente; a arena usa polling do snapshot persistido.
- Recompensas por partida continuam protegidas por chave única `(match_id, user_id)`.

## Site e artes

- Identidade visual renovada com paleta de pedra, bronze e verde escuro.
- Construtor de deck com cartas maiores, imagens em proporção de carta, descrição de habilidade, poder, raridade e facção.
- Busca por nome/habilidade e filtros por facção e raridade.
- Mercado visual com abertura de pacotes e forja.
- Arena com placar por fileira, cartas de campo maiores, identificação do adversário, histórico e botão de concessão.
- Renderizador de cartas em modo Gwent: categoria, facção, fileira, classe e habilidade são mostradas sem os rótulos do sistema antigo.
- Versão do cache de arte atualizada para evitar reutilizar imagens antigas.

## Remoção do jogo antigo

- Removido `cogs/cartas_coliseu.py`, que continha o fluxo antigo de coleção/deck/duelo do Discord.
- Removidas rotinas de deck clássico e duelo antigo do runtime de `database.py`.
- Removidas regras de confronto antigo de cinco cartas de `sistemas/cartas.py`.
- As tabelas antigas de deck/duelo permanecem no SQLite apenas como arquivo histórico; não são apagadas nem acessadas pelo runtime novo.

## Testes executados

- 15 testes do motor Gwent.
- 5 testes do catálogo/renderizador.
- 3 testes do schema/migração SQLite.
- Renderização local de todas as 70 cartas estáticas.
- Compilação Python e verificação sintática JavaScript.

## Limitações verificadas

Os testes foram executados localmente. Não foi possível testar login OAuth real, permissões do Discord, banco de produção, latência de duas contas reais ou hospedagem do usuário. O pacote está preparado para implantação, mas não foi instalado no servidor.
