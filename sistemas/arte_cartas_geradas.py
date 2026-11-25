"""Arte original procedural para cartas pessoais do Laboratório (V32).

Gera ilustrações locais determinísticas com Pillow a partir da identidade da carta.
Não depende de imagens externas nem de serviços de terceiros. O arquivo PNG é
persistido por ID de carta e acompanhado por SHA-256 para verificação de integridade.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image

from config import get_data_dir
from sistemas.arte_cartas import _draw_card, validar_imagem_bytes, LARGURA_PADRAO, ALTURA_PADRAO

CARD_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{8,100}$")


def _card_payload(definition: dict[str, Any]) -> dict[str, Any]:
    """Converte a definição pessoal para o contrato do renderer existente."""
    return {
        "id": str(definition["card_id"]),
        "nome": str(definition["nome"]),
        "categoria": "Unidade",
        "tipo": str(definition["tipo"]),
        "faccao": str(definition["faccao"]),
        "raridade": str(definition["raridade"]),
        "poder": int(definition["poder"]),
        "custo": int(definition.get("custo", 0)),
        "habilidade": str(definition.get("habilidade") or ""),
        "descricao": str(definition.get("descricao") or ""),
        "fileira": str(definition["fileira"]),
        "afinidades": list(definition.get("afinidades") or []),
        "afinidade_dominante": str(definition.get("afinidade_dominante") or ""),
        "funcao_tatica": str(definition.get("funcao_tatica") or ""),
        "origem_tipo": "transmutacao",
    }


def gerar_arte_original(definition: dict[str, Any], *, width: int = LARGURA_PADRAO,
                        height: int = ALTURA_PADRAO) -> bytes:
    """Renderiza PNG original determinístico para a identidade individual da carta."""
    card_id = str(definition.get("card_id", ""))
    if not CARD_ID_RE.fullmatch(card_id):
        raise ValueError("ID de carta gerada inválido.")
    required = ("nome", "tipo", "faccao", "raridade", "poder", "fileira")
    if any(k not in definition for k in required):
        raise ValueError("Definição incompleta para geração de arte.")
    if definition.get("origem_tipo") != "transmutacao" or definition.get("is_sacrificable") is not False:
        raise ValueError("A arte do Laboratório exige definição pessoal protegida.")
    card = _card_payload(definition)
    image = _draw_card(card, width=max(240, min(int(width), 1200)),
                       height=max(360, min(int(height), 1800)))
    import io
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    data = buffer.getvalue()
    if not validar_imagem_bytes(data, limite_bytes=15 * 1024 * 1024):
        raise ValueError("Renderer produziu uma imagem inválida.")
    return data


def persistir_arte_original(definition: dict[str, Any], image_bytes: bytes,
                            *, base_dir: Path | None = None) -> dict[str, Any]:
    """Armazena PNG imutável por carta, com gravação atômica e hash."""
    card_id = str(definition.get("card_id", ""))
    owner_id = int(definition.get("owner_id", 0))
    if not CARD_ID_RE.fullmatch(card_id) or owner_id <= 0:
        raise ValueError("Proprietário ou ID permanente inválido.")
    if definition.get("origem_tipo") != "transmutacao":
        raise ValueError("Somente cartas pessoais podem usar este armazenamento.")
    if not validar_imagem_bytes(image_bytes, limite_bytes=15 * 1024 * 1024):
        raise ValueError("PNG inválido ou acima do limite de tamanho.")
    digest = hashlib.sha256(image_bytes).hexdigest()
    root = Path(base_dir) if base_dir is not None else get_data_dir()
    target_dir = root / "cartas_geradas" / str(owner_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{card_id}.png"
    if target.exists():
        existing = hashlib.sha256(target.read_bytes()).hexdigest()
        if existing != digest:
            raise FileExistsError("A arte desta carta já foi gravada e é imutável.")
        return {
            "card_id": card_id, "owner_id": owner_id,
            "storage_path": str(target), "content_hash": digest,
            "width": Image.open(target).width, "height": Image.open(target).height,
            "status": "stored", "idempotent": True,
        }
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix=f".{card_id}.", suffix=".png.tmp",
                                         dir=target_dir, delete=False) as tmp:
            temp_path = Path(tmp.name)
            tmp.write(image_bytes)
            tmp.flush()
            os.fsync(tmp.fileno())
        # Confere novamente o arquivo temporário antes da publicação atômica.
        temp_bytes = temp_path.read_bytes()
        if hashlib.sha256(temp_bytes).hexdigest() != digest or not validar_imagem_bytes(temp_bytes):
            raise ValueError("Falha na verificação do PNG temporário.")
        with Image.open(temp_path) as im:
            width, height = im.size
            im.verify()
        # Hard-link impede sobrescrever um arquivo criado por uma corrida concorrente.
        created = True
        try:
            os.link(temp_path, target)
        except FileExistsError:
            created = False
            existing = hashlib.sha256(target.read_bytes()).hexdigest()
            if existing != digest:
                raise FileExistsError("Conflito: a carta já possui outra arte imutável.")
        return {
            "card_id": card_id, "owner_id": owner_id,
            "storage_path": str(target), "content_hash": digest,
            "width": width, "height": height,
            "status": "stored", "idempotent": not created,
        }
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def verificar_arte(path: str | Path, expected_hash: str) -> bool:
    """Verifica PNG e hash antes de a carta ser marcada como publicável."""
    try:
        p = Path(path)
        data = p.read_bytes()
        if hashlib.sha256(data).hexdigest() != str(expected_hash):
            return False
        if not validar_imagem_bytes(data, limite_bytes=15 * 1024 * 1024):
            return False
        with Image.open(p) as im:
            if im.format != "PNG" or im.width < 240 or im.height < 360:
                return False
            im.verify()
        return True
    except (OSError, ValueError):
        return False


# V44 — manifesto de arte individual e validação de identidade visual.
ARTE_MANIFEST_VERSION = "v44"
FACCOES_VALIDAS = {"Ordem Áurea", "Véu Carmesim", "Lua Negra"}
RARIDADES_VALIDAS = {"Comum", "Rara", "Épica", "Lendária", "Mítica"}


def validar_manifesto_arte(definition: dict[str, Any], image_bytes: bytes,
                           *, provider: str = "procedural_renderer",
                           concept: str | None = None) -> dict[str, Any]:
    """Valida a associação carta/arte antes da persistência.

    Para arte ilustrada externa, o chamador fornece os bytes finais do provedor.
    Este módulo não finge gerar ilustração por IA: o renderer local continua sendo
    uma composição gráfica procedural, não uma pintura original.
    """
    required = ("card_id", "owner_id", "nome", "faccao", "raridade",
                "afinidade_dominante", "funcao_tatica")
    missing = [key for key in required if definition.get(key) in (None, "")]
    if missing:
        raise ValueError("Manifesto incompleto: " + ", ".join(missing))
    if definition.get("faccao") not in FACCOES_VALIDAS:
        raise ValueError("Facção inválida para manifesto de arte.")
    if definition.get("raridade") not in RARIDADES_VALIDAS:
        raise ValueError("Raridade inválida para manifesto de arte.")
    if not validar_imagem_bytes(image_bytes, limite_bytes=15 * 1024 * 1024):
        raise ValueError("Imagem inválida para manifesto.")
    digest = hashlib.sha256(image_bytes).hexdigest()
    return {
        "version": ARTE_MANIFEST_VERSION,
        "card_id": str(definition["card_id"]),
        "owner_id": int(definition["owner_id"]),
        "card_name": str(definition["nome"]),
        "faction": str(definition["faccao"]),
        "rarity": str(definition["raridade"]),
        "affinity": str(definition["afinidade_dominante"]),
        "tactical_role": str(definition["funcao_tatica"]),
        "provider": str(provider),
        "concept": str(concept or ""),
        "image_sha256": digest,
        "unique_asset_key": f"{int(definition['owner_id'])}:{definition['card_id']}",
        "status": "validated",
    }


def persistir_arte_com_manifesto(definition: dict[str, Any], image_bytes: bytes,
                                 *, provider: str = "procedural_renderer",
                                 concept: str | None = None,
                                 base_dir: Path | None = None) -> dict[str, Any]:
    """Persiste imagem e manifesto JSON imutáveis por carta."""
    manifest = validar_manifesto_arte(
        definition, image_bytes, provider=provider, concept=concept
    )
    stored = persistir_arte_original(definition, image_bytes, base_dir=base_dir)
    manifest_path = Path(stored["storage_path"]).with_suffix(".manifest.json")
    payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    if manifest_path.exists():
        if manifest_path.read_bytes() != payload:
            raise FileExistsError("Manifesto da arte já existe e é imutável.")
    else:
        fd, tmp_name = tempfile.mkstemp(prefix=".manifest.", suffix=".tmp", dir=manifest_path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(tmp_name, manifest_path)
            except FileExistsError:
                if manifest_path.read_bytes() != payload:
                    raise FileExistsError("Conflito no manifesto de arte.")
        finally:
            Path(tmp_name).unlink(missing_ok=True)
    return {**stored, "manifest_path": str(manifest_path), "manifest": manifest}
