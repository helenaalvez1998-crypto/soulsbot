"""Política de recompensas de progressão do Gwent do Coliseu."""

# Marcos cumulativos de vitórias ranqueadas que concedem um drop adicional.
MARCOS_VITORIAS = (5, 10, 25, 50, 100)

# Limita a exploração de partidas combinadas sem retirar XP/MMR de partidas legítimas.
LIMITE_DROPS_VITORIA_24H = 3


def marco_de_vitorias(total_vitorias: int) -> int | None:
    """Retorna o marco atingido exatamente nesta vitória, se houver."""
    total = int(total_vitorias)
    return total if total in MARCOS_VITORIAS else None


async def conceder_drops_de_vitoria(tx, database, user_id: int, match_id: int,
                                     total_vitorias: int) -> tuple[str, str]:
    """Concede drop normal limitado e drop de marco único dentro da transação da partida.

    Retorna (event_key_vitoria, event_key_marco). Chaves vazias significam que
    não houve drop normal por limite diário ou que nenhum marco foi alcançado.
    """
    uid = int(user_id)
    drop_event_key = ""
    milestone_event_key = ""
    recentes = await tx._one(
        """SELECT COUNT(*) AS total FROM cartas_recompensas
           WHERE user_id=? AND origin='gwent_vitoria'
             AND created_at>=datetime('now','-1 day')""",
        (uid,),
    )
    if int(recentes["total"] or 0) < LIMITE_DROPS_VITORIA_24H:
        drop_event_key = f"gwent:vitoria:{int(match_id)}:{uid}"
        await database._coliseu_drop_tx(
            tx, uid, drop_event_key, origem="gwent_vitoria"
        )

    marco = marco_de_vitorias(total_vitorias)
    if marco is not None:
        milestone_event_key = f"gwent:marco:{uid}:{marco}"
        await database._coliseu_drop_tx(
            tx, uid, milestone_event_key, origem=f"gwent_marco_{marco}_vitorias"
        )
    return drop_event_key, milestone_event_key
