"""V48 — validação e normalização de arte enviada pelo criador."""
from __future__ import annotations
import io
from PIL import Image, UnidentifiedImageError

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MIN_WIDTH, MIN_HEIGHT = 500, 400
MAX_WIDTH, MAX_HEIGHT = 1200, 960
MIN_RATIO, MAX_RATIO = 1.15, 1.36


def normalizar_upload_arte(raw: bytes) -> dict:
    if not raw or len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("Arquivo vazio ou acima de 12 MB.")
    try:
        with Image.open(io.BytesIO(raw)) as image:
            source_format = str(image.format or "").upper()
            if source_format not in {"PNG", "JPEG", "WEBP"}:
                raise ValueError("Formato aceito: PNG, JPG ou WEBP.")
            image.verify()
        with Image.open(io.BytesIO(raw)) as image:
            width, height = image.size
            if width > 4096 or height > 4096:
                raise ValueError("Dimensões originais acima do limite de 4096 pixels.")
            ratio = width / max(1, height)
            if width < MIN_WIDTH or height < MIN_HEIGHT or not MIN_RATIO <= ratio <= MAX_RATIO:
                raise ValueError("A imagem deve ter no mínimo 500×400 e proporção horizontal próxima de 5:4.")
            image = image.convert("RGB")
            image.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="PNG", optimize=True)
            return {"image_bytes": output.getvalue(), "width": image.width,
                    "height": image.height, "source_format": source_format,
                    "format": "PNG"}
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Imagem inválida ou corrompida.") from exc
