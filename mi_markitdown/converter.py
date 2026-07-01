from __future__ import annotations

import re
import tempfile
from pathlib import Path

from fastapi import HTTPException, UploadFile

from .config import (
    ALLOWED_ENGINES,
    ALLOWED_EXTENSIONS,
    DEFAULT_EXTENSION,
    DEFAULT_ENGINE,
    MAX_UPLOAD_BYTES,
    OUTPUT_DIR,
    OVERWRITE_OUTPUT,
    READ_CHUNK_BYTES,
)
from .engines import convert_with_engine


def safe_output_name(filename: str) -> str:
    """Contrato: generar un nombre seguro para el Markdown de salida.

    Precondiciones: `filename` contiene el nombre original del archivo subido.
    Postcondiciones: devuelve un nombre terminado en la extensión configurada sin separadores inseguros.
    """
    source_name = Path(filename).stem or "documento"
    clean_name = re.sub(r"[^A-Za-z0-9._-]+", "-", source_name).strip(".-")
    extension = DEFAULT_EXTENSION if DEFAULT_EXTENSION.startswith(".") else f".{DEFAULT_EXTENSION}"
    return f"{clean_name or 'documento'}{extension}"


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


def validate_engine(engine: str) -> str:
    """Contrato: validar el motor de conversión solicitado.

    Precondiciones: `engine` proviene del formulario o de la configuración.
    Postcondiciones: devuelve el motor normalizado o lanza `HTTPException`.
    """
    normalized_engine = (engine or DEFAULT_ENGINE).strip().lower()
    if normalized_engine not in ALLOWED_ENGINES:
        allowed = ", ".join(sorted(ALLOWED_ENGINES))
        raise HTTPException(
            status_code=400,
            detail=f"Motor no permitido. Motores aceptados: {allowed}",
        )
    return normalized_engine


def convert_path_to_markdown(
    path: Path,
    engine: str,
    workspace_dir: Path,
) -> str:
    """Contrato: convertir un archivo local a Markdown usando un motor disponible.

    Precondiciones: `path` existe, `engine` está validado y `workspace_dir` es escribible.
    Postcondiciones: devuelve Markdown o propaga el error de conversión.
    """
    return convert_with_engine(path, engine=engine, workspace_dir=workspace_dir)


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


async def convert_upload(
    file: UploadFile,
    engine: str = DEFAULT_ENGINE,
) -> dict[str, str | int]:
    """Contrato: convertir un upload a Markdown, guardarlo y describir el resultado.

    Precondiciones: `file` permite lecturas async por chunks y cierre async.
    Postcondiciones: devuelve nombre, motor, contenido, ruta de salida y tamaño, o lanza `HTTPException`.
    """
    suffix = validate_upload(file)
    selected_engine = validate_engine(engine)

    try:
        with tempfile.TemporaryDirectory(prefix="mi-markitdown-") as temp_dir:
            workspace_dir = Path(temp_dir)
            temp_path = workspace_dir / f"upload{suffix}"
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
                markdown = convert_path_to_markdown(
                    temp_path,
                    engine=selected_engine,
                    workspace_dir=workspace_dir,
                )
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
        "engine": selected_engine,
        "markdown": markdown,
        "output_path": str(output_path.relative_to(OUTPUT_DIR.parent)),
        "size": len(markdown.encode("utf-8")),
    }
