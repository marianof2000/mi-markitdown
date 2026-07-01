from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from fastapi import HTTPException, UploadFile
import pytest

from mi_markitdown import config, converter


@dataclass
class FakeUploadFile:
    filename: str
    content: bytes
    position: int = 0
    closed: bool = False
    reads: list[int] = field(default_factory=list)

    async def read(self, size: int) -> bytes:
        """Contrato: simular una lectura async por chunks de `UploadFile`.

        Precondiciones: `size` es mayor que cero.
        Postcondiciones: devuelve el próximo chunk o `b""` al finalizar.
        """
        self.reads.append(size)
        if self.position >= len(self.content):
            return b""

        chunk = self.content[self.position : self.position + size]
        self.position += len(chunk)
        return chunk

    async def close(self) -> None:
        """Contrato: simular el cierre async de `UploadFile`.

        Precondiciones: ninguna.
        Postcondiciones: marca el archivo falso como cerrado.
        """
        self.closed = True


def make_upload(filename: str, content: bytes, _content_type: str = "text/plain") -> UploadFile:
    """Contrato: crear un doble de `UploadFile` para tests.

    Precondiciones: `filename` y `content` describen el archivo de prueba.
    Postcondiciones: devuelve un objeto compatible con la parte usada por `convert_upload`.
    """
    return FakeUploadFile(filename=filename, content=content)  # type: ignore[return-value]


def test_home_loads() -> None:
    """Contrato: verificar que el HTML principal contiene textos esperados.

    Precondiciones: el template principal existe.
    Postcondiciones: falla si el contenido base de la UI no está presente.
    """
    html = (config.TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")

    assert "Mi-Markitdown" in html
    assert "Subí un documento" in html


def test_convert_txt_file(monkeypatch, tmp_path) -> None:
    """Contrato: verificar una conversión exitosa y persistida.

    Precondiciones: el conversor se reemplaza por un doble determinístico.
    Postcondiciones: valida payload, archivo guardado y contenido Markdown.
    """
    def fake_convert(_path, engine, workspace_dir):
        """Contrato: simular una conversión exitosa.

        Precondiciones: recibe una ruta cualquiera.
        Postcondiciones: devuelve Markdown fijo.
        """
        return "# Hola\n\nTexto convertido.\n"

    output_dir = tmp_path / "output"
    monkeypatch.setattr(converter, "convert_path_to_markdown", fake_convert)
    monkeypatch.setattr(converter, "OUTPUT_DIR", output_dir)

    payload = asyncio.run(converter.convert_upload(make_upload("nota.txt", b"Hola")))

    assert payload == {
        "filename": "nota.md",
        "engine": "markitdown",
        "markdown": "# Hola\n\nTexto convertido.\n",
        "output_path": "output/nota.md",
        "size": 26,
    }
    assert (output_dir / "nota.md").read_text(encoding="utf-8") == "# Hola\n\nTexto convertido.\n"


def test_convert_with_mineru_engine(monkeypatch, tmp_path) -> None:
    """Contrato: verificar que se puede seleccionar MinerU como motor.

    Precondiciones: el conversor se reemplaza por un doble determinístico.
    Postcondiciones: valida que el payload informe `mineru` como motor usado.
    """
    def fake_convert(_path, engine, workspace_dir):
        """Contrato: simular una conversión con MinerU.

        Precondiciones: recibe ruta, motor y workspace temporal.
        Postcondiciones: devuelve Markdown fijo y valida el motor.
        """
        assert engine == "mineru"
        assert workspace_dir.exists()
        return "# MinerU\n"

    output_dir = tmp_path / "output"
    monkeypatch.setattr(converter, "convert_path_to_markdown", fake_convert)
    monkeypatch.setattr(converter, "OUTPUT_DIR", output_dir)

    payload = asyncio.run(
        converter.convert_upload(make_upload("nota.pdf", b"PDF"), engine="mineru")
    )

    assert payload["filename"] == "nota.md"
    assert payload["engine"] == "mineru"
    assert payload["markdown"] == "# MinerU\n"
    assert payload["output_path"] == "output/nota.md"


def test_convert_does_not_overwrite_existing_output(monkeypatch, tmp_path) -> None:
    """Contrato: verificar que una conversión no pisa un Markdown existente.

    Precondiciones: ya existe un archivo con el nombre de salida esperado.
    Postcondiciones: valida que se use un sufijo numérico para el nuevo archivo.
    """
    def fake_convert(_path, engine, workspace_dir):
        """Contrato: simular una conversión exitosa.

        Precondiciones: recibe una ruta cualquiera.
        Postcondiciones: devuelve Markdown fijo.
        """
        return "# Nuevo\n"

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "nota.md").write_text("# Existente\n", encoding="utf-8")

    monkeypatch.setattr(converter, "convert_path_to_markdown", fake_convert)
    monkeypatch.setattr(converter, "OUTPUT_DIR", output_dir)

    payload = asyncio.run(converter.convert_upload(make_upload("nota.txt", b"Hola")))

    assert payload["filename"] == "nota-1.md"
    assert payload["engine"] == "markitdown"
    assert payload["output_path"] == "output/nota-1.md"
    assert (output_dir / "nota.md").read_text(encoding="utf-8") == "# Existente\n"
    assert (output_dir / "nota-1.md").read_text(encoding="utf-8") == "# Nuevo\n"


