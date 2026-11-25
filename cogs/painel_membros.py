"""Central interativa de acesso às funções dos membros da NARA."""
from __future__ import annotations

import asyncio
import discord
import logging
from discord import app_commands
from discord.ext import commands

import config
from levels import nivel_por_xp, patente_por_nivel, barra_progresso
from utils import adicionar_botao_voltar, view_so_com_voltar

log = logging.getLogger("cogs.painel_membros")


class FecharPainelNaraButton(discord.ui.Button):
    """Fecha apenas a interface efêmera atual, sem apagar dados ou cancelar registros."""

    def __init__(self, user_id: int, row: int = 4):
        super().__init__(label="Fechar painel", emoji="✖️", style=discord.ButtonStyle.secondary, row=row)
        self.user_id = int(user_id)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "Este painel pertence a outro membro. Abra `/nara` para acessar o seu.", ephemeral=True
            )
        await interaction.response.edit_message(
            content="Central fechada. Quando quiser voltar, use `/nara`.",
            embed=None,
            attachments=[],
            view=None,
        )


def adicionar_fechar_nara(view: discord.ui.View | None, user_id: int) -> discord.ui.View | None:
    """Adiciona um fechamento seguro sem remover controles funcionais existentes."""
    if view is None or any(isinstance(item, FecharPainelNaraButton) for item in view.children):
        return view
    if len(view.children) >= 25:
        return view
    try:
        view.add_item(FecharPainelNaraButton(user_id))
    except ValueError:
        # Uma linha pode estar cheia mesmo quando ainda há espaço global na View.
        try:
            view.add_item(FecharPainelNaraButton(user_id, row=3))
        except ValueError:
            log.debug("Não foi possível encaixar o botão Fechar sem deslocar controles existentes.")
    return view


async def _marcar_painel_nara_expirado(view: discord.ui.View) -> None:
    """Mantém a mensagem visível, desativa controles e informa como reabrir a central."""
    for item in view.children:
        if hasattr(item, "disabled"):
            item.disabled = True
    mensagem = getattr(view, "_nara_message", None)
    if mensagem is None:
        return
    try:
        embeds = getattr(mensagem, "embeds", []) or []
        if embeds:
            embed = embeds[0].copy()
            footer = embed.footer.text or "NARA"
            embed.set_footer(text=f"{footer} · Sessão encerrada; use /nara para reabrir"[:2048])
            await mensagem.edit(embed=embed, view=view)
        else:
            await mensagem.edit(content="Esta sessão terminou. Use `/nara` para abrir uma nova.", view=view)
    except (discord.HTTPException, AttributeError):
        log.debug("Não foi possível atualizar a mensagem expirada da Nara.", exc_info=True)


def _view_com_navegacao_nara(view: discord.ui.View, callback_voltar, user_id: int, mensagem=None):
    # Alguns painéis já possuem um botão de retorno próprio e contextual.
    # Evita duplicar a navegação e apresentar dois botões que parecem iguais.
    if callback_voltar is not None and not getattr(view, "_nara_has_return", False):
        adicionar_botao_voltar(view, callback_voltar)
    adicionar_fechar_nara(view, user_id)
    if mensagem is not None:
        view._nara_message = mensagem
    return view


class RemoverZeradoModal(discord.ui.Modal, title="Remover registro de jogo zerado"):
    def __init__(self, cog, callback_voltar=None):
        super().__init__(timeout=180)
        self.cog = cog
        self.callback_voltar = callback_voltar
        self.registro = discord.ui.TextInput(
            label="Número do registro",
            placeholder="Somente o número do registro (ex.: 12)",
            min_length=1,
            max_length=10,
        )
        self.add_item(self.registro)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            registro = int(self.registro.value.strip())
            if registro < 1:
                raise ValueError
        except ValueError:
            return await interaction.response.send_message("Digite somente o número positivo do registro (ex.: 12). Você encontra esse número na lista de jogos zerados.", ephemeral=True)
        await type(self.cog).remover_zerado.callback(self.cog, interaction, registro)


GUIA_MEMBROS = {
    "jogos": ("🎮 Começar pelos jogos", "**Minha biblioteca:** registre e consulte platinas, zerados e runs.\n**Meus registros:** acompanhe aprovações e corrija envios rejeitados.\n**Ports & Mods:** explore o catálogo da comunidade."),
    "coliseu": ("⚔️ Como funciona o Coliseu", "Use **Cartas do Coliseu** no painel de Jogos ou o comando `/jogo` para abrir sua coleção e consultar seu deck, drops e estatísticas. As conquistas de platinas, zerados e runs ficam em **Conquistas e jornadas**."),
    "progresso": ("🏆 Progresso e recompensas", "Consulte nível, patente, XP e ranking. Os Denários ficam na carteira e podem ser usados na loja e nos pacotes do Coliseu."),
    "comunidade": ("📡 Participar da comunidade", "Envie lore, teorias, descobertas, guias e propostas. Acompanhe o estado de cada contribuição e responda a pedidos de ajuste."),
}


class GuiaMembrosSelect(discord.ui.Select):
    def __init__(self, bot, user_id: int):
        self.bot = bot
        self.user_id = int(user_id)
        super().__init__(
            placeholder="Não sabe por onde começar? Escolha um guia...",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="Começar pelos jogos", value="jogos", description="Biblioteca, conquistas e registros", emoji="🎮"),
                discord.SelectOption(label="Entender o Coliseu", value="coliseu", description="Deck, cartas e desafios", emoji="⚔️"),
                discord.SelectOption(label="Progresso e recompensas", value="progresso", description="Nível, XP, Denários e loja", emoji="🏆"),
                discord.SelectOption(label="Participar da comunidade", value="comunidade", description="Contribuições e arquivo", emoji="📡"),
            ],
            row=3,
        )

    async def callback(self, interaction: discord.Interaction):
        titulo, descricao = GUIA_MEMBROS[self.values[0]]
        embed = discord.Embed(title=titulo, description=descricao, color=config.COR_OURO)
        embed.set_footer(text="NARA • Orientação rápida · Voltar à central")
        callback = _retorno_categoria_membro(self.bot, self.user_id, "__inicio__")
        view = _view_com_navegacao_nara(view_so_com_voltar(callback), callback, self.user_id, interaction.message)
        await interaction.response.edit_message(embed=embed, view=view)



