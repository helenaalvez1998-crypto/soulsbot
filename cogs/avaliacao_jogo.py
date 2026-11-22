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
    """Formata a dificuldade subjetiva, sem declarar uma dificuldade universal."""
    if valor is None:
        return None
    valor = int(valor)
    rotulo = ROTULOS_DIFICULDADE.get(valor)
    return f"{valor}/5 — {rotulo}" if rotulo else f"{valor}/5"


class ConfirmarAvaliacaoView(discord.ui.View):
    """Última conferência antes de efetivamente criar o registro."""
    def __init__(self, nota: int, dificuldade: int, comentario: str, concluir: ConcluirAvaliacao, contexto: str = ""):
        super().__init__(timeout=300)
        self.nota = int(nota)
        self.dificuldade = int(dificuldade)
        self.comentario = str(comentario or "").strip()[:500]
        self.concluir = concluir
        self.contexto = str(contexto or "").strip()[:900]
        self._done = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self._done:
            await interaction.response.send_message("Esta avaliação já foi processada.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirmar e continuar", emoji="✅", style=discord.ButtonStyle.success)
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self._done = True
        for item in self.children:
            item.disabled = True
        # O fluxo original confirma a interação (defer/modal/DM) e continua o registro.
        await self.concluir(interaction, self.nota, self.dificuldade, self.comentario)

    @discord.ui.button(label="Cancelar", emoji="✖️", style=discord.ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self._done = True
        await interaction.response.edit_message(
            content="Avaliação cancelada. Nenhum registro foi enviado à moderação.", view=None
        )


class ComentarioJogoModal(discord.ui.Modal):
    """Recebe comentário opcional depois da nota e da dificuldade percebida."""

    def __init__(
        self, nota: int, dificuldade: int, concluir: ConcluirAvaliacao,
        ao_concluir: Callable[[], None] | None = None, contexto: str = "",
    ):
        super().__init__(title=f"Comentário · Nota {nota}/10 · Dificuldade {dificuldade}/5", timeout=300)
        self.nota = int(nota)
        self.dificuldade = int(dificuldade)
        self.concluir = concluir
        self.ao_concluir = ao_concluir
        self.contexto = str(contexto or "").strip()[:900]
        self.comentario = discord.ui.TextInput(
            label="Comentário (opcional)",
            placeholder="Compartilhe algo sobre sua experiência — ou deixe em branco.",
            style=discord.TextStyle.paragraph,
            required=False,
            min_length=0,
            max_length=500,
        )
        self.add_item(self.comentario)

    async def on_submit(self, interaction: discord.Interaction):
        comentario = str(self.comentario.value or "").strip()[:500]
        if comentario and len(comentario) < 5:
            return await interaction.response.send_message(
                "Se escrever um comentário, use pelo menos 5 caracteres. Você também pode deixar o campo em branco.",
                ephemeral=True,
            )
        if self.ao_concluir is not None:
            self.ao_concluir()
        contexto = f"**Dados do registro**\n{self.contexto}\n\n" if self.contexto else ""
        preview = (
            contexto + f"**Nota:** ⭐ {self.nota}/10\n"
            f"**Dificuldade percebida:** {formatar_dificuldade(self.dificuldade)}\n"
            f"**Comentário:** {discord.utils.escape_markdown(comentario) if comentario else '_Não informado_'}\n\n"
            "Confira antes de continuar. Nada será enviado à moderação até você confirmar."
        )
        await interaction.response.send_message(
            "## Revisar avaliação\n" + preview,
            view=ConfirmarAvaliacaoView(self.nota, self.dificuldade, comentario, self.concluir, self.contexto),
            ephemeral=True,
        )


class DificuldadeJogoView(discord.ui.View):
    """Pergunta a dificuldade que o próprio jogador sentiu."""

    OPCOES = (
        (1, "Muito fácil"),
        (2, "Fácil"),
        (3, "Moderada"),
        (4, "Difícil"),
        (5, "Muito difícil"),
    )

    def __init__(self, nota: int, pergunta: str, concluir: ConcluirAvaliacao, contexto: str = ""):
        super().__init__(timeout=300)
        self.nota = int(nota)
        self.pergunta = pergunta
        self.concluir = concluir
        self.contexto = str(contexto or "").strip()[:900]
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
                "Esta avaliação já avançou para a conferência final.", ephemeral=True,
            )
        dificuldade = int(self.selecao.values[0])
        await interaction.response.send_modal(
            ComentarioJogoModal(self.nota, dificuldade, self.concluir, self.marcar_concluido, self.contexto)
        )

    def marcar_concluido(self):
        self._claimed = True

    @discord.ui.button(label="Voltar à nota", style=discord.ButtonStyle.secondary, row=1)
    async def alterar_nota(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self._claimed:
            return await interaction.response.send_message(
                "Esta avaliação já avançou para a conferência final.", ephemeral=True,
            )
        await interaction.response.edit_message(
            content=(
                "**Avaliação — 1/3: Nota do jogo**\n"
                "Quanto você gostou deste jogo? Escolha uma nota de 1 a 10."
            ),
            view=NotaJogoView(self.concluir, self.pergunta, self.contexto),
        )


class NotaJogoView(discord.ui.View):
    """Conduz a avaliação: nota, dificuldade percebida, comentário opcional e revisão."""

    def __init__(self, concluir: ConcluirAvaliacao, pergunta_dificuldade: str, contexto: str = ""):
        super().__init__(timeout=300)
        self.concluir = concluir
        self.pergunta_dificuldade = pergunta_dificuldade
        self.contexto = str(contexto or "").strip()[:900]
        self.selecao = discord.ui.Select(
            placeholder="Quanto você gostou do jogo? Escolha de 1 a 10",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label=f"{nota}/10", value=str(nota),
                    description={1: "Péssimo", 2: "Muito ruim", 3: "Ruim", 4: "Abaixo da média",
                                 5: "Regular", 6: "Razoável", 7: "Bom", 8: "Muito bom",
                                 9: "Excelente", 10: "Adorei"}[nota],
                )
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
            view=DificuldadeJogoView(nota, self.pergunta_dificuldade, self.concluir, self.contexto),
        )
