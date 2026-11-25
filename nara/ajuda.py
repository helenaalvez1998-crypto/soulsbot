"""Painéis privados de ajuda e diretório de comandos do NARA."""
from __future__ import annotations

import discord


# Ordem pensada pelo percurso do membro: começar, progredir, jogar e só depois
# chegar aos assuntos de servidor, integrações e administração.
FAQ_CATEGORIA_ORDEM = (
    "Platinas e conquistas",
    "Jogos zerados",
    "Runs e desafios",
    "XP e patentes",
    "Perfis e rankings",
    "Perfis e Santuários",
    "Loja e Denários",
    "Servidor, cargos e painéis",
    "YouTube e ofertas",
    "Administração e Nara",
    "IA e funcionamento",
)

FAQ_CATEGORIA_LABEL = {
    "Administração e Nara": "Sobre a NARA",
    "IA e funcionamento": "Privacidade e recursos",
}

FAQ_CATEGORIA_EMOJI = {
    "Platinas e conquistas": "🏆",
    "Jogos zerados": "✅",
    "Runs e desafios": "⚔️",
    "XP e patentes": "📈",
    "Perfis e rankings": "👤",
    "Perfis e Santuários": "🏛️",
    "Loja e Denários": "🪙",
    "Servidor, cargos e painéis": "🛠️",
    "YouTube e ofertas": "📡",
    "Administração e Nara": "🤖",
    "IA e funcionamento": "🔒",
}

FAQ_CATEGORIA_DESCRICAO = {
    "Platinas e conquistas": "Registrar, comprovar e consultar platinas",
    "Jogos zerados": "Registrar jogos concluídos e corrigir registros",
    "Runs e desafios": "Enviar runs, tempos e comprovantes",
    "XP e patentes": "Experiência, níveis, patentes e recompensas",
    "Perfis e rankings": "Perfis, estatísticas e classificações",
    "Perfis e Santuários": "Seu espaço pessoal e visitas a outros membros",
    "Loja e Denários": "Saldo, itens cosméticos e compras",
    "Servidor, cargos e painéis": "Cargos, verificações e painéis públicos",
    "YouTube e ofertas": "Avisos de vídeos, lives e promoções",
    "Administração e Nara": "Quem sou, como me chamar e como posso ajudar",
    "IA e funcionamento": "Memória, privacidade e recursos disponíveis para você",
}


