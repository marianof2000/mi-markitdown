from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    import tomli as tomllib  # type: ignore[no-redef]


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.toml"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Contrato: cargar un archivo TOML de configuración.

    Precondiciones: `path` apunta a un archivo TOML legible.
    Postcondiciones: devuelve la configuración como diccionario.
    """
    with path.open("rb") as config_file:
        return tomllib.load(config_file)


CONFIG = load_config()
PATHS_CONFIG = CONFIG.get("paths", {})
CONVERSION_CONFIG = CONFIG.get("conversion", {})
OUTPUT_DIR = BASE_DIR / str(PATHS_CONFIG.get("output_dir", "output"))
OVERWRITE_OUTPUT = bool(CONVERSION_CONFIG.get("overwrite", False))
MAX_UPLOAD_BYTES = int(CONVERSION_CONFIG.get("max_upload_mb", 50)) * 1024 * 1024
READ_CHUNK_BYTES = 1024 * 1024
ALLOWED_EXTENSIONS = {
    extension.lower()
    for extension in CONVERSION_CONFIG.get("allowed_extensions", [])
}
