from __future__ import annotations

import uvicorn

from mi_markitdown.web import create_app


app = create_app()


def main() -> None:
    """Contrato: ejecutar el servidor local de desarrollo.

    Precondiciones: las dependencias de `requirements.txt` están instaladas.
    Postcondiciones: inicia Uvicorn en `http://127.0.0.1:8000` hasta que se interrumpa.
    """
    uvicorn.run("app:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
