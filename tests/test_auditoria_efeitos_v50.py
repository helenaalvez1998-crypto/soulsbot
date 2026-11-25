from sistemas.auditoria_efeitos import gerar_relatorio_efeitos

def test_todas_habilidades_do_catalogo_tem_categoria_no_motor():
    relatorio = gerar_relatorio_efeitos()
    assert relatorio["habilidades_sem_cobertura"] == []
    assert relatorio["status"] == "ok"

def test_efeitos_de_identidade_estao_separados_do_catalogo_generico():
    relatorio = gerar_relatorio_efeitos()
    assert relatorio["total_identidades"] > 0
    assert all(item["card_id"] and item["handler"] for item in relatorio["efeitos_identidade"])

def test_efeitos_especiais_sem_texto_ficam_explicitos():
    relatorio = gerar_relatorio_efeitos()
    # Relíquias possuem catálogo próprio e não devem ser confundidas com especiais comuns.
    assert "reliquia_godrick" in relatorio["especiais_motor_sem_texto_catalogo"]