# Diretório de referência: os recursos dos membros ficam no /nara; comandos de moderação/admin permanecem separados.
COMANDOS_SECOES = (
    {
        "key": "inicio", "label": "Comece por aqui", "emoji": "🎮",
        "description": "Os dois pontos de entrada da NARA", "title": "🌙 Comece por aqui",
        "intro": "A NARA possui dois comandos slash principais. O restante é acessado pelos painéis interativos — menos comandos para decorar, mais tempo para jogar.",
        "fields": (
            ("Central do membro", "`/nara` — abre seu painel privado com Ports & Mods, biblioteca, perfil, Santuário, progresso, Loja, comunidade e ajuda."),
            ("Central administrativa", "`/adm` — abre o painel restrito à equipe para moderação, configuração, auditoria, Ports & Mods e Radar de Games."),
            ("Navegação", "Use botões, menus e formulários dentro dos painéis. Não é necessário decorar comandos individuais."),
        ),
    },
    {
        "key": "membros", "label": "Painel do membro", "emoji": "👤",
        "description": "Recursos pessoais e comunidade", "title": "👤 Painel do membro",
        "intro": "Abra `/nara` e escolha uma categoria. Eu organizo a rota; suas consultas pessoais continuam privadas.",
        "fields": (
            ("Jogos e conquistas", "Acesse Coliseu, Platinas, Zerados, Runs e desafios."),
            ("Biblioteca", "Consulte seus jogos concluídos, platinas e runs. Para descobrir conteúdo comunitário, acesse Ports & Mods."),
            ("Progresso e recompensas", "Consulte nível, XP, patente, ranking e Loja de Denários."),
        ),
    },
    {
        "key": "perfil", "label": "Perfil e Santuário", "emoji": "🏛️",
        "description": "Identidade e evolução pessoal", "title": "🏛️ Perfil e Santuário",
        "intro": "Os recursos pessoais ficam na central `/nara`. Seu espaço, suas estatísticas e suas escolhas — cada coisa no seu devido lugar.",
        "fields": (
            ("Meu perfil", "Consulte patente, nível, XP, Denários, platinas, jogos zerados e posições nos rankings."),
            ("Meu Santuário", "Abra e personalize seu espaço pessoal e sua galeria, conforme os recursos habilitados no servidor."),
            ("Privacidade", "Os painéis pessoais são vinculados ao membro que os abriu."),
        ),
    },
    {
        "key": "catalogos", "label": "Ports & Mods", "emoji": "🎮",
        "description": "Ports e modificações da comunidade", "title": "🎮 Ports & Mods",
        "intro": "Acesse **Ports & Mods** dentro de `/nara`. Explore ports por plataforma e consulte os detalhes e links disponíveis. Sugestões passam pela revisão da equipe.",
        "fields": (
            ("Catálogo de ports", "Explore capas, filtre pela plataforma indicada, pesquise ports e consulte detalhes, links de download, ISO original e tutoriais quando disponíveis."),
            ("Catálogo de mods", "Explore mods associados aos ports, consulte imagens, descrições e links."),
            ("Envios da comunidade", "Envie ports e mods para revisão. Eles só aparecem publicamente após aprovação da equipe."),
        ),
    },
    {
        "key": "economia", "label": "Economia e coleção", "emoji": "🪙",
        "description": "Denários, loja e itens", "title": "🪙 Economia e coleção",
        "intro": "A economia da NARA fica no painel `/nara`. Confira preço e requisito antes de gastar; até uma estrategista respeita o orçamento.",
        "fields": (
            ("Loja", "Consulte itens cosméticos e recompensas disponíveis e faça compras com Denários."),
            ("Experiência", "Acompanhe XP, níveis, patentes e rankings."),
        ),
    },
    {
        "key": "moderacao", "label": "Moderação", "emoji": "🛡️",
        "description": "Fila de revisão e decisões", "title": "🛡️ Moderação",
        "intro": "A equipe autorizada acessa a central pelo `/adm`. Nesta área, precisão e evidência vêm antes de qualquer espetáculo.",
        "fields": (
            ("Solicitações da NARA", "Revise Platinas, Runs/Desafios e Jogos Zerados na Central de Moderação."),
            ("Envios de catálogo", "Aprove ou rejeite ports e mods enviados pelos membros, preservando o fluxo de revisão."),
            ("Auditoria", "Consulte histórico e indicadores operacionais disponíveis no painel administrativo."),
        ),
    },
    {
        "key": "administracao", "label": "Administração", "emoji": "⚙️",
        "description": "Configurações e sistemas", "title": "⚙️ Administração",
        "intro": "As configurações da equipe ficam no `/adm`, organizadas por categoria. Use a opção correta e não transforme um ajuste simples numa expedição.",
        "fields": (
            ("Servidor e sistemas", "Configure canais, cargos, personalização e sistemas comunitários conforme suas permissões."),
            ("Ports & Mods", "Gerencie ports e mods, revise envios e configure notificações de moderação."),
            ("Radar de Games", "Escolha o canal de notícias, cadastre feeds RSS, consulte fontes e envie uma publicação de teste."),
        ),
    },
    {
        "key": "integracoes", "label": "Integrações", "emoji": "📡",
        "description": "Notícias, YouTube e ofertas", "title": "📡 Integrações",
        "intro": "As integrações administrativas são gerenciadas pelo `/adm`. Se um aviso falhar, confira a configuração antes de culpar os cabos invisíveis.",
        "fields": (
            ("Radar de Games", "Monitora fontes RSS e publica anúncios e lançamentos relevantes no canal configurado."),
            ("Outras integrações", "O painel administrativo também permite consultar o estado das integrações existentes da NARA."),
        ),
    },
    {
        "key": "suporte", "label": "Ajuda e suporte", "emoji": "❔",
        "description": "Como encontrar qualquer recurso", "title": "❔ Ajuda e suporte",
        "intro": "Se não encontrar uma função, comece pelo painel correto. Eu mostro o caminho; telepatia ainda não entrou no pacote.",
        "fields": (
            ("Membros", "Use `/nara` e navegue pelas categorias, botões e guias."),
            ("Equipe", "Use `/adm` para abrir as ferramentas administrativas. Acesso depende das permissões e cargos configurados."),
            ("Dúvidas", "Abra a Central de Ajuda dentro do painel do membro para consultar orientações."),
        ),
    },
)


