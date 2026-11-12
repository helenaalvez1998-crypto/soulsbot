from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADMIN = (ROOT / "cogs" / "admin.py").read_text(encoding="utf-8")


def test_dashboard_e_historico_estao_no_menu_diagnostico():
    assert '("dashboard", "Dashboard operacional"' in ADMIN
    assert '("history", "Histórico de auditoria"' in ADMIN
    assert 'if action == "dashboard":' in ADMIN
    assert 'if action == "history":' in ADMIN


def test_dashboard_usa_metricas_das_tres_filas_e_logs_de_decisao():
    assert '("platinas", "sl_runs", "zerados")' in ADMIN
    assert "_contagem_decisoes_log" in ADMIN
    assert "approved7" in ADMIN
    assert "rejected7" in ADMIN
    assert "errors24" in ADMIN
    assert "datetime(created_at) >= datetime('now','-7 days')" in ADMIN


def test_historico_tem_filtros_pesquisa_e_limite_de_consulta():
    assert 'value="moderation"' in ADMIN
    assert 'value="admin"' in ADMIN
    assert 'value="errors"' in ADMIN
    assert "HistoricoBuscaModal" in ADMIN
    assert "ORDER BY id DESC LIMIT 200" in ADMIN


def test_paineis_operacionais_validam_moderador_e_dono():
    assert "class DashboardOperacionalView" in ADMIN
    assert "class HistoricoAuditoriaView" in ADMIN
    assert "interaction.user.id != self.user_id" in ADMIN
    assert "eh_moderador(interaction.user, self.bot.db)" in ADMIN
