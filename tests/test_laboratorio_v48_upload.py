import io
import pytest
from PIL import Image
from sistemas.arte_upload_criador import normalizar_upload_arte


def image_bytes(size=(1024,819), fmt="PNG"):
    out=io.BytesIO()
    Image.new("RGB",size,(80,90,100)).save(out,format=fmt)
    return out.getvalue()


def test_v48_normalizes_png_and_reports_dimensions():
    result=normalizar_upload_arte(image_bytes())
    assert result["format"]=="PNG"
    assert result["source_format"]=="PNG"
    assert result["width"]<=1200 and result["height"]<=960
    assert result["image_bytes"].startswith(b"\x89PNG")


def test_v48_accepts_jpeg_and_webp():
    assert normalizar_upload_arte(image_bytes(fmt="JPEG"))["source_format"]=="JPEG"
    assert normalizar_upload_arte(image_bytes(fmt="WEBP"))["source_format"]=="WEBP"


def test_v48_rejects_portrait_and_small_images():
    with pytest.raises(ValueError):
        normalizar_upload_arte(image_bytes((400,800)))
    with pytest.raises(ValueError):
        normalizar_upload_arte(image_bytes((300,240)))


def test_v48_rejects_unsupported_and_corrupt_files():
    with pytest.raises(ValueError):
        normalizar_upload_arte(b"not an image")
