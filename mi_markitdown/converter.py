from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
from markitdown import MarkItDown

from .config import (
    ALLOWED_EXTENSIONS,
    MAX_UPLOAD_BYTES,
    OUTPUT_DIR,
    OVERWRITE_OUTPUT,
    READ_CHUNK_BYTES,
)


def safe_output_name(filename: str) -> str:
    """Contrato: generar un nombre seguro para el Markdown de salida.

    Precondiciones: `filename` contiene el nombre original del archivo subido.
    Postcondiciones: devuelve un nombre terminado en `.md` sin separadores inseguros.
    """
    source_name = Path(filename).stem or "documento"
    clean_name = re.sub(r"[^A-Za-z0-9._-]+", "-", source_name).strip(".-")
    return f"{clean_name or 'documento'}.md"


def validate_upload(upload: UploadFile) -> str:
    """Contrato: validar metadatos mínimos del archivo subido.

    Precondiciones: `upload` expone `filename` como lo hace FastAPI `UploadFile`.
    Postcondiciones: devuelve la extensión normalizada o lanza `HTTPException`.
    """
    if not upload.filename:
        raise HTTPException(status_code=400, detail="Subí un archivo para convertir.")

    suffix = Path(upload.filename).suffix.lower()
    if not suffix:
        raise HTTPException(
            status_code=400,
            detail="El archivo debe tener una extensión para poder validar el formato.",
        )

    if ALLOWED_EXTENSIONS and suffix not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Formato no permitido. Extensiones aceptadas: {allowed}",
        )

    return suffix


def extract_markdown(result: Any) -> str:
    """Contrato: obtener texto Markdown desde el resultado de MarkItDown.

    Precondiciones: `result` puede exponer `text_content`, `markdown` o ser convertible a texto.
    Postcondiciones: devuelve una cadena con el contenido convertido.
    """
    for attribute in ("text_content", "markdown"):
        value = getattr(result, attribute, None)
        if isinstance(value, str):
            return value
    return str(result)


def convert_path_to_markdown(path: Path) -> str:
    """Contrato: convertir un archivo local a Markdown usando MarkItDown.

    Precondiciones: `path` apunta a un archivo existente y legible por el proceso.
    Postcondiciones: devuelve Markdown o propaga el error de conversión.
    """
    result = MarkItDown(enable_plugins=False).convert(path)
    return extract_markdown(result)


def next_available_path(path: Path) -> Path:
    """Contrato: resolver una ruta disponible sin sobrescribir archivos existentes.

    Precondiciones: `path` apunta al nombre deseado de salida.
    Postcondiciones: devuelve `path` si no existe o una variante con sufijo numérico.
    """
    if not path.exists():
        return path

    for counter in range(1, 10_000):
        candidate = path.with_name(f"{path.stem}-{counter}{path.suffix}")
        if not candidate.exists():
            return candidate

    raise RuntimeError("No se pudo encontrar un nombre disponible para el Markdown.")


def save_markdown(
    markdown: str,
    filename: str,
    output_dir: Path | None = None,
    overwrite: bool = OVERWRITE_OUTPUT,
) -> Path:
    """Contrato: persistir Markdown en el directorio de salida.

    Precondiciones: `markdown` es texto y `filename` es un nombre de archivo seguro.
    Postcondiciones: crea el directorio si falta, escribe el archivo y devuelve su ruta.
    """
    output_dir = output_dir or OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    if not overwrite:
        output_path = next_available_path(output_path)

    output_path.write_text(markdown, encoding="utf-8")
    return output_path


async def convert_upload(file: UploadFile) -> dict[str, str | int]:
    """Contrato: convertir un upload a Markdown, guardarlo y describir el resultado.

    Precondiciones: `file` permite lecturas async por chunks y cierre async.
    Postcondiciones: devuelve nombre, contenido, ruta de salida y tamaño, o lanza `HTTPException`.
    """
    suffix = validate_upload(file)

    try:
        with tempfile.TemporaryDirectory(prefix="mi-markitdown-") as temp_dir:
            temp_path = Path(temp_dir) / f"upload{suffix}"
            size = 0

            with temp_path.open("wb") as destination:
                while chunk := await file.read(READ_CHUNK_BYTES):
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        raise HTTPException(
                            status_code=413,
                            detail=f"El archivo supera el límite de {MAX_UPLOAD_BYTES // 1024 // 1024} MB.",
                        )
                    destination.write(chunk)

            if size == 0:
                raise HTTPException(
                    status_code=400,
                    detail="El archivo está vacío.",
                )

            try:
                markdown = convert_path_to_markdown(temp_path)
            except Exception as exc:  # noqa: BLE001 - send a clear conversion error to the UI
                raise HTTPException(
                    status_code=422,
                    detail=f"No se pudo convertir el archivo: {exc}",
                ) from exc
    finally:
        await file.close()

    output_filename = safe_output_name(file.filename)
    output_path = save_markdown(markdown, output_filename)

    return {
        "filename": output_path.name,
        "markdown": markdown,
        "output_path": str(output_path.relative_to(OUTPUT_DIR.parent)),
        "size": len(markdown.encode("utf-8")),
    }
