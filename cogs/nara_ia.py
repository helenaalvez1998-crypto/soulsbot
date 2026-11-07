"""Nara com roteamento local-first e economia de quota.

Perguntas frequentes e consultas de perfil usam respostas determinísticas/SQLite.
A IA externa só é chamada para pesquisa conversacional que tenha ferramenta compatível
(atualmente fontes de Elden Ring). Pesquisa de troféus, platinas e catálogos de qualquer
jogo é encaminhada ao comando `/jogo_buscar`. A conversa da Nara é exclusivamente textual:
nenhum anexo é baixado, aberto, interpretado ou enviado ao modelo.
"""
import logging
import os
import random
import time
from pathlib import Path

import discord
from discord.ext import commands

from cogs.platinas import eh_moderador
from ia_confirmacao import AtalhoView, ConfirmarAcaoView
from ia_ferramentas import criar_registro
from ia_multi import RoteadorIA, TodosProvedoresIndisponiveis
from ia_nucleo import Ctx, Registro, Risco, rodar_agente
from levels import nivel_por_xp, patente_por_nivel
from gemini_resilience import GeminiUnavailableError, gemini_status
from deepseek_resilience import DeepSeekUnavailableError, deepseek_status
from nara_local import aplicar_politica_de_quota, decidir_rota, resposta_local_fallback, tem_anexo_visual

log = logging.getLogger("nara.ia")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip() or "gemini-3.8-flash"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash").strip() or "deepseek-flash"


def _env_nonnegative_int(name: str, default: int = 0) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except (TypeError, ValueError):
        log.warning("Valor inválido para %s; usando %s.", name, default)
        return default
    if value < 0:
        log.warning("Valor negativo para %s; usando %s.", name, default)
        return default
    return value


IA_LIMITE_DIARIO = _env_nonnegative_int("IA_LIMITE_DIARIO", 3)  # padrão: 3 pesquisas de chat por pessoa/dia; 0 desativa o limite
NARA_CHAT_IA_ENABLED = os.getenv("NARA_CHAT_IA_ENABLED", "false").strip().lower() in {"1", "true", "yes", "sim", "on"}
# Canais em que a Nara responde apenas intenções locais reconhecidas sem ser mencionada.
IA_CANAIS_LIVRES = {int(x) for x in os.getenv("IA_CANAIS_LIVRES", "").replace(" ", "").split(",") if x.isdigit()}
COOLDOWN_SEG = 8  # intervalo mínimo entre pesquisas externas feitas no chat por usuário
PROMPT_PESQUISA_PATH = Path(__file__).resolve().parent.parent / "prompts" / "nara_pesquisa.md"