class AjudaCategoriaSelect(discord.ui.Select):
    def __init__(self, bot, callback_voltar=None):
        self.callback_voltar = callback_voltar
        from nara import faq as faq_base
        base = faq_base.carregar_base()
        disponiveis = {
            item.get("category", "Outros")
            for item in base["intents"] if (item.get("answer") or item.get("handler")) and not item.get("staff_only")
        }
        categorias = [cat for cat in FAQ_CATEGORIA_ORDEM if cat in disponiveis]
        categorias.extend(sorted(disponiveis - set(categorias) - set(FAQ_CATEGORIA_ORDEM)))
        options = [
            discord.SelectOption(
                label=FAQ_CATEGORIA_LABEL.get(cat, cat),
                value=cat,
                description=FAQ_CATEGORIA_DESCRICAO.get(cat, "Ver perguntas desta categoria")[:100],
                emoji=FAQ_CATEGORIA_EMOJI.get(cat, "📂"),
            )
            for cat in categorias[:25]
        ]
        super().__init__(placeholder="Escolha o assunto. Eu organizo a rota.", min_values=1, max_values=1, options=options)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        categoria = self.values[0]
        descricao = FAQ_CATEGORIA_DESCRICAO.get(categoria, "Escolha uma pergunta para ver a resposta.")
        await interaction.response.edit_message(
            embed=discord.Embed(
                title=f"Central de Ajuda · {categoria}",
                description=f"{descricao}.\n\n**2 · Escolha uma pergunta:** selecione o que você quer saber. Se ainda ficar alguma dúvida, me chama — prometo tentar não julgar. 😏",
                color=discord.Color.dark_teal(),
            ),
            view=AjudaPerguntasView(self.bot, categoria, callback_voltar=self.callback_voltar),
        )


class AjudaPerguntaSelect(discord.ui.Select):
    def __init__(self, bot, categoria: str, callback_voltar=None):
        self.callback_voltar = callback_voltar
        from nara import faq as faq_base
        base = faq_base.carregar_base()
        itens = [
            item for item in base["intents"]
            if item.get("category", "Outros") == categoria
            and (item.get("answer") or item.get("handler")) and not item.get("staff_only")
        ]
        itens.sort(key=lambda item: str(item.get("title", item.get("intent", ""))).casefold())
        intents = {item["intent"]: item for item in itens}
        options = [
            discord.SelectOption(
                label=item.get("title", intent)[:100],
                value=intent,
                description=(
                    "Mostra seus dados no servidor" if item.get("handler")
                    else " ".join(item.get("answer", "Resposta local").split())[:95]
                ),
            )
            for intent, item in list(intents.items())[:25]
        ]
        super().__init__(placeholder="Escolha a pergunta. Sem se perder no menu.", min_values=1, max_values=1, options=options)
        self.bot = bot
        self.categoria = categoria
        self.intents = intents

    async def callback(self, interaction: discord.Interaction):
        from nara import faq as faq_base
        item = self.intents[self.values[0]]
        resposta = faq_base.resposta_pronta(self.values[0])
        if not resposta and item.get("handler"):
            cog = self.bot.get_cog("NaraIA")
            if cog is None:
                resposta = "Ih, não consegui consultar isso agora. Tente mais uma vez daqui a pouco; não vou chutar seus dados."
            else:
                from types import SimpleNamespace
                mensagem = SimpleNamespace(
                    author=interaction.user,
                    guild=interaction.guild,
                    clean_content="",
                )
                try:
                    resposta = await cog._responder_local(mensagem, self.values[0])
                except Exception:
                    import logging
                    logging.getLogger("nara.help").exception(
                        "Falha em consulta dinâmica da Central de Ajuda: %s", self.values[0]
                    )
                    resposta = "Não consegui consultar esses dados agora. Tente novamente em instantes; prefiro admitir a falha a inventar seus números."
        resposta = resposta or "Essa resposta ainda não está cadastrada. Não vou improvisar uma regra só para preencher silêncio: consulte a equipe ou tente novamente mais tarde."
        embed = discord.Embed(
            title=item.get("title", "Resposta da Nara"),
            description=resposta[:4000],
            color=discord.Color.dark_teal(),
        )
        video_url = None
        if self.values[0] == "como_transmitir_discord":
            modulo = self.bot.get_cog("Transmissoes")
            if modulo is not None and interaction.guild_id is not None:
                video_url = await modulo.obter_video(interaction.guild_id)
        await interaction.response.edit_message(
            embed=embed, view=AjudaPerguntasView(
                self.bot, self.categoria, video_url=video_url, callback_voltar=self.callback_voltar
            )
        )


