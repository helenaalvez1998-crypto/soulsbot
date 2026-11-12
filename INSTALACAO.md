# Instalação, configuração e atualização — SoulsBot / Nara

O pacote **não** contém token Discord, chaves de IA, `.env` nem banco de produção. Esses itens são da sua instalação. O único banco incluído é `data/jogos.db`, um modelo vazio do catálogo de jogos (veja `data/LEIA-ME-DADOS.txt`).

## 1. Requisitos

- Windows 10/11 ou Linux, com **Python 3.11 ou superior**.
- Um bot criado no Discord Developer Portal e o token dele.
- Uma chave Gemini para a conversa livre da Nara. FAQ e consultas locais funcionam sem chave de IA.
- Tavily é opcional e serve só para a pesquisa web da Nara.
- Armazenamento persistente para `data/` (importante em hospedagem).

## 2. Instalação

Extraia o ZIP inteiro para uma pasta permanente. Não rode o bot de dentro do ZIP.

**Atalho (Windows):** dê duplo clique em `INICIAR_WINDOWS.bat`.
**Atalho (Linux):** `chmod +x iniciar_linux.sh && ./iniciar_linux.sh`.

Os dois criam o `.venv`, instalam o `requirements.txt`, rodam o configurador e iniciam o bot.

**Manual:**

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS:        source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python configurar_bot.py
python bot.py
```

O `configurar_bot.py` pede, com digitação oculta, o token Discord, a chave Gemini principal e as chaves reserva e terceira (opcionais). Pede também o `GUILD_ID` e grava tudo em `.env`. Enter mantém o valor já salvo. `GUILD_ID=0` sincroniza os comandos globalmente, o que pode demorar a aparecer. Também dá para copiar `.env.example` para `.env` e preencher à mão.

Nunca envie `.env`, token, chaves ou `data/colizeu.db` em chats, tickets ou repositórios públicos.

## 3. Discord Developer Portal

- Ative **Message Content Intent**, **Server Members Intent** e mantenha **Voice States** habilitado.
- Convide o bot com os escopos `bot` e `applications.commands`.
- Permissões: ver canais, ler histórico, enviar mensagens, embeds/links, anexar arquivos, usar comandos, ler e enviar em tópicos, criar e gerenciar tópicos privados, **Gerenciar Canais** e **Gerenciar Cargos**.
- O cargo mais alto do bot deve ficar acima dos cargos de patente, verificação e autoatribuíveis. O bot não cria cargos ausentes: crie antes os 10 cargos de patente descritos no `README.md` e o cargo de verificação (`Servidor Simplificado` ou uma variação compatível).

## 4. Configuração no servidor

1. Execute `/adm` e clique em **Configuração Automática**. Ela cria a categoria e os canais oficiais da Nara, sem criar cargos, sem publicar mensagens de teste e sem alterar ou apagar canais existentes.
2. Em `/adm` > Cargos, escolha o cargo da equipe de moderação, que ganha acesso à Central de Aprovação privada.
3. Use `/adm` > Canais para trocar qualquer destino. As escolhas ficam salvas por servidor no SQLite.

O `.env.example` traz só o mínimo (`DISCORD_TOKEN`, `GUILD_ID`, `NARA_CHANNEL_ID`, `CATALOGO_DATA_DIR`). Os demais IDs de canais, cargos e recursos são definidos pelo `/adm` ou por variáveis de ambiente (veja `config.py`). Ajuste ao menos: `GUILD_ID`, canal de moderação, platinas, Coliseu e perfis.

Detalhes do painel em `GUIA_CONFIGURACAO_VISUAL.md`. O fluxo de aprovações está em `CENTRAL_DE_APROVACAO.md`.

## 5. IA: Gemini e Tavily

| Variável | Função |
| --- | --- |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | projeto principal |
| `GEMINI_BACKUP_API_KEY` / `GEMINI_BACKUP_MODEL` | projeto reserva (failover automático) |
| `GEMINI_THIRD_API_KEY` / `GEMINI_THIRD_MODEL` | terceira configuração (opcional) |
| `*_QUOTA_COOLDOWN_SECONDS` | pausa de cada projeto após quota esgotada (padrão 21600) |
| `*_CIRCUIT_STATE_FILE` | estado persistente dos circuit breakers, em `data/` |
| `TAVILY_API_KEY` | pesquisa web da Nara (opcional) |
| `TAVILY_MAX_QUERIES_PER_JOB` | máximo de consultas por pesquisa (1 a 4, padrão 4) |
| `NARA_CONVERSA_ENABLED=true` | liga a conversa livre com Gemini |
| `NARA_CHAT_IA_ENABLED=false` | desliga só a pesquisa factual com ferramentas; não desliga o papo livre |
| `OFFERS_SHOW_DESCRIPTION=false` | evita chamadas extras de tradução nas ofertas |
| `IA_ACOES_MODERACAO=false` | mantém a concessão de XP por IA desligada |

Variáveis no painel da hospedagem têm precedência sobre o `.env`. Mais detalhes em `CONFIGURACAO_IA_NARA.md` e `NARA_GEMINI_TRES_CHAVES.md`.

**Criar as chaves sem plano pago**

1. No [Google AI Studio](https://aistudio.google.com/), gere uma key para `GEMINI_API_KEY`.
2. Para reserva real, use **outro projeto Google** em `GEMINI_BACKUP_API_KEY`. A quota é por projeto: duas chaves no mesmo projeto compartilham o mesmo limite.
3. Não vincule faturamento a nenhum projeto; use só o Free Tier.
4. Na Tavily, use o plano **Researcher Free** (1.000 créditos mensais, sem cartão) e não faça upgrade. Cada consulta Basic custa 1 crédito. Se acabarem, a pesquisa pausa até a renovação mensal, sem compra automática.

A pesquisa roda pela Tavily e os Gemini recebem apenas texto e trechos recuperados, sem Google Search grounding. A conversa da Nara não lê prints nem imagens; anexos de comprovação ficam nos formulários de platina, run e zerado, para revisão humana.

`/gemini_status` mostra os circuit breakers do Gemini e o estado local da Tavily. "Circuito liberado" não confirma a quota real restante no fornecedor.

## 6. Checklist depois de conectar

- `/nara`: teste os botões da central dos membros, incluindo Central de Ajuda e Memória da Nara.
- Faça uma pergunta de FAQ num canal de `IA_CANAIS_LIVRES`; fora deles, mencione a Nara.
- `/adm`: confira canais, cargos e recompensas.
- Publique só os painéis que vai usar: `/painel_principal`, `/painel_platinas`, `/postar_painel_zerados`, `/painel_santuarios`, `/painel_cargos`, `/painel_loja`.
- Teste a atribuição de um cargo e a hierarquia do bot antes de liberar cargos autoatribuíveis.
- Teste uma platina, uma run (com prova de teste e DMs habilitadas) e um jogo zerado em ambiente controlado. Confirme que os três cartões chegam ao canal central e que aprovar e rejeitar funcionam. Não use registros falsos em produção.
- `/gemini_status` e os comandos de status de YouTube e ofertas.

Os testes automatizados passam e os `.py` compilam, mas login, sincronização de comandos, permissões reais, DMs, chaves e persistência dependem do seu servidor. Faça o checklist antes de considerar a implantação concluída.

## 7. Atualização

1. Pare o bot.
2. Faça backup de `.env` e `data/`.
3. Extraia o ZIP novo sobre o projeto, preservando `.env` e **sem apagar `data/colizeu.db`**.
4. `python -m pip install -r requirements.txt`.
5. Na hospedagem, remova variáveis de provedores que não são mais usados e confira as chaves Gemini e Tavily.
6. Reinicie e leia os logs.

## 8. Hospedagem

Em hospedagem (por exemplo FadeHost), defina `DATA_DIR=/data` e `DB_PATH=/data/colizeu.db`, cadastre tokens e IDs no painel e mantenha o volume persistente. Passo a passo em `DEPLOY_FADEHOST.md`.

## 9. Testes locais

```bash
python -m compileall -q .
python -m unittest discover -s tests -v
# ou: pytest -q   (requer requirements-dev.txt)
```
