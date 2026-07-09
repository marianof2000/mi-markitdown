from __future__ import annotations

import asyncio
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import HTTPException, UploadFile
import httpx
import pytest

from mi_markitdown import config, converter, web
from mi_markitdown.engines import mineru_engine


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


async def request_app(method: str, path: str, **kwargs) -> httpx.Response:
    """Contrato: ejecutar una petición HTTP contra la app ASGI en memoria.

    Precondiciones: `method` y `path` describen una petición válida para la app.
    Postcondiciones: devuelve la respuesta HTTP sin levantar un servidor externo.
    """
    transport = httpx.ASGITransport(app=web.create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


def test_home_loads() -> None:
    """Contrato: verificar que el HTML principal contiene textos esperados.

    Precondiciones: el template principal existe.
    Postcondiciones: falla si el contenido base de la UI no está presente.
    """
    html = (config.TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")

    assert "Mi-Markitdown" in html
    assert "Subí un documento" in html
    assert '<link rel="icon" href="/favicon.ico" sizes="32x32">' in html
    assert '<script src="/static/theme.js?v=workflow-1"></script>' in html
    assert '<script src="/static/app.js?v=workflow-1"></script>' in html
    assert (config.STATIC_DIR / "favicon.ico").is_file()

    accept_match = re.search(r'accept="([^"]+)"', html)
    assert accept_match is not None
    assert set(accept_match.group(1).split(",")) == config.ALLOWED_EXTENSIONS


def test_web_home_route_loads() -> None:
    """Contrato: verificar que la ruta principal sirve la interfaz web.

    Precondiciones: la app FastAPI puede construirse.
    Postcondiciones: falla si `GET /` no devuelve HTML de la aplicación.
    """
    response = asyncio.run(request_app("GET", "/"))

    assert response.status_code == 200
    assert "Mi-Markitdown" in response.text


def test_web_favicon_route_loads() -> None:
    """Contrato: verificar que el favicon está disponible en la ruta estándar.

    Precondiciones: `static/favicon.ico` existe.
    Postcondiciones: falla si `GET /favicon.ico` no devuelve contenido binario.
    """
    response = asyncio.run(request_app("GET", "/favicon.ico"))

    assert response.status_code == 200
    assert response.content.startswith(b"\x00\x00\x01\x00")


def test_web_health_route_returns_ok() -> None:
    """Contrato: verificar el endpoint básico de salud.

    Precondiciones: la app FastAPI puede construirse.
    Postcondiciones: falla si `GET /health` no devuelve estado OK.
    """
    response = asyncio.run(request_app("GET", "/health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_web_convert_route_returns_payload(monkeypatch) -> None:
    """Contrato: verificar el contrato HTTP básico de conversión.

    Precondiciones: el conversor web se reemplaza por un doble determinístico.
    Postcondiciones: valida que `POST /api/convert` devuelva JSON serializable.
    """
    async def fake_convert_upload(file, engine):
        """Contrato: simular la conversión desde la capa web.

        Precondiciones: recibe un upload y el motor solicitado.
        Postcondiciones: devuelve un payload compatible con la API real.
        """
        assert file.filename == "nota.txt"
        assert engine == "markitdown"
        return {
            "filename": "nota.md",
            "engine": engine,
            "markdown": "# Nota\n",
            "output_path": "output/nota.md",
            "size": 7,
        }

    monkeypatch.setattr(web, "convert_upload", fake_convert_upload)
    response = asyncio.run(
        request_app(
            "POST",
            "/api/convert",
            data={"engine": "markitdown"},
            files={"file": ("nota.txt", b"Hola", "text/plain")},
        )
    )

    assert response.status_code == 200
    assert response.json() == {
        "filename": "nota.md",
        "engine": "markitdown",
        "markdown": "# Nota\n",
        "output_path": "output/nota.md",
        "size": 7,
    }


def test_safe_output_name_uses_configured_extension(monkeypatch) -> None:
    """Contrato: verificar que el nombre de salida usa la extensión configurada.

    Precondiciones: `DEFAULT_EXTENSION` se reemplaza por un valor de prueba.
    Postcondiciones: falla si el nombre seguro conserva una extensión hardcodeada.
    """
    monkeypatch.setattr(converter, "DEFAULT_EXTENSION", ".markdown")

    assert converter.safe_output_name("mi documento.pdf") == "mi-documento.markdown"


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


def test_find_markdown_output_prefers_matching_stem(tmp_path) -> None:
    """Contrato: verificar que MinerU prioriza el Markdown con el mismo nombre base.

    Precondiciones: la salida contiene varios Markdown generados.
    Postcondiciones: devuelve el archivo cuyo stem coincide con el documento origen.
    """
    output_dir = tmp_path / "mineru-output"
    output_dir.mkdir()
    (output_dir / "otro.md").write_text("# Otro\n\ncontenido largo\n", encoding="utf-8")
    expected = output_dir / "documento.md"
    expected.write_text("# Documento\n", encoding="utf-8")

    result = mineru_engine.find_markdown_output(output_dir, Path("documento.pdf"))

    assert result == expected


def test_find_markdown_output_uses_largest_file_when_no_stem_matches(tmp_path) -> None:
    """Contrato: verificar fallback al Markdown de mayor tamaño.

    Precondiciones: ningún Markdown coincide con el stem del archivo origen.
    Postcondiciones: devuelve el archivo `.md` más grande.
    """
    output_dir = tmp_path / "mineru-output"
    output_dir.mkdir()
    small = output_dir / "a.md"
    large = output_dir / "b.md"
    small.write_text("# A\n", encoding="utf-8")
    large.write_text("# B\n\ncontenido largo\n", encoding="utf-8")

    result = mineru_engine.find_markdown_output(output_dir, Path("documento.pdf"))

    assert result == large


def test_find_markdown_output_requires_markdown_file(tmp_path) -> None:
    """Contrato: verificar error cuando MinerU no genera Markdown.

    Precondiciones: el directorio de salida no contiene archivos `.md`.
    Postcondiciones: falla si no se lanza `RuntimeError`.
    """
    with pytest.raises(RuntimeError) as exc_info:
        mineru_engine.find_markdown_output(tmp_path, Path("documento.pdf"))

    assert "no generó ningún archivo Markdown" in str(exc_info.value)


def test_mineru_convert_requires_cli(monkeypatch, tmp_path) -> None:
    """Contrato: verificar error claro cuando la CLI de MinerU no está instalada.

    Precondiciones: `which` se reemplaza para simular ausencia de `mineru`.
    Postcondiciones: falla si no se lanza `RuntimeError` con instrucción de instalación.
    """
    source = tmp_path / "documento.pdf"
    source.write_bytes(b"PDF")
    monkeypatch.setattr(mineru_engine, "which", lambda _command: None)

    with pytest.raises(RuntimeError) as exc_info:
        mineru_engine.convert_path(
            source,
            workspace_dir=tmp_path,
            backend="pipeline",
            timeout_seconds=1,
        )

    assert "MinerU no está instalado" in str(exc_info.value)


def test_convert_reports_missing_mineru_with_install_hint(monkeypatch) -> None:
    """Contrato: verificar mensaje accionable cuando falta MinerU.

    Precondiciones: el conversor simula una ausencia de CLI MinerU.
    Postcondiciones: falla si el error no sugiere instalación o cambio de motor.
    """
    def fake_convert(_path, engine, workspace_dir):
        """Contrato: simular ausencia de MinerU durante la conversión.

        Precondiciones: recibe ruta, motor y workspace temporal.
        Postcondiciones: lanza el mismo tipo de error que el motor real.
        """
        raise RuntimeError("MinerU no está instalado.")

    monkeypatch.setattr(converter, "convert_path_to_markdown", fake_convert)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            converter.convert_upload(make_upload("documento.pdf", b"PDF"), engine="mineru")
        )

    assert exc_info.value.status_code == 422
    assert "uv sync --extra dev --extra mineru" in exc_info.value.detail
    assert "elegí MarkItDown" in exc_info.value.detail


def test_mineru_convert_reports_cli_failure(monkeypatch, tmp_path) -> None:
    """Contrato: verificar que una falla de CLI se reporta con stderr/stdout.

    Precondiciones: `subprocess.run` se reemplaza por un resultado fallido.
    Postcondiciones: falla si el error no conserva el detalle devuelto por MinerU.
    """
    source = tmp_path / "documento.pdf"
    source.write_bytes(b"PDF")
    monkeypatch.setattr(mineru_engine, "which", lambda _command: "/usr/bin/mineru")

    def fake_run(*_args, **_kwargs):
        """Contrato: simular una ejecución fallida de MinerU.

        Precondiciones: recibe argumentos compatibles con `subprocess.run`.
        Postcondiciones: devuelve un proceso con código de error y stderr.
        """
        return subprocess.CompletedProcess(
            args=["mineru"],
            returncode=2,
            stdout="",
            stderr="archivo inválido",
        )

    monkeypatch.setattr(mineru_engine.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as exc_info:
        mineru_engine.convert_path(
            source,
            workspace_dir=tmp_path,
            backend="pipeline",
            timeout_seconds=1,
        )

    assert "MinerU falló: archivo inválido" in str(exc_info.value)


def test_mineru_convert_reports_timeout(monkeypatch, tmp_path) -> None:
    """Contrato: verificar mensaje claro cuando MinerU supera el timeout.

    Precondiciones: `subprocess.run` se reemplaza por una excepción de timeout.
    Postcondiciones: falla si no se informa el tiempo máximo configurado.
    """
    source = tmp_path / "documento.pdf"
    source.write_bytes(b"PDF")
    monkeypatch.setattr(mineru_engine, "which", lambda _command: "/usr/bin/mineru")

    def fake_run(*_args, **_kwargs):
        """Contrato: simular una ejecución que supera el timeout.

        Precondiciones: recibe argumentos compatibles con `subprocess.run`.
        Postcondiciones: lanza `TimeoutExpired`.
        """
        raise subprocess.TimeoutExpired(cmd=["mineru"], timeout=3)

    monkeypatch.setattr(mineru_engine.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as exc_info:
        mineru_engine.convert_path(
            source,
            workspace_dir=tmp_path,
            backend="pipeline",
            timeout_seconds=3,
        )

    assert "superó el tiempo máximo configurado de 3 segundos" in str(exc_info.value)


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
