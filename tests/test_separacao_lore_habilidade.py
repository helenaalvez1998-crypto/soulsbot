from sistemas.cartas import CARTAS_POR_ID
from sistemas.gwent import preparar_carta


def test_descricao_narrativa_nao_vira_habilidade_mecanica():
    carta = CARTAS_POR_ID["gwent_unidade_gigante"]
    preparada = preparar_carta(carta.para_dict())
    assert preparada["descricao"] == "Uma presença colossal na linha de frente."
    assert preparada["habilidade_texto"] != preparada["descricao"]
    assert "Recebe +2" in preparada["habilidade_texto"]


def test_carta_sem_texto_de_habilidade_nao_usa_lore_como_fallback():
    carta = {
        "id": "teste_sem_habilidade", "nome": "Teste", "categoria": "Unidade",
        "tipo": "Força", "poder": 3, "raridade": "Comum",
        "descricao": "Uma frase apenas narrativa.",
    }
    preparada = preparar_carta(carta)
    assert preparada["descricao"] == "Uma frase apenas narrativa."
    assert preparada["habilidade_texto"] == "Sem habilidade especial."
