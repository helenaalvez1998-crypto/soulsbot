"""Execução transacional do Laboratório de Transmutação — V34.

Geração, renderização e validação são preparadas antes do débito. A execução
revalida propriedade, deck e saldo dentro de BEGIN IMMEDIATE. Somente uma
tentativa legítima (sucesso ou falha aleatória) consome recursos.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path
from typing import Any, Iterable

from sistemas.afinidades import analisar_compatibilidade, classificar_carta, validar_ingredientes
from sistemas.economia_transmutacao import calcular_orcamento, validar_saldo
from sistemas.gerador_cartas import gerar_carta_procedural, validar_definicao_gerada
from sistemas.arte_cartas_geradas import gerar_arte_original, persistir_arte_original, verificar_arte


def _scoped_tx_key(owner_id: int, tx_key: str) -> str:
    """Deriva chave interna por proprietário para impedir colisões entre contas."""
    raw = f"{int(owner_id)}:{tx_key}".encode("utf-8")
    return "owner_v1_" + hashlib.sha256(raw).hexdigest()


def _rowdict(row: Any) -> dict[str, Any]:
    return dict(row) if row is not None else {}


def _carta_catalogo(card_id: str) -> dict[str, Any]:
    from sistemas.cartas import get_carta
    card = get_carta(str(card_id))
    if card is None:
        raise RuntimeError(f"Definição canônica ausente para ingrediente {card_id}.")
    data = card.para_dict()
    return data


def _snapshot_ingrediente(row: Any) -> dict[str, Any]:
    item = _rowdict(row)
    card = _carta_catalogo(item["card_id"])
    card.update({
        "id": str(item["card_id"]),
        "card_id": str(item["card_id"]),
        "exemplar_id": int(item["id"]),
        "raridade": str(item["rarity"]),
        "raridade_exemplar": str(item["rarity"]),
        "poder": int(item["power"]),
        "origin_type": str(item.get("origin_type") or ""),
        "is_sacrificable": bool(item.get("is_sacrificable", 1)),
    })
    return card


async def executar_transmutacao(
    db: Any,
    user_id: int,
    exemplar_ids: Iterable[int],
    *,
    catalyst_active: bool = False,
    catalyst_key: str | None = None,
    tx_key: str | None = None,
) -> dict[str, Any]:
    """Executa tentativa idempotente; erro técnico propaga e reverte o banco."""
    owner = int(user_id)
    ids = [int(x) for x in exemplar_ids]
    if not 3 <= len(ids) <= 5 or len(set(ids)) != len(ids) or any(x <= 0 for x in ids):
        return {"status": "ingredientes_invalidos", "consumo_executado": False}
    key = str(tx_key or secrets.token_hex(16))
    if len(key) > 100 or not key.strip():
        return {"status": "chave_invalida", "consumo_executado": False}
    persisted_key = _scoped_tx_key(owner, key)

    arte_path: str | None = None
    try:
        async with db.transaction() as tx:
            previous = await tx._one(
                "SELECT status,generated_card_id,probability,roll FROM cartas_transmutacoes WHERE tx_key=?",
                (persisted_key,),
            )
            if previous:
                return {
                    "status": "repetida", "resultado_anterior": str(previous["status"]),
                    "generated_card_id": previous["generated_card_id"],
                    "probability": previous["probability"], "roll": previous["roll"],
                    "consumo_executado": False,
                }

            placeholders = ",".join("?" for _ in ids)
            rows = await tx._all(
                f"""SELECT id,user_id,card_id,rarity,power,source,origin_type,origin_card_id,is_sacrificable
                    FROM cartas_exemplares WHERE user_id=? AND id IN ({placeholders})""",
                (owner, *ids),
            )
            if len(rows) != len(ids):
                return {"status": "ingredientes_nao_encontrados_ou_sem_propriedade",
                        "consumo_executado": False}
            by_id = {int(r["id"]): r for r in rows}
            rows = [by_id[x] for x in ids]

            deck = await tx._one(
                "SELECT exemplar_ids_json FROM cartas_gwent_decks WHERE user_id=?", (owner,)
            )
            active_deck_ids = set()
            if deck:
                try:
                    active_deck_ids = {int(x) for x in json.loads(deck["exemplar_ids_json"] or "[]")}
                except (TypeError, ValueError, json.JSONDecodeError):
                    raise RuntimeError("Deck ativo possui exemplar_ids_json inválido; execução bloqueada.")
            if active_deck_ids.intersection(ids):
                return {"status": "ingrediente_equipado_no_deck", "consumo_executado": False}

            ingredients = [_snapshot_ingrediente(r) for r in rows]
            valid, reason = validar_ingredientes(ingredients)
            if not valid:
                return {"status": "ingredientes_bloqueados", "motivo": reason,
                        "consumo_executado": False}

            compatibility = analisar_compatibilidade(ingredients)
            generated_id = "transmutacao_" + secrets.token_hex(12)
            seed = secrets.token_hex(32)
            proposal = gerar_carta_procedural(
                ingredients, seed=seed, generated_id=generated_id,
                balanceamento=None,
            )
            if not proposal.get("valido"):
                raise RuntimeError("Falha técnica/estrutural no gerador: " + str(proposal.get("motivo", proposal.get("status"))))
            definition = proposal["definition"]
            valid_definition, errors = validar_definicao_gerada(definition)
            if not valid_definition:
                raise RuntimeError("Definição procedural rejeitada: " + "; ".join(errors))

            rarities = [classificar_carta(x)["raridade"] for x in ingredients]
            from collections import Counter
            factions = Counter(classificar_carta(x)["faccao"] for x in ingredients)
            same_faction = bool(factions and factions.most_common(1)[0][1] == len(ingredients))
            from sistemas.catalisadores import obter_efeito, validar_afinidade
            catalyst_effect = obter_efeito(catalyst_key, legacy_active=bool(catalyst_active))
            ingredient_affinities = sorted({a for item in ingredients for a in __import__(
                "sistemas.afinidades", fromlist=["classificar_carta"]).classificar_carta(item)["afinidades"]})
            if not validar_afinidade(catalyst_effect, ingredient_affinities):
                return {"status": "catalisador_incompativel", "motivo": "O catalisador exige afinidade " + str(catalyst_effect.afinidade_requerida) + ".", "consumo_executado": False}
            quote = calcular_orcamento(
                definition["raridade"], int(compatibility["score"]),
                same_faction, bool(catalyst_active), catalyst_key=catalyst_key,
            )
            balances_rows = await tx._all(
                "SELECT material_key,quantidade FROM cartas_materiais_transmutacao WHERE user_id=?",
                (owner,),
            )
            balances = {str(r["material_key"]): int(r["quantidade"]) for r in balances_rows}
            missing = validar_saldo(quote.costs, balances)
            if missing:
                return {"status": "materiais_insuficientes", "faltantes": missing,
                        "quote": quote.__dict__, "consumo_executado": False}

            roll = secrets.randbelow(10_000) / 100.0
            success = roll < quote.final_chance
            stored = None
            if success:
                # Arte é preparada e validada antes do débito. Falha legítima não precisa de arte.
                definition_for_art = dict(definition)
                definition_for_art.update({"owner_id": owner})
                image_bytes = gerar_arte_original(definition_for_art)
                stored = persistir_arte_original(definition_for_art, image_bytes)
                arte_path = str(stored["storage_path"])
                if not verificar_arte(arte_path, stored["content_hash"]):
                    raise RuntimeError("Arte gerada não passou na verificação de integridade.")
            snapshot = json.dumps(
                [{"exemplar_id": int(r["id"]), "card_id": str(r["card_id"]),
                  "rarity": str(r["rarity"]), "power": int(r["power"])} for r in rows],
                ensure_ascii=False, separators=(",", ":"),
            )
            # Debita materiais e ingredientes apenas após a geração/arte terem sido validadas.
            for material_key, amount in quote.costs.items():
                if amount <= 0:
                    continue
                cur = await tx.conn.execute(
                    """UPDATE cartas_materiais_transmutacao
                       SET quantidade=quantidade-?,updated_at=CURRENT_TIMESTAMP
                       WHERE user_id=? AND material_key=? AND quantidade>=?""",
                    (int(amount), owner, material_key, int(amount)),
                )
                if cur.rowcount != 1:
                    raise RuntimeError("Saldo mudou durante a tentativa; transação revertida.")
                await tx.conn.execute(
                    """INSERT INTO cartas_movimentacoes
                       (user_id,action,card_id,resource,amount,source)
                       VALUES (?,?,?,?,?,?)""",
                    (owner, "transmutacao_consumo", "transmutacao", material_key,
                     -int(amount), key),
                )
            for row in rows:
                cur = await tx.conn.execute(
                    "DELETE FROM cartas_exemplares WHERE id=? AND user_id=?",
                    (int(row["id"]), owner),
                )
                if cur.rowcount != 1:
                    raise RuntimeError("Ingrediente deixou de pertencer ao jogador; transação revertida.")
                await tx.conn.execute(
                    """INSERT INTO cartas_movimentacoes
                       (user_id,action,card_id,exemplar_id,rarity_before,resource,amount,source)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (owner, "transmutacao_sacrificio", str(row["card_id"]), int(row["id"]),
                     str(row["rarity"]), "exemplar", -1, key),
                )

            if success:
                definition["owner_id"] = owner
                definition["art_path"] = arte_path
                definition["art_hash"] = stored["content_hash"]
                definition["art_width"] = stored["width"]
                definition["art_height"] = stored["height"]
                await tx.conn.execute(
                    """INSERT INTO cartas_geradas
                       (card_id,owner_id,name,rarity,faction,power,definition_json,
                        art_path,art_status,status,generator_version)
                       VALUES (?,?,?,?,?,?,?,?, 'validated','published','v34')""",
                    (generated_id, owner, definition["nome"], definition["raridade"],
                     definition["faccao"], int(definition["poder"]),
                     json.dumps(definition, ensure_ascii=False, separators=(",", ":")),
                     arte_path),
                )
                await tx.conn.execute(
                    """INSERT INTO cartas_colecao
                       (user_id,card_id,quantidade,source,game_name)
                       VALUES (?,?,1,'transmutacao','Elden Ring')""",
                    (owner, generated_id),
                )
                cur = await tx.conn.execute(
                    """INSERT INTO cartas_exemplares
                       (user_id,card_id,rarity,power,source,origin_type,origin_card_id,is_sacrificable)
                       VALUES (?,?,?,?,?,'transmutacao',?,0)""",
                    (owner, generated_id, definition["raridade"], int(definition["poder"]),
                     "transmutacao", generated_id),
                )
                exemplar_id = cur.lastrowid
                await tx.conn.execute(
                    "UPDATE cartas_geradas SET exemplar_id=? WHERE card_id=? AND owner_id=?",
                    (int(exemplar_id), generated_id, owner),
                )
                if definition.get("habilidade"):
                    await tx.conn.execute(
                        """INSERT INTO cartas_geradas_habilidades(generated_card_id,ability_id,position)
                           VALUES (?,?,0)""",
                        (generated_id, str(definition["habilidade"])),
                    )
                if definition.get("habilidade"):
                    await tx.conn.execute(
                        """UPDATE cartas_geracao_balanceamento
                           SET total_com_habilidade=total_com_habilidade+1,updated_at=CURRENT_TIMESTAMP
                           WHERE id=1"""
                    )
                else:
                    await tx.conn.execute(
                        """UPDATE cartas_geracao_balanceamento
                           SET total_sem_habilidade=total_sem_habilidade+1,updated_at=CURRENT_TIMESTAMP
                           WHERE id=1"""
                    )
                await tx.conn.execute(
                    """INSERT INTO cartas_geradas_artes
                       (generated_card_id,storage_path,content_hash,width,height,status)
                       VALUES (?,?,?,?,?,'validated')""",
                    (generated_id, arte_path, stored["content_hash"],
                     int(stored["width"]), int(stored["height"])),
                )
                await tx.conn.execute(
                    """INSERT INTO cartas_movimentacoes
                       (user_id,action,card_id,exemplar_id,rarity_after,power_after,resource,amount,source)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (owner, "transmutacao_sucesso", generated_id, int(exemplar_id),
                     definition["raridade"], int(definition["poder"]), "carta", 1, key),
                )

            await tx.conn.execute(
                """INSERT INTO cartas_transmutacoes
                   (tx_key,owner_id,status,ingredient_ids_json,ingredient_snapshot_json,
                    probability,roll,seed_hash,generated_card_id,failure_reason,generator_version,completed_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
                (persisted_key, owner, "success" if success else "failed",
                 json.dumps(ids), snapshot, quote.final_chance, roll,
                 hashlib.sha256(seed.encode()).hexdigest(),
                 generated_id if success else None,
                 "" if success else "Falha legítima do ritual.",
                 "v34"),
            )

            return {
                "status": "sucesso" if success else "falha",
                "tx_key": key, "generated_card_id": generated_id if success else None,
                "probability": quote.final_chance, "roll": roll,
                "rarity": definition["raridade"], "costs": quote.costs,
                "compatibility": compatibility, "consumo_executado": True,
                "art_path": arte_path if success else None,
                "exemplar_id": int(exemplar_id) if success else None,
            }
    except BaseException:
        # Se o commit falhar após gravar a arte, remove o arquivo órfão. Recursos ficam intactos.
        if arte_path:
            try:
                Path(arte_path).unlink(missing_ok=True)
            except OSError:
                pass
        raise
