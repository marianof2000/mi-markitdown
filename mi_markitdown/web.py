from __future__ import annotations

import json
from html import escape
from string import Template

from fastapi import FastAPI, File, Form, Header, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .config import DEFAULT_ENGINE, STATIC_DIR, TEMPLATES_DIR
from .converter import convert_upload


TRANSLATIONS = {
    "es": {
        "html_lang": "es",
        "page_title": "Mi-Markitdown",
        "eyebrow_converter": "Conversor local",
        "intro_copy": "Subí un documento y descargalo convertido a Markdown.",
        "theme_title": "Cambiar tema",
        "theme_aria": "Cambiar a modo oscuro",
        "theme_to_dark": "Cambiar a modo oscuro",
        "theme_to_light": "Cambiar a modo claro",
        "engine_aria": "Motor de conversión",
        "engine_legend": "Motor",
        "drop_title": "Seleccionar archivo",
        "file_label": "PDF, Word, Excel, PowerPoint, HTML, CSV, JSON, XML, TXT, ZIP o EPUB",
        "convert_button": "Convertir",
        "download_button": "Descargar .md",
        "waiting_status": "Esperando archivo.",
        "result_eyebrow": "Resultado",
        "copy_title": "Copiar Markdown",
        "copy_button": "Copiar",
        "preview_empty": "El contenido convertido va a aparecer acá.",
        "github_title": "Abrir repositorio de Mi-Markitdown en GitHub",
        "github_label": "Abrir repositorio de Mi-Markitdown en GitHub",
        "select_file_first": "Seleccioná un archivo primero.",
        "uploading_file": "Subiendo archivo...",
        "processing_with": "Procesando con {engine}...",
        "preparing_markdown": "Preparando Markdown...",
        "conversion_failed": "No se pudo convertir el archivo.",
        "saving_markdown": "Guardando Markdown...",
        "empty_conversion": "La conversión no devolvió contenido.",
        "conversion_done": "Se convirtió con {engine} en {elapsed} - guardado en {path} - {size} KB Markdown",
        "no_preview": "No hay contenido para mostrar.",
        "no_markdown_to_copy": "Todavía no hay Markdown para copiar.",
        "copied": "Markdown copiado al portapapeles.",
        "copy_failed": "No se pudo copiar el Markdown al portapapeles.",
        "locale": "es-AR",
    },
    "en": {
        "html_lang": "en",
        "page_title": "Mi-Markitdown",
        "eyebrow_converter": "Local converter",
        "intro_copy": "Upload a document and download it converted to Markdown.",
        "theme_title": "Change theme",
        "theme_aria": "Switch to dark mode",
        "theme_to_dark": "Switch to dark mode",
        "theme_to_light": "Switch to light mode",
        "engine_aria": "Conversion engine",
        "engine_legend": "Engine",
        "drop_title": "Select file",
        "file_label": "PDF, Word, Excel, PowerPoint, HTML, CSV, JSON, XML, TXT, ZIP or EPUB",
        "convert_button": "Convert",
        "download_button": "Download .md",
        "waiting_status": "Waiting for a file.",
        "result_eyebrow": "Result",
        "copy_title": "Copy Markdown",
        "copy_button": "Copy",
        "preview_empty": "Converted content will appear here.",
        "github_title": "Open Mi-Markitdown repository on GitHub",
        "github_label": "Open Mi-Markitdown repository on GitHub",
        "select_file_first": "Select a file first.",
        "uploading_file": "Uploading file...",
        "processing_with": "Processing with {engine}...",
        "preparing_markdown": "Preparing Markdown...",
        "conversion_failed": "The file could not be converted.",
        "saving_markdown": "Saving Markdown...",
        "empty_conversion": "The conversion did not return content.",
        "conversion_done": "Converted with {engine} in {elapsed} - saved to {path} - {size} KB Markdown",
        "no_preview": "No content to show.",
        "no_markdown_to_copy": "There is no Markdown to copy yet.",
        "copied": "Markdown copied to clipboard.",
        "copy_failed": "Could not copy Markdown to clipboard.",
        "locale": "en-US",
    },
}


def select_language(accept_language: str | None) -> str:
    """Contrato: elegir el idioma de la interfaz desde `Accept-Language`.

    Precondiciones: `accept_language` puede venir vacío o con valores HTTP estándar.
    Postcondiciones: devuelve el idioma soportado con mayor prioridad o `en` por defecto.
    """
    if not accept_language:
        return "en"

    candidates: list[tuple[float, int, str]] = []
    for position, item in enumerate(accept_language.split(",")):
        parts = [part.strip() for part in item.split(";")]
        language = parts[0].lower()
        if language.startswith("es"):
            supported_language = "es"
        elif language.startswith("en"):
            supported_language = "en"
        else:
            continue

        quality = 1.0
        for parameter in parts[1:]:
            key, separator, value = parameter.partition("=")
            if key.strip().lower() == "q" and separator:
                try:
                    quality = float(value)
                except ValueError:
                    quality = 0.0

        if quality > 0:
            candidates.append((quality, -position, supported_language))

    if not candidates:
        return "en"

    return max(candidates)[2]


def render_template(language: str) -> str:
    """Contrato: renderizar el HTML principal con textos localizados.

    Precondiciones: `language` existe en `TRANSLATIONS` y el template contiene placeholders.
    Postcondiciones: devuelve HTML completo con textos e i18n JSON escapados.
    """
    messages = TRANSLATIONS.get(language, TRANSLATIONS["en"])
    template = Template((TEMPLATES_DIR / "index.html").read_text(encoding="utf-8"))
    values = {key: escape(str(value), quote=True) for key, value in messages.items()}
    values["i18n_json"] = json.dumps(messages, ensure_ascii=False)
    return template.safe_substitute(values)


def create_app() -> FastAPI:
    """Contrato: construir la aplicación FastAPI de Mi-Markitdown.

    Precondiciones: existen los directorios de templates y archivos estáticos.
    Postcondiciones: devuelve una app con rutas web, API y montaje de estáticos.
    """
    app = FastAPI(title="Mi-Markitdown")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index(accept_language: str | None = Header(None)) -> HTMLResponse:
        """Contrato: servir la interfaz web principal en el idioma del navegador.

        Precondiciones: `templates/index.html` existe y es legible.
        Postcondiciones: devuelve la respuesta HTML localizada en español o inglés.
        """
        language = select_language(accept_language)
        return HTMLResponse(render_template(language))

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        """Contrato: servir el favicon principal de la aplicación.

        Precondiciones: `static/favicon.ico` existe y es legible.
        Postcondiciones: devuelve el icono para navegadores y pestañas.
        """
        return Response(
            (STATIC_DIR / "favicon.ico").read_bytes(),
            media_type="image/x-icon",
        )

    @app.get("/health")
    async def health() -> JSONResponse:
        """Contrato: exponer un estado básico de salud de la aplicación.

        Precondiciones: la aplicación pudo inicializar sus rutas.
        Postcondiciones: devuelve un JSON simple útil para chequeos externos.
        """
        return JSONResponse({"status": "ok"})

    @app.post("/api/convert")
    async def convert_file(
        file: UploadFile = File(...),
        engine: str = Form(DEFAULT_ENGINE),
    ) -> JSONResponse:
        """Contrato: exponer la conversión de archivos por HTTP.

        Precondiciones: la petición incluye un campo multipart `file` y opcionalmente `engine`.
        Postcondiciones: devuelve JSON con el Markdown y su ruta guardada, o error HTTP.
        """
        return JSONResponse(await convert_upload(file, engine=engine))

    return app
