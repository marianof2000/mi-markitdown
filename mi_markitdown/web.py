from __future__ import annotations

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
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

    @app.get("/", response_class=FileResponse)
    async def index() -> FileResponse:
        """Contrato: servir la interfaz web principal.

        Precondiciones: `templates/index.html` existe y es legible.
        Postcondiciones: devuelve la respuesta de archivo HTML.
        """
        return FileResponse(TEMPLATES_DIR / "index.html")

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
