from __future__ import annotations

from pathlib import Path

from mi_markitdown.config import MINERU_BACKEND, MINERU_TIMEOUT_SECONDS

from . import markitdown_engine, mineru_engine


def convert_with_engine(
    path: Path,
    engine: str,
    workspace_dir: Path,
) -> str:
    """Contrato: convertir un archivo local usando el motor solicitado.

    Precondiciones: `path` existe, `engine` está validado y `workspace_dir` es escribible.
    Postcondiciones: devuelve Markdown o propaga un error descriptivo del motor.
    """
    if engine == "markitdown":
        return markitdown_engine.convert_path(path)

    if engine == "mineru":
        return mineru_engine.convert_path(
            path,
            workspace_dir=workspace_dir,
            backend=MINERU_BACKEND,
            timeout_seconds=MINERU_TIMEOUT_SECONDS,
        )

    raise ValueError(f"Motor de conversión no soportado: {engine}")
