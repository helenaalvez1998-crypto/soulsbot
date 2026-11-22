"""Etapas reutilizáveis para avaliar um jogo ao registrar uma conquista."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

import discord

ConcluirAvaliacao = Callable[[discord.Interaction, int, int, str], Awaitable[None]]
ROTULOS_DIFICULDADE = {
    1: "Muito fácil",
    2: "Fácil",
    3: "Moderada",
    4: "Difícil",
    5: "Muito difícil",
}


def formatar_dificuldade(valor: int | None) -> str | None:
    """Formata a escala subjetiva sem classificar o jogo de forma universal."""
    if valor is None:
        return None
    valor = int(valor)
    rotulo = ROTULOS_DIFICULDADE.get(valor)
    return f"{valor}/5 — {rotulo}" if rotulo else f"{valor}/5"


class ComentarioJogoModal(discord.ui.Modal):
    """Recebe o comentário depois da nota e da dificuldade percebida."""

    def __init__(
        self, nota: int, dificuldade: int, concluir: ConcluirAvaliacao,
        ao_concluir: Callable[[], None] | None = None,
    ):
        super().__init__(title=f"Comentário · Nota {nota}/10 · Dificuldade {dificuldade}/5", timeout=300)
        self.nota = int(nota)
        self.dificuldade = int(dificuldade)
        self.concluir = concluir
        self.ao_concluir = ao_concluir
        self.comentario = discord.ui.TextInput(
            label="O que você achou do jogo?",
            placeholder="Conte o que mais gostou, o que poderia melhorar ou algo marcante...",
            style=discord.TextStyle.paragraph,
            required=True,
            min_length=5,
            max_length=500,
        )
        self.add_item(self.comentario)

    async def on_submit(self, interaction: discord.Interaction):
        comentario = str(self.comentario.value).strip()
        if len(comentario) < 5:
            return await interaction.response.send_message(
                "Escreva um comentário com pelo menos 5 caracteres.", ephemeral=True
            )
        await self.concluir(interaction, self.nota, self.dificuldade, comentario)
        if self.ao_concluir is not None:
            self.ao_concluir()


class DificuldadeJogoView(discord.ui.View):
    """Pergunta a dificuldade que o próprio jogador sentiu."""

    OPCOES = (
        (1, "Muito fácil"),
        (2, "Fácil"),
        (3, "Moderada"),
        (4, "Difícil"),
        (5, "Muito difícil"),
    )

    def __init__(self, nota: int, pergunta: str, concluir: ConcluirAvaliacao):
        super().__init__(timeout=300)
        self.nota = int(nota)
        self.pergunta = pergunta
        self.concluir = concluir
        self._claimed = False
        self.selecao = discord.ui.Select(
            placeholder="Como foi a dificuldade para você? (1 a 5)",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=f"{valor} — {rotulo}", value=str(valor))
                for valor, rotulo in self.OPCOES
            ],
        )
        self.selecao.callback = self.selecionar_dificuldade
        self.add_item(self.selecao)

    async def selecionar_dificuldade(self, interaction: discord.Interaction):
        if self._claimed:
            return await interaction.response.send_message(
                "Esta avaliação já foi enviada. Confira a confirmação recebida pelo bot.",
                ephemeral=True,
            )
        dificuldade = int(self.selecao.values[0])
        await interaction.response.send_modal(
            ComentarioJogoModal(self.nota, dificuldade, self.concluir, self.marcar_concluido)
        )

    def marcar_concluido(self):
        self._claimed = True

    @discord.ui.button(label="Voltar à nota", style=discord.ButtonStyle.secondary, row=1)
    async def alterar_nota(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self._claimed:
            return await interaction.response.send_message(
                "Esta avaliação já foi enviada. Confira a confirmação recebida pelo bot.",
                ephemeral=True,
            )
        await interaction.response.edit_message(
            content=(
                "**Avaliação — 1/3: Nota do jogo**\n"
                "Quanto você gostou deste jogo? Escolha uma nota de 1 a 10."
            ),
            view=NotaJogoView(self.concluir, self.pergunta),
        )


class NotaJogoView(discord.ui.View):
    """Conduz a avaliação em ordem: nota, dificuldade percebida e comentário."""

    def __init__(self, concluir: ConcluirAvaliacao, pergunta_dificuldade: str):
        super().__init__(timeout=300)
        self.concluir = concluir
        self.pergunta_dificuldade = pergunta_dificuldade
        self.selecao = discord.ui.Select(
            placeholder="Quanto você gostou do jogo? Escolha de 1 a 10",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=f"{nota}/10", value=str(nota))
                for nota in range(1, 11)
            ],
        )
        self.selecao.callback = self.selecionar_nota
        self.add_item(self.selecao)

    async def selecionar_nota(self, interaction: discord.Interaction):
        nota = int(self.selecao.values[0])
        await interaction.response.edit_message(
            content=(
                "**Avaliação — 2/3: Dificuldade percebida**\n"
                f"{self.pergunta_dificuldade}\n"
                "Considere a sua experiência, não uma dificuldade universal do jogo."
            ),
            view=DificuldadeJogoView(nota, self.pergunta_dificuldade, self.concluir),
        )