def test_rejects_unsupported_engine() -> None:
    """Contrato: verificar rechazo de motores no permitidos.

    Precondiciones: se entrega un motor fuera de configuración.
    Postcondiciones: falla si no se lanza `HTTPException` 400.
    """
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            converter.convert_upload(make_upload("nota.txt", b"Hola"), engine="otro")
        )

    assert exc_info.value.status_code == 400
    assert "Motor no permitido" in exc_info.value.detail


def test_rejects_file_without_extension() -> None:
    """Contrato: verificar rechazo de archivos sin extensión.

    Precondiciones: se entrega un upload con nombre sin sufijo.
    Postcondiciones: falla si no se lanza `HTTPException` 400.
    """
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(converter.convert_upload(make_upload("nota", b"Hola")))

    assert exc_info.value.status_code == 400
    assert "extensión" in exc_info.value.detail


def test_rejects_unsupported_extension() -> None:
    """Contrato: verificar rechazo de extensiones no permitidas.

    Precondiciones: se entrega un upload con extensión fuera de configuración.
    Postcondiciones: falla si no se lanza `HTTPException` 400.
    """
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            converter.convert_upload(
                make_upload("script.exe", b"Hola", "application/octet-stream")
            )
        )

    assert exc_info.value.status_code == 400
    assert "Formato no permitido" in exc_info.value.detail


def test_rejects_empty_file() -> None:
    """Contrato: verificar rechazo de archivos vacíos.

    Precondiciones: se entrega un upload permitido pero sin contenido.
    Postcondiciones: falla si no se lanza `HTTPException` 400.
    """
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(converter.convert_upload(make_upload("vacio.txt", b"")))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "El archivo está vacío."


def test_rejects_oversized_file(monkeypatch) -> None:
    """Contrato: verificar rechazo cuando se supera el límite de tamaño.

    Precondiciones: el límite se reduce para el caso de prueba.
    Postcondiciones: falla si no se lanza `HTTPException` 413.
    """
    monkeypatch.setattr(converter, "MAX_UPLOAD_BYTES", 3)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(converter.convert_upload(make_upload("grande.txt", b"1234")))

    assert exc_info.value.status_code == 413
    assert "límite" in exc_info.value.detail


def test_reports_conversion_errors(monkeypatch) -> None:
    """Contrato: verificar que los errores de conversión se reportan como HTTP 422.

    Precondiciones: el conversor se reemplaza por un doble que falla.
    Postcondiciones: falla si el error no se traduce a `HTTPException` 422.
    """
    def fake_convert(_path, engine, workspace_dir):
        """Contrato: simular una falla de conversión.

        Precondiciones: recibe una ruta cualquiera.
        Postcondiciones: lanza `RuntimeError`.
        """
        raise RuntimeError("archivo inválido")

    monkeypatch.setattr(converter, "convert_path_to_markdown", fake_convert)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(converter.convert_upload(make_upload("fallo.txt", b"contenido")))

    assert exc_info.value.status_code == 422
    assert "No se pudo convertir" in exc_info.value.detail