MEMBROS_CATEGORIAS = {
    "jogos": {
        "titulo": "🎮 Jogos e biblioteca",
        "descricao": "Acesse seus registros de platinas, jogos zerados, Runs e desafios. Consulte o que já foi aprovado, acompanhe pendências e explore os catálogos.",
        "acoes": [
            ("cartas_coliseu", "Cartas do Coliseu", "🃏", discord.ButtonStyle.primary),
            ("coliseu", "Conquistas e jornadas", "🏛️", discord.ButtonStyle.primary),
            ("zerados", "Jogos zerados", "✅", discord.ButtonStyle.success),
            ("meus_registros", "Meus registros", "📬", discord.ButtonStyle.secondary),
            ("catalogos", "Ports & Mods", "🎮", discord.ButtonStyle.primary),
            ("luatools", "LuaTools — Steam", "🕹️", discord.ButtonStyle.success),
            ("remover_zerado", "Remover jogo zerado", "🗑️", discord.ButtonStyle.secondary),
        ],
    },
    "progresso": {
        "titulo": "🏆 Meu progresso e recompensas",
        "descricao": "Veja sua patente, nível, XP e ranking. Use Denários na loja e nos recursos do Coliseu.",
        "acoes": [
            ("nivel", "Meu nível e XP", "🛡️", discord.ButtonStyle.primary),
            ("ranking_xp", "Ranking de XP", "🏆", discord.ButtonStyle.secondary),
            ("loja", "Loja de recompensas", "🪙", discord.ButtonStyle.success),
        ],
    },
    "preferencias": {
        "titulo": "🧠 Minhas preferências",
        "descricao": "Ajuste como a Nara conversa com você e escolha quais avisos deseja receber.",
        "acoes": [
            ("memoria", "Memória da Nara", "🧠", discord.ButtonStyle.secondary),
            ("notificacoes", "Notificações", "🔔", discord.ButtonStyle.primary),
        ],
    },
    "ajuda": {
        "titulo": "❔ Ajuda e suporte",
        "descricao": "Encontre orientações rápidas e suporte para usar os recursos do NARABOT.",
        "acoes": [
            ("ajuda", "Central de ajuda", "📖", discord.ButtonStyle.primary),
            ("tutorial_transmissao", "Como transmitir a tela", "📺", discord.ButtonStyle.success),
        ],
    },
    "comunidade": {
        "titulo": "📡 Comunidade e contribuições",
        "descricao": "Envie ideias, acompanhe suas propostas, explore o Arquivo de Mundos e gerencie favoritos.",
        "acoes": [
            ("community_home", "Central de contribuições", "💡", discord.ButtonStyle.primary),
            ("community_archive", "Arquivo de Mundos", "📚", discord.ButtonStyle.secondary),
            ("community_mine", "Minhas contribuições", "🗂️", discord.ButtonStyle.secondary),
        ],
    },
}


def _embed_categoria_membro(categoria: str) -> discord.Embed:
    dados = MEMBROS_CATEGORIAS[categoria]
    embed = discord.Embed(
        title=dados["titulo"],
        description=dados["descricao"] + "\n\nEscolha uma opção. Você pode voltar à central a qualquer momento.",
        color=config.COR_OURO,
    )
    embed.set_footer(text="NARA • Painel privado · Voltar à central a qualquer momento")
    return embed


async def _montar_embed_central_nara(bot: commands.Bot, user_id: int):
    """Monta a central inicial sem consultar nem renderizar o deck do membro."""
    db = bot.db
    resumo = await db.resumo_painel_nara(int(user_id))
    xp = resumo["xp"]
    nivel_atual = nivel_por_xp(xp)

    embed = discord.Embed(
        title="🌙 NARA — SUA CENTRAL",
        description=(
            "Sua jornada em um só lugar. Consulte seu progresso, veja seu deck, acompanhe registros e ajuste avisos sem precisar memorizar comandos. Os painéis são privados e você pode voltar ou fechar quando quiser."
        ),
        color=config.COR_OURO,
    )
    embed.add_field(
        name="🛡️ Seu progresso",
        value=(
            f"**Nível {nivel_atual} · {patente_por_nivel(nivel_atual)}**\\n"
            f"{barra_progresso(xp)}\\n"
            f"🏆 {resumo['platinas']} platinas · ✅ {resumo['zerados']} zerados · ⚔️ {resumo['runs']} runs"
        ),
        inline=False,
    )
    embed.add_field(
        name="🪙 Sua carteira",
        value=f"**{max(0, int(resumo['denarios'])):,} Denários**".replace(",", "."),
        inline=True,
    )
    if resumo["media_nota"] is not None:
        embed.add_field(
            name="⭐ Suas avaliações",
            value=f"**{resumo['media_nota']:.1f}/10** · {resumo['qtd_notas']} avaliações",
            inline=True,
        )
    if resumo["pendentes"]:
        embed.add_field(
            name="📬 Há atualizações nos seus registros",
            value=f"Você tem **{resumo['pendentes']}** registro(s) aguardando moderação. Consulte **Minha biblioteca → Meus registros**.",
            inline=True,
        )

    embed.add_field(
        name="Atalhos rápidos",
        value=(
            "📬 **Meus registros** para acompanhar aprovações · "
            "🔔 **Notificações** para escolher avisos · "
            "👤 **Meu perfil** para consultar sua trajetória.\\n"
            "🃏 **Cartas do Coliseu** para consultar sua coleção, deck, drops e estatísticas."
        ),
        inline=False,
    )

    embed.set_footer(text="NARA • Painel privado · Voltar retorna uma etapa; Fechar encerra esta sessão")
    return embed, None


