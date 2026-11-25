"""Auditoria de fidelidade do compêndio ao catálogo e ao motor de batalha."""
from __future__ import annotations

from sistemas.cartas import HABILIDADES, CARTAS_SEM_EFEITO_IDS
from sistemas.gwent import (
    HABILIDADES_UNIDADE_IMPLEMENTADAS,
    HABILIDADES_ESPECIAIS_IMPLEMENTADAS,
    CARD_IDENTITY_ABILITIES,
)

def gerar_relatorio_efeitos() -> dict:
    unidade = sorted(k for k in HABILIDADES if k in HABILIDADES_UNIDADE_IMPLEMENTADAS)
    especial = sorted(k for k in HABILIDADES if k in HABILIDADES_ESPECIAIS_IMPLEMENTADAS)
    sem_motor = sorted(k for k in HABILIDADES if k not in HABILIDADES_UNIDADE_IMPLEMENTADAS
                       and k not in HABILIDADES_ESPECIAIS_IMPLEMENTADAS)
    identidades = [
        {"card_id": card_id, "nome": info["name"], "texto": info["text"],
         "handler": info["effect"]}
        for card_id, info in sorted(CARD_IDENTITY_ABILITIES.items())
    ]
    # Relíquias têm catálogo próprio e handlers próprios; são listadas aqui
    # para não serem contabilizadas como habilidades especiais convencionais.
    especiais_sem_cobertura = sorted(
        k for k in HABILIDADES_ESPECIAIS_IMPLEMENTADAS
        if k not in HABILIDADES or k.startswith("reliquia_")
    )
    return {
        "total_catalogo": len(HABILIDADES),
        "habilidades_unidade": [{"id": k, **HABILIDADES[k]} for k in unidade],
        "habilidades_especiais_catalogadas": [{"id": k, **HABILIDADES[k]} for k in especial],
        "habilidades_sem_cobertura": sem_motor,
        "efeitos_identidade": identidades,
        "total_identidades": len(identidades),
        "especiais_motor_sem_texto_catalogo": especiais_sem_cobertura,
        "total_unidades_sem_habilidade": len(CARTAS_SEM_EFEITO_IDS),
        "status": "ok" if not sem_motor else "incompleto",
        "nota": (
            "Cobertura estrutural por contrato de nomes. Não substitui teste de execução "
            "de cada efeito em uma partida real."
        ),
    }
