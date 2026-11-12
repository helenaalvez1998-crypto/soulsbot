"""Utilitários compartilhados para navegação entre painéis efêmeros do NARA."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

import discord

CallbackVoltar = Callable[[discord.Interaction], Awaitable[None]]


class VoltarPainelButton(discord.ui.Button):
    """Botão que restaura o painel imediatamente anterior na mesma mensagem."""

    def __init__(
        self,
        callback_voltar: CallbackVoltar,
        *,
        label: str = "Voltar ao painel anterior",
        emoji: str = "↩️",
        row: int | None = None,
    ):
        super().__init__(
            label=label,
            emoji=emoji,
            style=discord.ButtonStyle.secondary,
            row=row,
        )
        self.callback_voltar = callback_voltar

    async def callback(self, interaction: discord.Interaction):
        await self.callback_voltar(interaction)


def adicionar_botao_voltar(
    view: discord.ui.View | None,
    callback_voltar: CallbackVoltar | None,
    *,
    label: str = "Voltar ao painel anterior",
    emoji: str = "↩️",
) -> discord.ui.View | None:
    """Adiciona um botão de retorno uma única vez, sem alterar os outros itens."""
    if view is None or callback_voltar is None:
        return view
    # Guarda o callback para que telas dinâmicas possam reconstruir a View
    # depois de clear_items() sem perder a navegação.
    view._nara_callback_voltar = callback_voltar
    if any(isinstance(item, VoltarPainelButton) for item in view.children):
        view._nara_botao_voltar = True
        return view
    if len(view.children) >= 25:
        # Discord limita Views a 25 componentes. Não removemos controles funcionais
        # para encaixar o botão: o chamador pode exibir uma mensagem de fallback.
        return view
    view.add_item(VoltarPainelButton(callback_voltar, label=label, emoji=emoji))
    view._nara_botao_voltar = True
    return view


def restaurar_botao_voltar(view: discord.ui.View | None) -> discord.ui.View | None:
    """Reinsere o botão de retorno após uma View dinâmica reconstruir seus itens."""
    if view is None:
        return view
    callback = getattr(view, "_nara_callback_voltar", None)
    if callback is None:
        return view
    return adicionar_botao_voltar(view, callback)


def view_so_com_voltar(callback_voltar: CallbackVoltar) -> discord.ui.View:
    """Cria uma View curta para resultados que, de outro modo, seriam telas sem navegação."""
    view = discord.ui.View(timeout=600)
    adicionar_botao_voltar(view, callback_voltar)
    return view
