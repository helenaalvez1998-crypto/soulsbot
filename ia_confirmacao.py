"""Interface (botões) do agente da Nara.

ConfirmarAcaoView: toda ação que gasta algo do membro ou sobrescreve dados só acontece depois que
o PRÓPRIO autor clica em Confirmar. Isso vale mesmo que a IA seja enganada por uma mensagem maliciosa:
quem decide é um clique humano, sobre um resumo gerado pelo código (não pelo modelo).
"""
from __future__ import annotations

import asyncio
import logging

import discord

from ia_ferramentas import PAINEIS
from ia_nucleo import ErroFerramenta, Pendente

log = logging.getLogger("nara.ia.botoes")

TIMEOUT_CONFIRMACAO = 120


class ConfirmarAcaoView(discord.ui.View):
    def __init__(self, bot, pendente: Pendente):
        super().__init__(timeout=TIMEOUT_CONFIRMACAO)
        self.bot = bot
        self.pendente = pendente
        self.message: discord.Message | None = None
        self._usada = False
        self._trava = asyncio.Lock()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.pendente.autor_id:
            await interaction.response.send_message("Só quem fez o pedido pode confirmar.", ephemeral=True)
            return False
        if self.pendente.exige_mod:
            from cogs.platinas import eh_moderador       # noqa: PLC0415
            if not isinstance(interaction.user, discord.Member) or not await eh_moderador(interaction.user, self.bot.db):
                await interaction.response.send_message("Apenas moderadores.", ephemeral=True)
                return False
        return True

    async def _finalizar(self, interaction: discord.Interaction, linha: str):
        for item in self.children:
            item.disabled = True
        base = interaction.message.content if interaction.message else ""
        await interaction.edit_original_response(content=f"{base}\n\n{linha}"[:1990], view=None)
        self.stop()

    @discord.ui.button(label="Confirmar", emoji="✅", style=discord.ButtonStyle.success)
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self._trava:
            if self._usada:
                return await interaction.response.send_message("Essa ação já foi tratada.", ephemeral=True)
            self._usada = True
        await interaction.response.defer()
        try:
            texto = await self.pendente.executar()
        except ErroFerramenta as e:
            texto = f"⚠️ Não deu para concluir: {e}"
        except Exception:
            log.exception("Falha ao executar ação confirmada %s", self.pendente.ferramenta)
            texto = "⚠️ Algo deu errado ao executar. Nada foi cobrado se a falha aconteceu antes; confira com /perfil."
        await self._finalizar(interaction, texto)

    @discord.ui.button(label="Cancelar", emoji="✖️", style=discord.ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self._trava:
            if self._usada:
                return await interaction.response.send_message("Essa ação já foi tratada.", ephemeral=True)
            self._usada = True
        await interaction.response.defer()
        await self._finalizar(interaction, "✖️ Cancelado. Nada foi alterado.")

    async def on_timeout(self):
        if self.message is not None and not self._usada:
            try:
                await self.message.edit(content=f"{self.message.content}\n\n⌛ Expirou sem confirmação. Nada foi alterado.",
                                        view=None)
            except discord.HTTPException:
                pass


async def abrir_painel(bot, painel: str, interaction: discord.Interaction):
    """Abre um painel existente reaproveitando o fluxo atual de cada módulo."""
    def cog(nome):
        c = bot.get_cog(nome)
        if c is None:
            raise ErroFerramenta("Esse painel não está disponível. Avise a moderação.")
        return c

    if painel == "coliseu":
        from cogs.platinas import ColiseuView           # noqa: PLC0415
        view = ColiseuView(cog("Platinas"), interaction.user)
        return await interaction.response.send_message(content=view.texto(), view=view, ephemeral=True)
    if painel == "platinas":
        return await cog("Platinas").abrir_painel(interaction)
    if painel == "zerados":
        return await cog("Zerados").abrir_painel(interaction)
    if painel == "runs":
        from cogs.soulslike import CentralView           # noqa: PLC0415
        c = cog("Soulslike")
        return await interaction.response.send_message(content=c.texto_central(), view=CentralView(c), ephemeral=True)
    if painel == "loja":
        return await cog("Loja").abrir_loja(interaction)
    if painel == "santuario":
        return await cog("Santuario").abrir_meu(interaction)
    raise ErroFerramenta("Painel desconhecido.")


class AtalhoView(discord.ui.View):
    """Botões que abrem painéis (resposta privada) para quem pediu."""
    def __init__(self, bot, autor_id: int, paineis: list[str]):
        super().__init__(timeout=300)
        self.bot = bot
        self.autor_id = autor_id
        for chave in paineis[:4]:
            botao = discord.ui.Button(label=PAINEIS[chave].split(" (")[0][:80], style=discord.ButtonStyle.primary)
            botao.callback = self._callback(chave)
            self.add_item(botao)

    def _callback(self, chave: str):
        async def cb(interaction: discord.Interaction):
            if interaction.user.id != self.autor_id:
                return await interaction.response.send_message("Esse botão é de quem pediu. Fale comigo para ter o seu.",
                                                               ephemeral=True)
            try:
                await abrir_painel(self.bot, chave, interaction)
            except ErroFerramenta as e:
                if not interaction.response.is_done():
                    await interaction.response.send_message(str(e), ephemeral=True)
        return cb
