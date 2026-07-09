from __future__ import annotations

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .config import DEFAULT_ENGINE, STATIC_DIR, TEMPLATES_DIR
from .converter import convert_upload


def create_app() -> FastAPI:
    """Contrato: construir la aplicación FastAPI de Mi-Markitdown.

    Precondiciones: existen los directorios de templates y archivos estáticos.
    Postcondiciones: devuelve una app con rutas web, API y montaje de estáticos.
    """
    app = FastAPI(title="Mi-Markitdown")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        """Contrato: servir la interfaz web principal.

        Precondiciones: `templates/index.html` existe y es legible.
        Postcondiciones: devuelve la respuesta de archivo HTML.
        """
        html = (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(html)

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