# ------------------------------------------------------------------------- cog
class NaraIA(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # A Nara local está sempre ativa. Se pesquisa conversacional for habilitada,
        # DeepSeek é o principal e Gemini é a reserva automática (ou vice-versa por env).
        self.ia = None
        self.ia_config_error = ""
        if NARA_CHAT_IA_ENABLED and (DEEPSEEK_API_KEY or GEMINI_API_KEY):
            try:
                self.ia = RoteadorIA(
                    deepseek_key=DEEPSEEK_API_KEY, deepseek_model=DEEPSEEK_MODEL,
                    gemini_key=GEMINI_API_KEY, gemini_model=GEMINI_MODEL,
                )
            except Exception as exc:
                self.ia_config_error = f"{type(exc).__name__}: {exc}"[:300]
                log.exception("Provedores conversacionais não puderam ser inicializados; respostas locais continuam ativas.")
        self.ultimo_uso: dict[int, float] = {}
        try:
            self.prompt_pesquisa = PROMPT_PESQUISA_PATH.read_text(encoding="utf-8")
        except OSError:
            self.prompt_pesquisa = (
                "Você é Nara, assistente do Soulsbot: direta, inteligente e levemente irônica. "
                "Pesquise apenas Elden Ring com as ferramentas disponíveis, cite fontes abertas e não invente. "
                "Não receba, solicite, abra ou analise imagens/anexos."
            )
            log.warning("prompts/nara_pesquisa.md ausente; usando prompt mínimo de pesquisa.")
        if not NARA_CHAT_IA_ENABLED:
            log.info("Nara local-first ativa; chat com IA desligado para economia. DeepSeek/Gemini ficam reservados às pesquisas do Caçador.")
        elif self.ia is None:
            log.warning("Nara local ativa; nenhum provedor conversacional foi configurado. Perguntas básicas continuam sem API.")
        else:
            log.info("Nara local ativa; chat IA habilitado com failover. Principal=%s; DeepSeek=%s; Gemini=%s; limite=%s por usuário/dia.",
                     os.getenv("AI_PRIMARY_PROVIDER", "deepseek"), DEEPSEEK_MODEL if DEEPSEEK_API_KEY else "desativado",
                     GEMINI_MODEL if GEMINI_API_KEY else "desativado",
                     IA_LIMITE_DIARIO if IA_LIMITE_DIARIO else "sem limite local")

    async def cog_unload(self):
        if self.ia is not None:
            try:
                self.ia.close()
            except Exception:
                log.exception("Falha ao fechar adaptadores de IA da Nara")

    async def cog_load(self):
        await self.bot.db.conn.execute(
            """CREATE TABLE IF NOT EXISTS ia_uso (
                 user_id INTEGER NOT NULL, dia TEXT NOT NULL, qtd INTEGER NOT NULL DEFAULT 0,
                 PRIMARY KEY (user_id, dia))""")
        await self.bot.db.conn.commit()

    # ---- limite diário (conta só respostas bem-sucedidas)
    def _dia(self) -> str:
        import config
        import datetime as dt
        return dt.datetime.now(config.BRAZIL_TZ).strftime("%Y-%m-%d")

    async def _pode_usar(self, user_id: int) -> bool:
        if IA_LIMITE_DIARIO <= 0:
            return True
        row = await self.bot.db._one("SELECT qtd FROM ia_uso WHERE user_id=? AND dia=?", (user_id, self._dia()))
        return not (row and row["qtd"] >= IA_LIMITE_DIARIO)

    async def _registrar_uso(self, user_id: int):
        await self.bot.db.conn.execute(
            """INSERT INTO ia_uso(user_id, dia, qtd) VALUES (?,?,1)
               ON CONFLICT(user_id, dia) DO UPDATE SET qtd = qtd + 1""", (user_id, self._dia()))
        await self.bot.db.conn.commit()

    async def _responder_local(self, message: discord.Message, intent: str) -> str:
        """FAQ e consultas SQLite: sem modelo, sem rede e sem consumo de quota Gemini."""
        db = self.bot.db
        autor = message.author
        guild = message.guild

        if intent == "saudacao":
            import config
            from datetime import datetime
            hora = datetime.now(config.BRAZIL_TZ).hour
            cumprimento = "Bom dia" if hora < 12 else ("Boa tarde" if hora < 18 else "Boa noite")
            return random.choice([
                f"{cumprimento}, {autor.display_name}. Nara na área. O que precisa?",
                f"Ora, {autor.display_name} apareceu. Diga o que precisa — sem invocar nenhum chefe, por enquanto.",
                f"Oi, {autor.display_name}. Meus circuitos estão em ordem. E os seus?",
            ])
        respostas = {
            "identidade": "Sou a Nara, assistente do Soulsbot. Cuido das informações do servidor, dos painéis e das consultas que o bot consegue fazer.",
            "capacidades": "Consigo consultar seu perfil, XP, patente, Denários, platinas, jogos zerados, runs, rankings e loja; também explico os sistemas do Soulsbot. Pesquisas factuais de jogos, troféus e guias usam a IA externa quando você pede isso explicitamente.",
            "ajuda": "**Atalhos do Soulsbot**\n• `/coliseu` — platinas, runs, rankings e santuários.\n• `/zerados` — registrar e consultar jogos finalizados.\n• `/remover_zerado` — remover um registro seu de zerado.\n• `/nivel` — seu nível, XP e progresso.\n• `/ranking-xp` — ranking de XP.\n• `/cacador` — abrir o Caçador de Troféus.\n• `/jogo_buscar` — identificar jogo e pesquisar catálogo de troféus.\n• `/loja` — loja de itens cosméticos.\nUse os painéis para abrir formulários e consultar detalhes.",
            "como_registrar_platina": "Para registrar uma platina: abra `/coliseu`, entre em **Platinas** e escolha registrar. Preencha jogo, plataforma, data e envie o comprovante no formulário. A platina só entra no perfil e gera recompensa depois da aprovação da moderação.",
            "como_registrar_zerado": "Abra `/zerados` ou `/coliseu` e escolha **Zerados**. Use o formulário para informar jogo, plataforma e data. Confira os dados antes de enviar. O registro é gravado e a recompensa aplicável é calculada pelas regras do servidor.",
            "como_remover_zerado": "Use `/remover_zerado` para remover um registro seu de jogo zerado. Confira o jogo e a plataforma antes de confirmar; a remoção pode afetar suas estatísticas e a classificação.",
            "quando_recebo_recompensa": "A platina gera recompensa depois da aprovação da moderação. O jogo zerado é registrado diretamente pelo formulário e a recompensa aplicável é calculada no registro. Runs recebem XP após aprovação. Se o valor não apareceu, confira o registro e procure a moderação antes de enviar outro.",
            "como_funciona_aprovacao": "Platina e run ficam pendentes até a moderação analisar o registro e o comprovante. A aprovação libera a recompensa prevista; a rejeição não concede recompensa. O jogo zerado segue um fluxo próprio de registro, sem a mesma fila de aprovação de platinas/runs.",
            "como_ver_platinas": "Abra `/coliseu` e entre em **Platinas** para consultar as conquistas aprovadas, seu perfil e o ranking. Você também pode perguntar à Nara **minhas platinas** para consultar seus próprios registros pelo banco, sem IA.",
            "como_ver_zerados": "Use `/zerados` ou abra `/coliseu` e escolha **Zerados**. Para consultar seus próprios registros, pergunte **meus jogos zerados**; a Nara consulta o banco sem Gemini.",
            "como_ver_runs": "Abra `/coliseu` e escolha **Runs** para consultar a Central Soulslike. Você também pode perguntar **minhas runs** para ver a contagem de registros aprovados.",
            "perfil_outro_membro": "Abra `/coliseu` e use o menu de membros para escolher outra pessoa e consultar o perfil público, como patente, nível, XP e estatísticas de jogo. Saldo e inventário continuam privados.",
            "como_registrar_run": "Abra `/coliseu` e entre em **Runs**. Informe jogo, desafio, tempo, build e comprovante. A run fica pendente até a moderação revisar.",
            "como_comprovante": "Os prints não são analisados pela conversa da Nara. Para comprovar platina ou run, abra `/coliseu` e envie o arquivo no formulário específico; a moderação revisa o registro.",
            "como_buscar_jogo": "Use `/jogo_buscar` e informe o nome do jogo, mesmo que seja uma abreviação. O comando procura primeiro no catálogo já existente. Se não encontrar, usa pesquisa com fontes para sugerir o título oficial; você confirma o candidato e o catálogo fica em revisão, sem publicação automática.",
            "privacidade": "Seu saldo de Denários e seu inventário são privados e só são consultados para você. Rankings são públicos e mostram posição/estatísticas de jogo, não seu saldo ou inventário.",
            "como_chamar_nara": "Marque meu usuário com @Nara ou responda a uma mensagem minha. Nos canais configurados para dúvidas, também respondo a perguntas frequentes reconhecidas localmente. Conversas comuns não são enviadas ao Gemini.",
            "loja": "A loja usa Denários e vende apenas itens cosméticos, como cores de perfil e títulos. Use `/loja` para consultar itens, preços e requisitos de nível. Comprar/equipar não aumenta atributos nem XP.",
            "patentes": "As patentes são definidas pelo seu nível e podem conceder cargos automáticos. Seu nível depende do XP acumulado. Consulte `/nivel` para ver seu progresso atual.",
            "coliseu": "O `/coliseu` é o painel central: reúne Platinas, Zerados, Runs Soulslike, rankings, santuários e desafios. Os registros com comprovante passam por revisão da moderação.",
            "santuario": "O Santuário é seu espaço de perfil pessoal, com bio, banner, redes e galeria de platinas. Abra `/coliseu` e escolha a área de Santuário para criar ou visitar.",
            "rankings": "O Soulsbot possui rankings de XP, platinas, zerados e resultados Soulslike. Use `/ranking-xp` para o ranking de XP ou abra `/coliseu` para os demais painéis.",
            "youtube": "O bot publica avisos de vídeos novos e lives do canal configurado. Para receber alertas, confira os cargos de aviso disponíveis no painel de cargos.",
            "ofertas": "O módulo de ofertas verifica promoções e jogos gratuitos de lojas configuradas, como Steam, Epic e GOG. Os avisos aparecem no canal de ofertas do servidor.",
            "regras": "Respeite as regras do servidor, não tente fraudar comprovantes ou rankings e use os formulários oficiais para registros. A moderação decide aprovações e pode rejeitar registros inválidos.",
            "recompensas": "As recompensas são consultadas da configuração atual do servidor. Platinas aprovadas concedem XP e Denários; registros de jogos zerados também podem conceder recompensas. Consulte `/coliseu` para os registros e `/loja` para gastar Denários.",
            "agradecimento": random.choice(["Disponha. Guarde o agradecimento; Denários seriam mais úteis. 😏", "Por nada. Trabalho bem feito não precisa de cerimônia — mas aceito elogios.", "Tamo junto. Só não transforme isso em uma quest secundária."]),
            "despedida": "Até mais. Que sua próxima tentativa tenha menos mortes desnecessárias.",
            "como_esta": "Operacional e sem gastar quota do Gemini nesta conversa. Você está bem?",
            "provocacao": "Anotado. Quando terminar de testar minha paciência, posso ajudar com seu perfil ou com os sistemas do servidor.",
            "status": "Estou online se esta mensagem chegou até mim. As respostas básicas funcionam localmente; pesquisas avançadas dependem da disponibilidade da API externa.",
            "piada": random.choice(["Um jogador Soulslike entrou numa reunião. Morreu três vezes antes de encontrar o botão de sair.", "Qual é o chefe mais pontual? O que sempre chega na segunda fase.", "Minha build favorita? Defesa alta contra perguntas sem contexto." ]),
            "motivacao": random.choice(["Você não precisa vencer o chefe inteiro hoje. Só precisa aprender o padrão do próximo golpe.", "Progresso não é ausência de mortes; é voltar sabendo mais do que antes.", "Uma tentativa ruim ainda é informação. Use-a na próxima." ]),
            "criador": "Fui configurada como assistente do Soulsbot. Minha identidade, regras e personalidade vêm das instruções e dos sistemas definidos para este servidor.",
            "sem_visao": "Não. A Nara não recebe nem analisa prints nesta conversa. Para comprovantes, use os formulários próprios em `/coliseu`.",
            "faq_geral": "Consigo responder dúvidas sobre XP, Denários, patentes, platinas, zerados, runs, loja e painéis sem chamar o Gemini. Diga qual sistema quer consultar.",
        }
        if intent in respostas:
            return respostas[intent]
        if intent == "como_ganhar_xp":
            from cogs.progressao import XP_MENSAGEM_MIN, XP_MENSAGEM_MAX, XP_VOZ_POR_INTERVALO
            import config
            return (f"Mensagens válidas rendem **{XP_MENSAGEM_MIN}–{XP_MENSAGEM_MAX} XP**, respeitando o intervalo de 60 segundos. "
                    f"Voz rende **{XP_VOZ_POR_INTERVALO} XP a cada 5 minutos** com pelo menos duas pessoas. "
                    f"Platina aprovada: **{config.XP_PLATINA} XP**; jogo zerado registrado: **{config.XP_ZERADO} XP**. "
                    "Runs aprovadas também concedem XP conforme as regras da Central Soulslike.")
        if intent == "como_ganhar_denarios":
            import config
            return (f"Denários são a moeda cosmética do Soulsbot. Platina aprovada: **{config.DENARIOS_PLATINA} Denários**; "
                    f"jogo zerado registrado: **{config.DENARIOS_ZERADO} Denários**. Use `/loja` para gastar em cores e títulos.")
        if intent == "recompensas":
            import config
            from cogs.progressao import XP_MENSAGEM_MIN, XP_MENSAGEM_MAX
            return (f"Uma platina aprovada concede **{config.XP_PLATINA} XP** e **{config.DENARIOS_PLATINA} Denários**. "
                    f"Um jogo zerado registrado pode conceder **{config.XP_ZERADO} XP** e **{config.DENARIOS_ZERADO} Denários**. "
                    f"Mensagens válidas concedem {XP_MENSAGEM_MIN}–{XP_MENSAGEM_MAX} XP conforme o intervalo do sistema. "
                    "Runs têm regras próprias na Central Soulslike.")

        user = await db.get_user(autor.id)
        xp = int(user["xp"] or 0)
        nivel = nivel_por_xp(xp)
        if intent in {"meu_perfil", "meu_saldo", "minhas_platinas", "meus_zerados", "minhas_runs", "meu_inventario"}:
            platinas = await db.contar_platinas(autor.id)
            zerados = await db.contar_zerados(autor.id)
            runs_row = await db._one("SELECT COUNT(*) AS total FROM sl_runs WHERE user_id=? AND status='approved'", (autor.id,))
            runs = int(runs_row["total"] if runs_row else 0)
            if intent == "meu_saldo":
                return f"Seu saldo é **{int(user['denarios'] or 0)} Denários**. Consulte `/loja` para ver os itens disponíveis."
            if intent == "minhas_platinas":
                rows = await db.platinas_do_usuario(autor.id)
                lista = "\n".join(f"• {r['game']} ({r['platform']})" for r in rows[:10]) or "Nenhuma platina aprovada ainda."
                return f"Você tem **{platinas} platina(s) aprovada(s)**.\n{lista}"
            if intent == "meus_zerados":
                rows = await db.zerados_do_usuario(autor.id)
                lista = "\n".join(f"• {r['game']} ({r['platform']})" for r in rows[:10]) or "Nenhum jogo zerado registrado ainda."
                return f"Você tem **{zerados} jogo(s) zerado(s)** registrado(s).\n{lista}"
            if intent == "minhas_runs":
                return f"Você tem **{runs} run(s) aprovada(s)** na Central Soulslike. Abra `/coliseu` para consultar seus registros e desafios."
            if intent == "meu_inventario":
                import loja
                rows = await db.inventario_do_usuario(autor.id)
                if not rows:
                    return "Seu inventário cosmético está vazio. Consulte `/loja` para ver cores e títulos disponíveis."
                itens = []
                for row in rows[:15]:
                    item = loja.POR_ID.get(row["item"])
                    nome = item.nome if item else row["item"]
                    estado = "equipado" if row["equipado"] else "guardado"
                    itens.append(f"• {nome} — {estado}")
                return "**Seu inventário:**\n" + "\n".join(itens)
            from levels import barra_progresso, xp_para_nivel
            prox = xp_para_nivel(nivel + 1) - xp
            posicao = await db.posicao_xp(xp)
            return (f"**Perfil de {autor.display_name}**\nNível **{nivel}** — {patente_por_nivel(nivel)}\n"
                    f"XP: **{xp}** ({barra_progresso(xp)})\nPróximo nível: **{max(0, prox)} XP**\n"
                    f"Denários: **{int(user['denarios'] or 0)}**\nPlatinas: **{platinas}** · Zerados: **{zerados}** · Runs: **{runs}**\n"
                    f"Posição no ranking XP: **#{posicao}**")

        if intent in {"ranking_xp", "ranking_platinas", "ranking_zerados"}:
            getters = {
                "ranking_xp": (db.ranking_xp, "XP"),
                "ranking_platinas": (db.ranking_platinas, "platinas"),
                "ranking_zerados": (db.ranking_zerados, "jogos zerados"),
            }
            getter, label = getters[intent]
            rows = await getter(10)
            if not rows:
                return f"Ainda não há registros suficientes para montar o ranking de {label}."
            linhas = []
            for i, row in enumerate(rows, 1):
                membro = guild.get_member(int(row["user_id"])) if guild else None
                nome = membro.display_name if membro else f"Membro {str(row['user_id'])[-4:]}"
                linhas.append(f"**{i}.** {nome} — {int(row['valor'])} {label}")
            return f"**Top {label}:**\n" + "\n".join(linhas)

        return resposta_local_fallback(message.clean_content)

    # ---- gatilho
    def _foi_marcado(self, message: discord.Message) -> bool:
        if self.bot.user in message.mentions and not message.mention_everyone:
            return True
        ref = message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved.author.id == self.bot.user.id
        return False

    def _auditoria(self, autor_id: int):
        async def gravar(acao: str, detalhes: str):
            await self.bot.db.log(autor_id, acao, detalhes[:500])
        return gravar

    async def _responder_ia(self, message: discord.Message) -> tuple[str, Ctx]:
        """Único caminho de chat com IA: pesquisa somente textual em fontes autorizadas."""
        pergunta = (message.clean_content or "").strip()
        # Não envia histórico, perfil, saldo, inventário, prints ou anexos.
        conteudo = f"Pedido de pesquisa factual sobre Elden Ring (texto digitado):\n{pergunta}"

        eh_mod = await eh_moderador(message.author, self.bot.db)
        ctx = Ctx(
            bot=self.bot, guild=message.guild, autor=message.author, canal=message.channel, eh_mod=eh_mod,
            modo="marcado",
            mencionados={},
            auditoria=self._auditoria(message.author.id),
        )
        registro = criar_registro(self.bot, pesquisa=True, acoes_mod=False)
        # Pesquisa em chat fica estritamente limitada a ferramentas de leitura.
        registro = Registro([f for f in registro.ferramentas.values() if f.risco is Risco.LEITURA])

        gerar = self.ia.criar_gerador(self.prompt_pesquisa, registro)
        texto = await rodar_agente(gerar, self.ia, conteudo, registro, ctx)
        return (texto or "Não consegui concluir a pesquisa.").strip(), ctx

    def _montar_resposta(self, texto: str, ctx: Ctx, autor_id: int):
        """Texto final + botões. O resumo da ação vem do CÓDIGO, não do modelo, para o membro ver o que vai acontecer."""
        view = None
        if ctx.pendentes:
            pend = ctx.pendentes[0]
            extra = f"\n\n📝 **Ação preparada** — {pend.resumo}"
            texto = texto[:max(0, 1900 - len(extra))] + extra
            view = ConfirmarAcaoView(self.bot, pend)
        elif ctx.atalhos:
            view = AtalhoView(self.bot, autor_id, ctx.atalhos)
        return texto[:1900], view

    async def _enviar(self, message: discord.Message, texto: str, ctx: Ctx):
        texto, view = self._montar_resposta(texto, ctx, message.author.id)
        enviada = await message.reply(texto, allowed_mentions=discord.AllowedMentions.none(), view=view)
        if isinstance(view, ConfirmarAcaoView):
            view.message = enviada
        return enviada

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # A rota local independe das chaves de IA e permanece ativa quando qualquer quota acaba.
        if message.author.bot or message.guild is None:
            return
        foi_marcado = self._foi_marcado(message)
        canal_livre = message.channel.id in IA_CANAIS_LIVRES
        sem_mencao = discord.AllowedMentions.none()
        conteudo_usuario = (message.clean_content or "").strip()
        if self.bot.user:
            conteudo_usuario = conteudo_usuario.replace(f"@{self.bot.user.display_name}", "").strip()
        tem_imagem = tem_anexo_visual(message.attachments)
        rota, intent = decidir_rota(
            conteudo_usuario,
            direcionada=foi_marcado,
            canal_livre=canal_livre,
            tem_imagem=tem_imagem,
        )
        rota = aplicar_politica_de_quota(rota, chat_ia_ativa=NARA_CHAT_IA_ENABLED)

        if rota == "ignorar":
            return
        if rota == "recusar_imagem":
            return await message.reply(
                "Não analiso prints nem imagens nesta conversa. Para comprovantes de platina/run, "
                "envie o arquivo pelo formulário específico em `/coliseu`; a moderação faz a revisão.",
                allowed_mentions=sem_mencao,
            )
        if rota == "local":
            try:
                texto = await self._responder_local(message, intent)
            except Exception:
                log.exception("Falha em uma resposta local da Nara (intenção=%s)", intent)
                texto = "Consigo responder sem IA, mas falhei ao consultar esse dado agora. Tente novamente."
            if tem_imagem:
                texto += "\n\n_Não abri nem analisei o anexo; respondi apenas ao texto._"
            return await message.reply(texto[:1900], allowed_mentions=sem_mencao)
        if rota == "pedir_mencao":
            texto = (
                "Essa pergunta precisa de pesquisa com fontes. Me marque na mensagem ou use `/jogo_buscar` "
                "para identificar o jogo e preparar o catálogo. Não consumo quota automaticamente no canal."
            )
            if tem_imagem:
                texto += "\n\n_Não abri nem analisei o print; considerei somente o texto._"
            return await message.reply(texto, allowed_mentions=sem_mencao)
        if rota == "catalogo":
            texto = (
                "Para pesquisar **jogos, troféus, platinas, DLCs e colecionáveis**, use `/jogo_buscar` "
                "com o nome do jogo. O comando procura primeiro no catálogo local; se não encontrar, "
                "usa a pesquisa com fontes, pede sua confirmação do título e cria um rascunho para revisão. "
                "Assim a quota só é usada quando realmente precisamos pesquisar um catálogo."
            )
            if tem_imagem:
                texto += "\n\n_Não abri nem analisei o print; considerei somente o texto._"
            return await message.reply(texto, allowed_mentions=sem_mencao)
        if rota == "pesquisa_chat_desativada":
            texto = (
                "Desativei a pesquisa conversacional para preservar a quota. Não vou chamar o Gemini para guias ou perguntas abertas no chat. "
                "Para pesquisar jogos, troféus, platinas, DLCs e colecionáveis, use `/jogo_buscar`; ele consulta primeiro o catálogo local "
                "e só chama a pesquisa externa quando não encontra dados existentes."
            )
            if tem_imagem:
                texto += "\n\n_Não abri nem analisei o print; considerei somente o texto._"
            return await message.reply(texto, allowed_mentions=sem_mencao)
        if rota == "pesquisa_nao_suportada":
            texto = (
                "Não vou inventar uma pesquisa: no chat, minhas fontes automáticas estão configuradas para "
                "Elden Ring. Para catálogo de troféus/platinas de outros jogos, use `/jogo_buscar`."
            )
            if tem_imagem:
                texto += "\n\n_Não abri nem analisei o print; considerei somente o texto._"
            return await message.reply(texto, allowed_mentions=sem_mencao)
        if rota == "fallback":
            texto = resposta_local_fallback(conteudo_usuario)
            if tem_imagem:
                texto += "\n\n_Não abri nem analisei o anexo; considerei somente o texto._"
            return await message.reply(texto[:1900], allowed_mentions=sem_mencao)

        # Única rota de chat que consome IA externa: pesquisa factual explicitamente solicitada.
        if self.ia is None:
            return await message.reply(
                "A pesquisa avançada está indisponível porque nenhum provedor de IA foi configurado. "
                "As respostas básicas e consultas do servidor continuam funcionando localmente.",
                allowed_mentions=sem_mencao,
            )

        agora = time.monotonic()
        if agora - self.ultimo_uso.get(message.author.id, 0) < COOLDOWN_SEG:
            return
        self.ultimo_uso[message.author.id] = agora
        if not await self._pode_usar(message.author.id):
            return await message.reply("Você já usou suas consultas avançadas de hoje. Volte amanhã.",
                                       allowed_mentions=sem_mencao)

        ctx = None
        async with message.channel.typing():
            try:
                texto, ctx = await self._responder_ia(message)
                await self._registrar_uso(message.author.id)
            except (GeminiUnavailableError, DeepSeekUnavailableError) as exc:
                log.warning("Pesquisa da Nara falhou no provedor: %s", getattr(exc, "admin_message", str(exc)))
                texto = getattr(exc, "user_message", str(exc))
            except TodosProvedoresIndisponiveis as exc:
                log.error("Todos os provedores da Nara indisponíveis: %s", exc.admin_message)
                texto = exc.user_message
            except Exception:
                log.exception("Falha na pesquisa da Nara")
                texto = "A pesquisa falhou. As respostas locais continuam disponíveis; tente novamente mais tarde."
        if tem_imagem:
            texto += "\n\n_Não abri nem analisei o anexo; usei somente o texto digitado._"
        if ctx is None:
            return await message.reply(texto[:1900], allowed_mentions=sem_mencao)
        return await self._enviar(message, texto, ctx)

    @discord.app_commands.command(name="gemini_status", description="Mostra o estado dos provedores de IA (admin).")
    @discord.app_commands.default_permissions(manage_guild=True)
    async def gemini_status_command(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Você precisa de Gerenciar servidor.", ephemeral=True)
        states = {"deepseek": deepseek_status(), "gemini": gemini_status()}
        labels = []
        for name, state in states.items():
            if state["blocked"]:
                mins = max(1, (state["remaining_seconds"] + 59) // 60)
                labels.append(
                    f"**{name.title()}: PAUSADO** — {state['kind']}, cerca de {mins} min. "
                    f"Motivo: `{(state['reason'] or 'não informado')[:220]}`"
                )
            else:
                labels.append(f"**{name.title()}: disponível no circuito local** (isso não garante quota/saldo no provedor).")
        configured = []
        if DEEPSEEK_API_KEY:
            configured.append(f"DeepSeek (`{DEEPSEEK_MODEL}`)")
        if GEMINI_API_KEY:
            configured.append(f"Gemini (`{GEMINI_MODEL}`)")
        body = (
            f"**Provedor principal:** `{os.getenv('AI_PRIMARY_PROVIDER', 'deepseek')}`\n"
            f"**Chaves configuradas:** {', '.join(configured) if configured else 'nenhuma'}\n\n"
            + "\n".join(labels)
            + "\n\nO roteador tenta o principal primeiro e usa o outro como reserva quando detecta quota, rate limit ou indisponibilidade."
        )
        await interaction.response.send_message(body[:1900], ephemeral=True)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # Menções ao bot usam o prefixo "@bot"; sem isso o discord.py logaria CommandNotFound.
        if isinstance(error, commands.CommandNotFound):
            return
        log.error("Erro de comando de prefixo", exc_info=error)


async def setup(bot):
    await bot.add_cog(NaraIA(bot))