def _retorno_categoria_membro(bot: commands.Bot, user_id: int, categoria: str):
    async def voltar(interaction: discord.Interaction):
        if categoria == "__inicio__":
            # Reconhece o clique antes das consultas do resumo e da renderização do deck.
            if not interaction.response.is_done():
                await interaction.response.defer()
            embed, deck_file = await _montar_embed_central_nara(bot, user_id)
            view = PainelMembrosView(bot, user_id)
            mensagem = await interaction.edit_original_response(
                embed=embed, attachments=[deck_file] if deck_file else [], view=view,
            )
            view._nara_message = mensagem
            return
        view = MembrosCategoriaView(bot, user_id, categoria)
        view._nara_message = interaction.message
        await interaction.response.edit_message(embed=_embed_categoria_membro(categoria), view=view)
    return voltar


LUATOOLS_DOWNLOAD_URL = "https://github.com/madoiscool/LuaTools/releases/download/v1.3.2/LuaTools-win-Setup.exe"
LUATOOLS_TUTORIAL_URL = "https://discord.com/channels/1563028028508995585/1564047314937716736/1564048613250965726"


def luatools_embed() -> discord.Embed:
    return discord.Embed(
        title="🎮 LuaTools — Integração com Steam",
        description=(
            "Conheça o LuaTools! Aprenda a utilizar a ferramenta para adicionar e instalar "
            "jogos na sua biblioteca Steam e conhecer seus recursos.\n\n"
            "📌 Confira os requisitos e as instruções do tutorial e baixe ferramentas somente "
            "de fontes confiáveis.\n\n"
            "⚠️ Adicionar um jogo à biblioteca não garante uma licença válida para jogá-lo. "
            "A disponibilidade e a execução dependem da compatibilidade e dos direitos de uso."
        ),
        color=config.COR_OURO,
    )


class LuaToolsLinksView(discord.ui.View):
    def __init__(self, callback_voltar=None):
        super().__init__(timeout=600 if callback_voltar else None)
        self.add_item(discord.ui.Button(
            label="Baixar LuaTools v1.3.2", emoji="⬇️",
            style=discord.ButtonStyle.link, url=LUATOOLS_DOWNLOAD_URL,
        ))
        self.add_item(discord.ui.Button(
            label="Assistir ao tutorial", emoji="📹",
            style=discord.ButtonStyle.link, url=LUATOOLS_TUTORIAL_URL,
        ))
        if callback_voltar:
            adicionar_botao_voltar(self, callback_voltar, label="Voltar à categoria", emoji="↩️")


def tutorial_transmissao_embed() -> discord.Embed:
    embed = discord.Embed(
        title="📺 Como transmitir sua tela no Discord",
        description=(
            "Siga os passos abaixo para compartilhar um jogo, aplicativo ou a tela inteira "
            "com as pessoas em um canal de voz.\n\n"
            "**💻 No computador (Windows/macOS)**\n"
            "1. Entre em um canal de voz ou inicie uma chamada.\n"
            "2. Clique em **Compartilhar sua tela** (ícone de monitor).\n"
            "3. Escolha uma janela específica ou a tela inteira.\n"
            "4. Ajuste a resolução e a taxa de quadros disponíveis.\n"
            "5. Se quiser transmitir o áudio, selecione uma janela/aplicativo compatível "
            "e habilite o compartilhamento de som quando essa opção aparecer.\n"
            "6. Clique em **Transmitir ao vivo**. Para encerrar, clique em **Parar transmissão**.\n\n"
            "**📱 No celular**\n"
            "1. Entre em um canal de voz ou chamada pelo aplicativo Discord.\n"
            "2. Abra os controles da chamada e toque em **Compartilhar tela**.\n"
            "3. Confirme **Iniciar agora** (Android) ou **Iniciar transmissão** (iOS), "
            "quando solicitado pelo sistema.\n"
            "4. Para encerrar, volte ao Discord e toque em **Parar compartilhamento**.\n\n"
            "**🔧 Se algo não funcionar**\n"
            "• Verifique se o Discord tem permissão para capturar a tela.\n"
            "• Feche e abra novamente o Discord; no computador, tente executar o app com as permissões adequadas.\n"
            "• Algumas plataformas, aplicativos protegidos e conteúdos com DRM podem bloquear a captura.\n"
            "• A disponibilidade de áudio e de opções de qualidade varia conforme o dispositivo e o sistema."
        ),
        color=config.COR_OURO,
    )
    embed.set_footer(text="NARA • Ajuda e suporte")
    return embed


class MeusRegistrosSelect(discord.ui.Select):
    def __init__(self, view: "MeusRegistrosView"):
        self.parent_view = view
        super().__init__(
            placeholder="Filtrar meus registros",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="Todos", value="all", default=view.filtro == "all"),
                discord.SelectOption(label="Aguardando aprovação", value="pending", default=view.filtro == "pending"),
                discord.SelectOption(label="Aprovados", value="approved", default=view.filtro == "approved"),
                discord.SelectOption(label="Rejeitados", value="rejected", default=view.filtro == "rejected"),
                discord.SelectOption(label="Invalidados", value="invalidated", default=view.filtro == "invalidated"),
            ],
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        nova_view = MeusRegistrosView(
            self.parent_view.bot,
            self.parent_view.user_id,
            self.values[0],
            callback_voltar=self.parent_view.callback_voltar,
        )
        embed = await nova_view.criar_embed()
        await interaction.response.edit_message(embed=embed, view=nova_view)


