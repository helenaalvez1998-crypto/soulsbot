"""Contratos do painel administrativo do relacionamento adaptativo."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_relacionamento_e_configurado_por_comandos_e_nao_por_env():
    fonte = (ROOT / "cogs" / "nara_ia.py").read_text(encoding="utf-8")
    config = (ROOT / "config.py").read_text(encoding="utf-8")
    env_example = (ROOT / "env.example").read_text(encoding="utf-8")
    assert '@app_commands.command(' in fonte
    assert 'name="nara_relacionamento"' in fonte
    assert 'name="configurar"' not in fonte
    assert 'name="status"' not in fonte
    assert 'name="desativar"' not in fonte
    assert "nara_relacionamento_config" in fonte
    assert "NARA_RELACIONAMENTO_USER_ID" not in fonte + config + env_example


def test_somente_dono_do_bot_pode_alterar_configuracao():
    fonte = (ROOT / "cogs" / "nara_ia.py").read_text(encoding="utf-8")
    assert "async def _interacao_e_dono_bot" in fonte
    assert "await self.bot.is_owner(interaction.user)" in fonte
    assert fonte.count("if not await self._interacao_e_dono_bot(interaction):") == 1
    assert "@app_commands.default_permissions(administrator=True)" in fonte


def test_configuracao_persiste_e_carrega_no_inicio():
    fonte = (ROOT / "cogs" / "nara_ia.py").read_text(encoding="utf-8")
    assert "SELECT guild_id, user_id FROM nara_relacionamento_config" in fonte
    assert "self._relacionamento_alvos[guild_id] = novo_user_id" in fonte
    assert "ON CONFLICT(guild_id) DO UPDATE SET" in fonte


def test_painel_tem_botoes_de_ajuste_e_revalida_o_dono_em_cada_interacao():
    fonte = (ROOT / "cogs" / "nara_ia.py").read_text(encoding="utf-8")
    assert "class PainelRelacionamentoAdminView(discord.ui.View)" in fonte
    assert "async def interaction_check(self, interaction: discord.Interaction) -> bool:" in fonte
    assert "await self.cog._interacao_e_dono_bot(interaction)" in fonte
    assert 'label="Afinidade +0,5"' in fonte
    assert 'label="Afinidade −0,5"' in fonte
    assert 'label="Paciência +0,5"' in fonte
    assert 'label="Paciência −0,5"' in fonte
    assert 'label="Desativar relacionamento"' in fonte
    assert "ephemeral=True" in fonte
    assert "nara_relacionamento.ajustar_indicador" in fonte


def test_pontuacoes_e_eventos_nao_sao_exibidos_ao_usuario_no_painel_de_memoria():
    fonte = (ROOT / "cogs" / "nara_ia.py").read_text(encoding="utf-8")
    memoria = fonte.split("async def nara_memoria", 1)[1].split("async def nara_relatorio", 1)[0]
    assert "float(rel['afinidade'])" not in memoria
    assert "float(rel['paciencia'])" not in memoria
    assert "Eventos recentes:" not in memoria
    assert "pontuações e controles" in memoria
    assert "não aparecem neste painel" in memoria


def test_trocar_usuario_nao_apaga_o_perfil_anterior():
    fonte = (ROOT / "cogs" / "nara_ia.py").read_text(encoding="utf-8")
    comando = fonte.split("async def nara_relacionamento(", 1)[1].split("async def _carregar_memoria", 1)[0]
    assert "anterior fica preservado" in comando
    assert "DELETE FROM nara_relacionamento_perfil" not in comando
    assert "DELETE FROM nara_relacionamento_eventos" not in comando


def test_comando_reabre_usuario_selecionado_sem_variavel_nao_definida():
    fonte = (ROOT / "cogs" / "nara_ia.py").read_text(encoding="utf-8")
    comando = fonte.split("async def nara_relacionamento(", 1)[1].split("async def _carregar_memoria", 1)[0]
    declaracao = "anterior = int(self._relacionamento_alvos.get(guild_id, 0) or 0)"
    assert declaracao in comando
    assert comando.index(declaracao) < comando.index("user_id = anterior")
