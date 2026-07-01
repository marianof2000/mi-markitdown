from __future__ import annotations

from pathlib import Path
from typing import Any

from markitdown import MarkItDown


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


def convert_path(path: Path) -> str:
    """Contrato: convertir un archivo local a Markdown usando MarkItDown.

    Precondiciones: `path` apunta a un archivo existente y legible por el proceso.
    Postcondiciones: devuelve Markdown o propaga el error de conversión.
    """
    result = MarkItDown(enable_plugins=False).convert(path)
    return extract_markdown(result)