class AjudaVoltarButton(discord.ui.Button):
    def __init__(self, bot, callback_voltar=None):
        super().__init__(label="Categorias", emoji="↩️", style=discord.ButtonStyle.secondary, row=1)
        self.bot = bot
        self.callback_voltar = callback_voltar

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="Central de Ajuda da Nara",
                description="Escolha o assunto e depois a pergunta. Eu mostro o caminho — sem transformar um botão numa trilogia.",
                color=discord.Color.dark_teal(),
            ),
            view=CentralAjudaView(self.bot, callback_voltar=self.callback_voltar),
        )


class AbrirComandosButton(discord.ui.Button):
    def __init__(self, bot, callback_voltar=None):
        super().__init__(label="Ver índice de comandos", emoji="📚", style=discord.ButtonStyle.secondary, row=1)
        self.bot = bot
        self.callback_voltar = callback_voltar

    async def callback(self, interaction: discord.Interaction):
        view = ComandosEntradaView(self.bot, callback_voltar=self.callback_voltar)
        if self.callback_voltar is not None:
            await interaction.response.edit_message(embed=embed_inicio_comandos(), view=view)
        else:
            await interaction.response.send_message(embed=embed_inicio_comandos(), view=view, ephemeral=True)


class PainelAjudaPublicoView(discord.ui.View):
    """View persistente: o botão público abre a Central de Ajuda em modo privado."""
    def __init__(self, bot=None):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(PainelAjudaAbrirButton(bot))


class PainelAjudaAbrirButton(discord.ui.Button):
    def __init__(self, bot=None):
        super().__init__(
            label="Abrir Central de Ajuda",
            emoji="📚",
            style=discord.ButtonStyle.primary,
            custom_id="nara:central_ajuda:abrir:v1",
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message(
                "A Central de Ajuda funciona dentro do servidor. Aqui fora, nem meu alcance é ilimitado.", ephemeral=True
            )
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Central de Ajuda da Nara",
                description=(
                    "Escolha o assunto e depois a pergunta. Vou direto ao que interessa — "
                    "uma dúvida simples não precisa virar uma saga de 80 horas. 😏"
                ),
                color=discord.Color.dark_teal(),
            ),
            view=CentralAjudaView(self.bot),
            ephemeral=True,
        )


class CentralAjudaView(discord.ui.View):
    def __init__(self, bot, callback_voltar=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.callback_voltar = callback_voltar
        self.add_item(AjudaCategoriaSelect(bot, callback_voltar=callback_voltar))
        self.add_item(AbrirComandosButton(bot, callback_voltar=callback_voltar))
        if callback_voltar is not None:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, callback_voltar, label="Voltar à Nara", emoji="🏠")
        from cogs.comunidade import adicionar_botao_contribuicao_contextual
        adicionar_botao_contribuicao_contextual(
            self, "faq", "ajuda", "Sugerir pergunta ou resposta", "💡", row=2,
            style=discord.ButtonStyle.success,
        )


class AjudaPerguntasView(discord.ui.View):
    def __init__(self, bot, categoria: str, video_url: str | None = None, callback_voltar=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.callback_voltar = callback_voltar
        self.add_item(AjudaPerguntaSelect(bot, categoria, callback_voltar=callback_voltar))
        self.add_item(AjudaVoltarButton(bot, callback_voltar=callback_voltar))
        if callback_voltar is not None:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, callback_voltar, label="Voltar à Nara", emoji="🏠")
        if video_url:
            self.add_item(discord.ui.Button(
                label="Assistir ao vídeo tutorial", style=discord.ButtonStyle.link,
                url=video_url, emoji="▶️"
            ))
        from cogs.comunidade import adicionar_botao_contribuicao_contextual
        adicionar_botao_contribuicao_contextual(
            self, "faq", "ajuda", "Não encontrou? Sugerir resposta", "💡", row=2,
            style=discord.ButtonStyle.success,
        )