class CorrigirRegistroSelect(discord.ui.Select):
    """Permite reabrir um registro rejeitado com os dados anteriores preenchidos."""

    def __init__(self, parent_view: "MeusRegistrosView", rows):
        self.parent_view = parent_view
        options = []
        for row in rows[:25]:
            tipo = str(row["tipo"])
            titulo = str(row["titulo"] or "Jogo")
            motivo = str(row["motivo"] or "Revise os dados e o comprovante")
            options.append(discord.SelectOption(
                label=f"{tipo}: {titulo}"[:100],
                value=f"{tipo}:{int(row['id'])}",
                description=motivo[:100],
                emoji="📝",
            ))
        super().__init__(
            placeholder="Corrigir um registro rejeitado (dados pré-preenchidos)",
            min_values=1, max_values=1, options=options, row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        tipo, raw_id = self.values[0].split(":", 1)
        try:
            registro_id = int(raw_id)
        except ValueError:
            return await interaction.response.send_message("Não consegui identificar esse registro. Atualize a lista e tente novamente.", ephemeral=True)

        if tipo == "Platina":
            row = await self.parent_view.bot.db._one(
                "SELECT * FROM platinas WHERE id=? AND user_id=? AND status='rejected'",
                (registro_id, self.parent_view.user_id),
            )
            cog = self.parent_view.bot.get_cog("Platinas")
            if not row or cog is None:
                return await interaction.response.send_message("Esse registro não está mais disponível para correção. Atualize sua lista.", ephemeral=True)
            from cogs.platinas import PlatinaModal
            await interaction.response.send_modal(PlatinaModal(
                cog, row["platform"], row["game"], _data_para_modal(row["earned_at"]), row["reject_reason"]
            ))
            return

        if tipo == "Zerado":
            row = await self.parent_view.bot.db._one(
                "SELECT * FROM zerados WHERE id=? AND user_id=? AND status='rejected'",
                (registro_id, self.parent_view.user_id),
            )
            cog = self.parent_view.bot.get_cog("Zerados")
            if not row or cog is None:
                return await interaction.response.send_message("Esse registro não está mais disponível para correção. Atualize sua lista.", ephemeral=True)
            from cogs.zerados import ZeradoModal
            await interaction.response.send_modal(ZeradoModal(
                cog, row["platform"], row["game"], _data_para_modal(row["finished_at"]), row["reject_reason"]
            ))
            return

        if tipo == "Run":
            row = await self.parent_view.bot.db._one(
                "SELECT * FROM sl_runs WHERE id=? AND user_id=? AND status='rejected'",
                (registro_id, self.parent_view.user_id),
            )
            cog = self.parent_view.bot.get_cog("Soulslike")
            if not row or cog is None:
                return await interaction.response.send_message("Essa run não está mais disponível para correção. Atualize sua lista.", ephemeral=True)
            from cogs.soulslike import RunDadosModal
            await interaction.response.send_modal(RunDadosModal(
                cog, row["game_id"], row["challenge_id"],
                tempo_padrao=row["seconds"], build_padrao=row["build"],
                motivo_rejeicao=row["reject_reason"],
                callback_voltar=self.parent_view.callback_voltar,
            ))
            return

        await interaction.response.send_message("Tipo de registro não reconhecido. Atualize sua lista.", ephemeral=True)


def _data_para_modal(valor) -> str:
    """Converte datas ISO armazenadas no banco para o formato DD/MM/AAAA."""
    texto = str(valor or "").strip()
    if len(texto) >= 10 and texto[4:5] == "-":
        try:
            ano, mes, dia = texto[:10].split("-")
            return f"{dia}/{mes}/{ano}"
        except ValueError:
            pass
    return texto[:10] if texto else ""


class MeusRegistrosView(discord.ui.View):
    """Linha do tempo privada para acompanhar platinas, zerados e runs."""
    STATUS = {
        "pending": "🕒 Pendente",
        "approved": "✅ Aprovado",
        "rejected": "❌ Rejeitado",
        "invalidated": "⚠️ Invalidado",
    }

    def __init__(self, bot: commands.Bot, user_id: int, filtro: str = "all", callback_voltar=None):
        super().__init__(timeout=600)
        self.bot, self.user_id, self.filtro = bot, int(user_id), filtro
        self.callback_voltar = callback_voltar
        self.registros_rejeitados = []

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Estes registros são privados. Abra `/nara` para consultar os seus.", ephemeral=True)
            return False
        return True

    async def criar_embed(self) -> discord.Embed:
        rows = await self.bot.db.registros_do_usuario(self.user_id, 100)
        resumo = await self.bot.db.resumo_registros_usuario(self.user_id)
        self.registros_rejeitados = [r for r in rows if str(r["status"]) == "rejected"]
        self.clear_items()
        self.add_item(MeusRegistrosSelect(self))
        if self.registros_rejeitados:
            self.add_item(CorrigirRegistroSelect(self, self.registros_rejeitados))
        if self.callback_voltar:
            adicionar_botao_voltar(self, self.callback_voltar, label="Voltar à biblioteca", emoji="↩️")
        else:
            self.add_item(MembrosVoltarButton(self.bot, self.user_id))
        adicionar_fechar_nara(self, self.user_id)
        visiveis = [r for r in rows if self.filtro == "all" or str(r["status"]) == self.filtro]
        counts = {key: int(resumo.get(key, 0)) for key in ("pending", "approved", "rejected", "invalidated")}
        embed = discord.Embed(
            title="📬 Meus registros",
            description=(
                f"🕒 **{counts['pending']} pendentes** · ✅ **{counts['approved']} aprovados** · "
                f"❌ **{counts['rejected']} rejeitados** · ⚠️ **{counts['invalidated']} invalidados**\n"
                "Acompanhe platinas, zerados e runs. Quando houver rejeição, use o seletor de correção: os dados anteriores serão preenchidos automaticamente e você poderá atualizar o que for necessário."
            ),
            color=config.COR_OURO,
        )
        if not visiveis:
            embed.add_field(name="Nenhum registro neste filtro", value="Quando você enviar uma conquista, ela aparecerá aqui.", inline=False)
        else:
            lines = []
            for row in visiveis[:12]:
                status = self.STATUS.get(str(row["status"]), str(row["status"]).title())
                data = str(row["data"] or row["criado"] or "")[:10]
                line = (
                    f"**{row['tipo']} #{row['id']} — {discord.utils.escape_markdown(str(row['titulo']))}**\n"
                    f"{status} · `{discord.utils.escape_markdown(str(row['detalhe'] or '—'))}` · {data}"
                )
                if row["motivo"]:
                    line += f"\n> Motivo: {str(row['motivo'])[:220]}"
                lines.append(line)
            embed.add_field(name="Histórico recente", value="\n\n".join(lines)[:3900], inline=False)
            if len(visiveis) > 12:
                embed.set_footer(text=f"Mostrando 12 de {len(visiveis)} registros recentes neste filtro (até 100 carregados).")
            elif len(rows) >= 100:
                embed.set_footer(text="Linha do tempo limitada aos 100 registros mais recentes; as contagens acima incluem o histórico completo.")
        return embed

    async def on_timeout(self) -> None:
        await _marcar_painel_nara_expirado(self)


class NotificacaoToggleButton(discord.ui.Button):
    LABELS = {
        "approvals": ("Aprovações", "✅"),
        "rejections": ("Rejeições e correções", "📝"),
        "levels": ("Subidas de nível", "⬆️"),
        "replies": ("Respostas e atualizações", "💬"),
        "challenges": ("Desafios e participantes", "⚔️"),
    }

    def __init__(self, bot, guild_id: int, user_id: int, key: str, enabled: bool, row: int, callback_voltar=None):
        label, emoji = self.LABELS[key]
        super().__init__(
            label=f"{label}: {'ON' if enabled else 'OFF'}",
            emoji=emoji,
            style=discord.ButtonStyle.success if enabled else discord.ButtonStyle.secondary,
            row=row,
        )
        self.bot, self.guild_id, self.user_id, self.key = bot, int(guild_id), int(user_id), key
        self.callback_voltar = callback_voltar

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Estas preferências pertencem a outro membro.", ephemeral=True)
        prefs = await self.bot.db.get_preferencias_notificacao(self.guild_id, self.user_id)
        await self.bot.db.definir_preferencia_notificacao(self.guild_id, self.user_id, self.key, not prefs[self.key])
        view = await NotificacoesView.criar(self.bot, self.guild_id, self.user_id, callback_voltar=self.callback_voltar)
        view._nara_message = interaction.message
        await interaction.response.edit_message(view=view)




class NotificacoesInboxView(discord.ui.View):
    def __init__(self, bot, guild_id: int, user_id: int):
        super().__init__(timeout=180)
        self.bot, self.guild_id, self.user_id = bot, int(guild_id), int(user_id)

    @discord.ui.button(label="Marcar avisos como lidos", emoji="✓", style=discord.ButtonStyle.success)
    async def marcar_lidas(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "Esta caixa de entrada pertence a outro membro.", ephemeral=True
            )
        quantidade = await self.bot.db.marcar_notificacoes_lidas(self.guild_id, self.user_id)
        self.stop()
        await interaction.response.edit_message(
            content=f"✓ {quantidade} aviso(s) marcado(s) como lido(s).",
            embed=None, view=None,
        )


class NotificacoesView(discord.ui.View):
    def __init__(self, bot, guild_id: int, user_id: int, prefs: dict, callback_voltar=None):
        super().__init__(timeout=600)
        self.bot, self.guild_id, self.user_id = bot, int(guild_id), int(user_id)
        self.callback_voltar = callback_voltar
        for i, key in enumerate(NotificacaoToggleButton.LABELS):
            self.add_item(NotificacaoToggleButton(bot, guild_id, user_id, key, bool(prefs.get(key, True)), row=i // 3, callback_voltar=callback_voltar))
        if callback_voltar:
            adicionar_botao_voltar(self, callback_voltar, label="Voltar às preferências", emoji="↩️")
        else:
            self.add_item(MembrosVoltarButton(bot, user_id))
        adicionar_fechar_nara(self, user_id)

    @discord.ui.button(
        label="Ver avisos não entregues", emoji="📥",
        style=discord.ButtonStyle.primary, row=2,
    )
    async def ver_inbox(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "Esta caixa de entrada pertence a outro membro.", ephemeral=True
            )
        rows = await self.bot.db.listar_notificacoes_pendentes(self.guild_id, self.user_id, 10)
        if not rows:
            return await interaction.response.send_message(
                "Você não tem avisos pendentes. Quando uma DM não puder ser entregue, o aviso ficará disponível aqui.",
                ephemeral=True,
            )
        linhas = []
        for row in rows:
            data = str(row["created_at"] or "").split(".")[0]
            linhas.append(f"**{data}** · {row['message']}")
        embed = discord.Embed(
            title="📥 Avisos não entregues",
            description="\\n\\n".join(linhas)[:4000],
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"Exibindo até 10 avisos não lidos · {len(rows)} encontrados")
        await interaction.response.send_message(
            embed=embed,
            view=NotificacoesInboxView(self.bot, self.guild_id, self.user_id),
            ephemeral=True,
        )

    @classmethod
    async def criar(cls, bot, guild_id: int, user_id: int, callback_voltar=None):
        prefs = await bot.db.get_preferencias_notificacao(guild_id, user_id)
        return cls(bot, guild_id, user_id, prefs, callback_voltar=callback_voltar)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Estas preferências pertencem a outro membro.", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        await _marcar_painel_nara_expirado(self)


async def _executar_acao_membro(
    interaction: discord.Interaction,
    bot: commands.Bot,
    action: str,
    *,
    categoria: str | None = None,
    user_id: int | None = None,
):
    """Encaminha a ação do painel para o módulo original, sem duplicar regras de negócio."""
    voltar = (
        _retorno_categoria_membro(bot, user_id or interaction.user.id, categoria)
        if categoria in MEMBROS_CATEGORIAS or categoria == "__inicio__" else None
    )

    def com_voltar(view):
        return _view_com_navegacao_nara(view, voltar, user_id or interaction.user.id, interaction.message)

    if action == "cartas_coliseu":
        cog = bot.get_cog("PainelJogo")
        if cog is None:
            return await interaction.response.send_message("O painel de Cartas do Coliseu está indisponível no momento.", ephemeral=True)
        return await cog.abrir_painel(interaction, callback_voltar=voltar)

    if action == "coliseu":
        cog = bot.get_cog("Platinas")
        if cog is None:
            return await interaction.response.send_message("O Coliseu está indisponível no momento. Tente novamente mais tarde.", ephemeral=True)
        from cogs.platinas import ColiseuView
        view = ColiseuView(cog, interaction.user, back_callback=voltar)
        _view_com_navegacao_nara(view, voltar, interaction.user.id, interaction.message)
        return await interaction.response.edit_message(content=view.texto(), embed=None, view=view)

    if action == "biblioteca_platinas":
        cog = bot.get_cog("Platinas")
        if cog is None:
            return await interaction.response.send_message("O painel de platinas está indisponível no momento.", ephemeral=True)
        from cogs.platinas import PainelView
        view = PainelView(cog, interaction.user, callback_voltar=voltar)
        await interaction.response.defer()
        embed = await view.embed()
        return await interaction.edit_original_response(content=None, embed=embed, view=com_voltar(view))

    if action == "biblioteca_runs":
        cog = bot.get_cog("Soulslike")
        if cog is None:
            return await interaction.response.send_message("O painel de runs e desafios está indisponível no momento.", ephemeral=True)
        from cogs.soulslike import CentralView
        view = CentralView(cog, callback_voltar=voltar, user_id=interaction.user.id)
        return await interaction.response.edit_message(content=cog.texto_central(), embeds=[], view=com_voltar(view))

    if action == "zerados":
        cog = bot.get_cog("Zerados")
        if cog is None:
            return await interaction.response.send_message("O painel de jogos zerados está indisponível no momento.", ephemeral=True)
        view = cog.painel_view(interaction.user, callback_voltar=voltar)
        await interaction.response.defer()
        embed = await view.embed()
        return await interaction.edit_original_response(content=None, embed=embed, view=com_voltar(view))

    if action == "remover_zerado":
        cog = bot.get_cog("Zerados")
        if cog is None:
            return await interaction.response.send_message("O gerenciamento de jogos zerados está indisponível no momento.", ephemeral=True)
        return await interaction.response.send_modal(RemoverZeradoModal(cog, callback_voltar=voltar))

    if action == "meus_registros":
        view = MeusRegistrosView(bot, interaction.user.id, callback_voltar=voltar)
        view._nara_message = interaction.message
        await interaction.response.defer()
        embed = await view.criar_embed()
        return await interaction.edit_original_response(
            content=None, embed=embed, view=view,
        )

    if action == "notificacoes":
        if interaction.guild_id is None:
            return await interaction.response.send_message("Abra as preferências dentro do servidor.", ephemeral=True)
        await interaction.response.defer()
        view = await NotificacoesView.criar(bot, interaction.guild_id, interaction.user.id, callback_voltar=voltar)
        view._nara_message = interaction.message
        return await interaction.edit_original_response(
            content=(
                "🔔 **Notificações pessoais**\n"
                "Ative apenas os avisos que deseja receber por mensagem direta. "
                "Se as DMs estiverem fechadas, o NARABOT não consegue entregá-los."
            ), embed=None, view=view,
        )

    if action == "loja":
        cog = bot.get_cog("Loja")
        if cog is None:
            return await interaction.response.send_message("A loja está indisponível no momento.", ephemeral=True)
        from cogs.loja import LojaView
        view = LojaView(cog, interaction.user)
        await interaction.response.defer()
        await view.carregar()
        com_voltar(view)
        return await interaction.edit_original_response(content=None, embed=view.embed(), view=view)

    if action == "nivel":
        cog = bot.get_cog("ProgressaoXP")
        if cog is None:
            return await interaction.response.send_message("O sistema de níveis está indisponível no momento.", ephemeral=True)
        await interaction.response.defer()
        user = await bot.db.get_user(interaction.user.id)
        xp = int(user["xp"])
        nivel_atual = nivel_por_xp(xp)
        embed = discord.Embed(title=f"🛡️ NARA — {interaction.user.display_name}", color=config.COR_OURO)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Patente", value=patente_por_nivel(nivel_atual), inline=True)
        embed.add_field(name="Nível", value=str(nivel_atual), inline=True)
        embed.add_field(name="XP total", value=f"{xp:,}", inline=True)
        embed.add_field(name="Progresso", value=barra_progresso(xp), inline=False)
        return await interaction.edit_original_response(embed=embed, content=None, view=_view_com_navegacao_nara(view_so_com_voltar(voltar), voltar, interaction.user.id, interaction.message))

    if action == "ranking_xp":
        cog = bot.get_cog("ProgressaoXP")
        if cog is None:
            return await interaction.response.send_message("O ranking de XP está indisponível no momento.", ephemeral=True)
        await interaction.response.defer()
        rows = await bot.db.ranking_xp(10)
        if not rows:
            return await interaction.edit_original_response(content="Ainda não há XP registrado para montar o ranking.", embed=None, view=_view_com_navegacao_nara(view_so_com_voltar(voltar), voltar, interaction.user.id, interaction.message))
        linhas = []
        for i, row in enumerate(rows, 1):
            nivel_atual = nivel_por_xp(int(row["valor"]))
            linhas.append(
                f"`{i:>2}.` <@{row['user_id']}> — **Nível {nivel_atual}** · "
                f"{patente_por_nivel(nivel_atual)} · {row['valor']} XP"
            )
        return await interaction.edit_original_response(
            content="## 🏆 Ranking de XP da NARA\n\n" + "\n".join(linhas),
            embed=None,
            view=_view_com_navegacao_nara(view_so_com_voltar(voltar), voltar, interaction.user.id, interaction.message),
        )

    if action == "memoria":
        cog = bot.get_cog("NaraIA")
        if cog is None:
            return await interaction.response.send_message("As preferências de memória estão indisponíveis no momento.", ephemeral=True)
        return await cog.abrir_painel_memoria(interaction, callback_voltar=voltar)

    if action == "ajuda":
        cog = bot.get_cog("NaraIA")
        if cog is None:
            return await interaction.response.send_message("A Central de Ajuda está indisponível no momento.", ephemeral=True)
        return await cog.abrir_central_ajuda(interaction, callback_voltar=voltar)

    if action == "perfil":
        cog = bot.get_cog("Perfil")
        if cog is None:
            return await interaction.response.send_message("Seu perfil está indisponível no momento.", ephemeral=True)
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("Não consegui identificar seu perfil neste servidor.", ephemeral=True)
        await interaction.response.defer()
        embed = await cog.embed_perfil(interaction.user)
        embed.set_footer(text="NARA • Seu perfil pessoal")
        return await interaction.edit_original_response(embed=embed, content=None, view=_view_com_navegacao_nara(view_so_com_voltar(voltar), voltar, interaction.user.id, interaction.message))

    if action == "santuario":
        cog = bot.get_cog("Santuario")
        if cog is None:
            return await interaction.response.send_message("Seu Santuário está indisponível no momento.", ephemeral=True)
        return await cog.abrir_meu(interaction, callback_voltar=voltar)

    if action == "catalogos":
        cog = bot.get_cog("CatalogoIntegrado")
        if cog is None:
            return await interaction.response.send_message("O catálogo Ports & Mods ainda não está disponível.", ephemeral=True)
        return await cog.abrir_membros(interaction, callback_voltar=voltar)

    if action == "luatools":
        return await interaction.response.edit_message(
            content=None, embed=luatools_embed(), view=LuaToolsLinksView(callback_voltar=voltar)
        )

    if action == "tutorial_transmissao":
        return await interaction.response.edit_message(
            content=None,
            embed=tutorial_transmissao_embed(),
            view=_view_com_navegacao_nara(view_so_com_voltar(voltar), voltar, interaction.user.id, interaction.message),
        )

    if action in ("community_home", "community_archive", "community_mine"):
        cog = bot.get_cog("Comunidade")
        if cog is None:
            return await interaction.response.send_message("O sistema de contribuições está indisponível no momento.", ephemeral=True)
        if action == "community_archive":
            await interaction.response.defer()
            return await cog.mostrar_arquivo(interaction, callback_voltar=voltar)
        if action == "community_mine":
            await interaction.response.defer()
            return await cog.mostrar_minhas(interaction, callback_voltar=voltar)
        from cogs.comunidade import CommunityHomeView
        embed = discord.Embed(
            title="💡 Contribuições da Comunidade",
            description="Publique lore, teorias, descobertas, guias, tutoriais e propostas para o NARA. Todos os envios passam por aprovação humana antes de aparecerem nos canais oficiais.",
            color=config.COR_OURO,
        )
        view = CommunityHomeView(cog, callback_voltar=voltar)
        _view_com_navegacao_nara(view, voltar, interaction.user.id, interaction.message)
        return await interaction.response.edit_message(content=None, embed=embed, view=view)

    return await interaction.response.send_message("Esta opção ainda não está disponível. Volte à central e escolha outra categoria.", ephemeral=True)


class MembrosAcaoButton(discord.ui.Button):
    def __init__(self, painel, action: str, label: str, emoji: str, style: discord.ButtonStyle, row: int):
        super().__init__(label=label, emoji=emoji, style=style, row=row)
        self.painel = painel
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        await _executar_acao_membro(interaction, self.painel.bot, self.action, categoria=self.painel.categoria, user_id=self.painel.user_id)


class MembrosVoltarButton(discord.ui.Button):
    def __init__(self, bot: commands.Bot, user_id: int):
        super().__init__(label="Voltar à central", emoji="🏠", style=discord.ButtonStyle.secondary, row=4)
        self.bot = bot
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Este painel pertence a outro membro.", ephemeral=True)
        embed, deck_file = await _montar_embed_central_nara(self.bot, self.user_id)
        view = PainelMembrosView(self.bot, self.user_id)
        view._nara_message = interaction.message
        if deck_file:
            await interaction.response.edit_message(embed=embed, attachments=[deck_file], view=view)
        else:
            await interaction.response.edit_message(embed=embed, attachments=[], view=view)


class MembrosCategoriaView(discord.ui.View):
    def __init__(self, bot: commands.Bot, user_id: int, categoria: str):
        super().__init__(timeout=600)
        self.bot = bot
        self.user_id = user_id
        self.categoria = categoria
        dados = MEMBROS_CATEGORIAS[categoria]
        for index, (action, label, emoji, style) in enumerate(dados["acoes"]):
            self.add_item(MembrosAcaoButton(self, action, label, emoji, style, row=index // 2))
        self.add_item(MembrosVoltarButton(bot, user_id))
        adicionar_fechar_nara(self, user_id)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Este painel pertence a outro membro. Use `/nara` para abrir o seu.", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        await _marcar_painel_nara_expirado(self)


class MembrosAcessoDiretoButton(discord.ui.Button):
    def __init__(self, painel, action: str, label: str, emoji: str, style: discord.ButtonStyle, row: int = 2):
        super().__init__(label=label, emoji=emoji, style=style, row=row)
        self.painel = painel
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        await _executar_acao_membro(interaction, self.painel.bot, self.action, categoria="__inicio__", user_id=self.painel.user_id)


class MembrosCategoriaButton(discord.ui.Button):
    def __init__(self, painel, categoria: str, label: str, emoji: str, row: int):
        super().__init__(label=label, emoji=emoji, style=discord.ButtonStyle.primary, row=row)
        self.painel = painel
        self.categoria = categoria

    async def callback(self, interaction: discord.Interaction):
        dados = MEMBROS_CATEGORIAS[self.categoria]
        embed = discord.Embed(
            title=dados["titulo"],
            description=dados["descricao"] + "\n\nEscolha uma opção. Você pode voltar à central a qualquer momento.",
            color=config.COR_OURO,
        )
        embed.set_footer(text="NARA • Painel privado · Voltar à central a qualquer momento")
        view = MembrosCategoriaView(self.painel.bot, self.painel.user_id, self.categoria)
        view._nara_message = interaction.message
        await interaction.response.edit_message(embed=embed, view=view)


class PainelMembrosView(discord.ui.View):
    """Central de membros organizada por categorias, com submenus privados."""

    def __init__(self, bot: commands.Bot, user_id: int):
        super().__init__(timeout=600)
        self.bot = bot
        self.user_id = user_id
        categorias = [
            ("jogos", "Jogos e biblioteca", "🎮"),
            ("progresso", "Meu progresso", "🏆"),
            ("comunidade", "Comunidade", "📡"),
            ("preferencias", "Preferências", "🧠"),
            ("ajuda", "Ajuda e suporte", "❔"),
        ]
        for index, (key, label, emoji) in enumerate(categorias):
            self.add_item(MembrosCategoriaButton(self, key, label, emoji, row=index // 3))
        self.add_item(MembrosAcessoDiretoButton(self, "perfil", "Meu perfil", "👤", discord.ButtonStyle.secondary))
        self.add_item(MembrosAcessoDiretoButton(self, "santuario", "Meu Santuário", "🏛️", discord.ButtonStyle.secondary))
        # Atalhos frequentes na tela inicial: reduzem navegação sem duplicar regras de negócio.
        self.add_item(MembrosAcessoDiretoButton(self, "meus_registros", "Meus registros", "📬", discord.ButtonStyle.secondary))
        self.add_item(MembrosAcessoDiretoButton(self, "notificacoes", "Notificações", "🔔", discord.ButtonStyle.secondary))
        self.add_item(GuiaMembrosSelect(bot, user_id))
        adicionar_fechar_nara(self, user_id)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Este painel pertence a outro membro. Use `/nara` para abrir o seu.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        await _marcar_painel_nara_expirado(self)


class PainelMembros(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="nara", description="Abra sua central de Ports & Mods, biblioteca, progresso, recompensas e suporte.")
    @app_commands.guild_only()
    async def nara(self, interaction: discord.Interaction):
        # O usuário recebe o ACK do Discord imediatamente; o painel substitui o
        # placeholder assim que os dados e a prévia estiverem prontos.
        await interaction.response.defer(ephemeral=True, thinking=True)
        embed, deck_file = await _montar_embed_central_nara(self.bot, interaction.user.id)
        view = PainelMembrosView(self.bot, interaction.user.id)
        mensagem = await interaction.edit_original_response(
            embed=embed, attachments=[deck_file] if deck_file else [], view=view,
        )
        view._nara_message = mensagem

    @app_commands.command(name="publicar_luatools", description="Publica e fixa o painel do LuaTools em um canal.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def publicar_luatools(self, interaction: discord.Interaction, canal: discord.TextChannel):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                "Você precisa da permissão Gerenciar servidor para publicar este painel.",
                ephemeral=True,
            )
        await interaction.response.defer(ephemeral=True, thinking=True)
        mensagem = await canal.send(embed=luatools_embed(), view=LuaToolsLinksView())
        try:
            await mensagem.pin(reason=f"Painel LuaTools publicado por {interaction.user}")
            resultado = f"Painel do LuaTools publicado e fixado em {canal.mention}."
        except discord.Forbidden:
            resultado = (
                f"Painel publicado em {canal.mention}, mas não consegui fixá-lo. "
                "Conceda ao bot a permissão Gerenciar mensagens."
            )
        await interaction.followup.send(resultado, ephemeral=True)

    async def cog_load(self):
        # Os comandos continuam implementados nos módulos originais e são acessados
        # pelos botões. Removê-los da árvore reduz a lista pública do Discord sem
        # duplicar a lógica nem quebrar os fluxos internos.
        comandos_membros = (
            "coliseu", "zerados", "remover_zerado",
            "loja", "nivel", "ranking-xp", "nara_memoria", "central_ajuda", "comandos",
        )
        for nome in comandos_membros:
            self.bot.tree.remove_command(nome)


async def setup(bot: commands.Bot):
    await bot.add_cog(PainelMembros(bot))
