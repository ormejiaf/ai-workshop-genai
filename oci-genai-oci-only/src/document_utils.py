"""Funciones pequeñas y reutilizables para enviar documentos a un modelo visual."""

import base64
import mimetypes
from pathlib import Path

import fitz


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".pdf"}
MAX_PDF_PAGES = 3


def list_documents(folder: Path) -> list[Path]:
    if not folder.is_dir():
        raise FileNotFoundError(f"No existe la carpeta de documentos: {folder}")
    documents = sorted(
        path for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    if not documents:
        raise FileNotFoundError(
            "La carpeta no contiene PNG, JPG, WEBP ni PDF para analizar."
        )
    return documents


def image_data_url(image: bytes, name: str) -> str:
    mime = mimetypes.guess_type(name)[0] or "image/png"
    encoded = base64.b64encode(image).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def document_content(folder: Path) -> list[dict]:
    """Convierte imágenes y las primeras páginas de PDF en entradas visuales."""
    content: list[dict] = []
    for path in list_documents(folder):
        content.append({"type": "input_text", "text": f"Archivo: {path.name}"})
        if path.suffix.lower() != ".pdf":
            content.append({
                "type": "input_image",
                "image_url": image_data_url(path.read_bytes(), path.name),
            })
            continue

        pdf = fitz.open(path)
        for page_number, page in enumerate(pdf[:MAX_PDF_PAGES], start=1):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            content.append({
                "type": "input_text",
                "text": f"Página {page_number} de {path.name}",
            })
            content.append({
                "type": "input_image",
                "image_url": image_data_url(pixmap.tobytes("png"), f"{path.stem}.png"),
            })
    return content