class AjudaAtalhoView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.bot = bot

    @discord.ui.button(label="Abrir painel de ajuda", emoji="📚", style=discord.ButtonStyle.primary)
    async def abrir(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Central de Ajuda da Nara",
                description="Escolha um assunto e depois a pergunta. Se não encontrar o que procura, me chama; eu procuro o caminho sem inventar resposta.",
                color=discord.Color.dark_teal(),
            ),
            view=CentralAjudaView(self.bot),
            ephemeral=True,
        )


class ComandosCategoriaSelect(discord.ui.Select):
    def __init__(self, bot=None, callback_voltar=None):
        self.callback_voltar = callback_voltar
        options = [
            discord.SelectOption(
                label=secao["label"], value=secao["key"],
                description=secao["description"][:100], emoji=secao["emoji"],
            )
            for secao in COMANDOS_SECOES
        ]
        super().__init__(placeholder="Escolha uma área. Eu cuido do mapa; você só precisa não se perder.", min_values=1, max_values=1, options=options)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        secao = next((item for item in COMANDOS_SECOES if item["key"] == self.values[0]), None)
        if secao is None:
            return await interaction.response.send_message("Essa área não está disponível neste momento. Volte à central `/nara` e tente por lá.", ephemeral=True)
        embed = discord.Embed(title=secao["title"], description=secao["intro"], color=discord.Color.dark_teal())
        for nome, valor in secao["fields"]:
            embed.add_field(name=nome, value=valor[:1024], inline=False)
        embed.set_footer(text="Índice do NARA · escolha outra área no menu ou use /nara para acessar a central")
        await interaction.response.edit_message(embed=embed, view=ComandosView(self.bot, callback_voltar=self.callback_voltar))


class ComandosFAQButton(discord.ui.Button):
    def __init__(self, bot=None, callback_voltar=None):
        super().__init__(label="Abrir FAQ da Nara", emoji="❓", style=discord.ButtonStyle.secondary, row=1)
        self.bot = bot
        self.callback_voltar = callback_voltar

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
                title="Central de Ajuda da Nara",
                description="Escolha um assunto e depois a pergunta. Se não encontrar o que procura, me chama; eu procuro o caminho sem inventar resposta.",
                color=discord.Color.dark_teal(),
            )
        view = CentralAjudaView(self.bot, callback_voltar=self.callback_voltar)
        if self.callback_voltar is not None:
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ComandosView(discord.ui.View):
    def __init__(self, bot=None, callback_voltar=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.callback_voltar = callback_voltar
        self.add_item(ComandosCategoriaSelect(bot, callback_voltar=callback_voltar))
        self.add_item(ComandosFAQButton(bot, callback_voltar=callback_voltar))
        if callback_voltar is not None:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, callback_voltar, label="Voltar à Nara", emoji="🏠")


def embed_inicio_comandos() -> discord.Embed:
    embed = discord.Embed(
        title="📚 Guia de comandos do NARA",
        description=(
            "Os comandos estão separados por função. Escolha uma área no menu abaixo para ver "
            "o que cada comando faz e a sequência recomendada.\n\n"
            "**Fluxo recomendado para jogadores**\n"
            "1. `/nara` — abra a central interativa dos membros.\n"
            "2. Escolha a categoria e use os botões para abrir os sistemas.\n"
            "3. Os painéis pessoais e formulários abrem de forma privada.\n\n"
            "Os comandos de moderação e administração continuam separados e identificados neste índice."
        ),
        color=discord.Color.dark_teal(),
    )
    embed.set_footer(text="Painel privado · não publica mensagens nos canais")
    return embed


class ComandosEntradaView(ComandosView):
    def __init__(self, bot=None, callback_voltar=None):
        super().__init__(bot=bot, callback_voltar=callback_voltar)


