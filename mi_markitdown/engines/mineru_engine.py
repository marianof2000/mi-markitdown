from __future__ import annotations

import subprocess
from pathlib import Path
from shutil import which


def find_markdown_output(output_dir: Path, source_path: Path) -> Path:
    """Contrato: localizar el Markdown principal generado por MinerU.

    Precondiciones: `output_dir` contiene la salida producida por la CLI de MinerU.
    Postcondiciones: devuelve el `.md` más probable o lanza `RuntimeError`.
    """
    markdown_files = sorted(output_dir.rglob("*.md"))
    if not markdown_files:
        raise RuntimeError("MinerU no generó ningún archivo Markdown.")

    source_stem = source_path.stem.lower()
    for markdown_file in markdown_files:
        if markdown_file.stem.lower() == source_stem:
            return markdown_file

    return max(markdown_files, key=lambda path: path.stat().st_size)


def convert_path(
    path: Path,
    workspace_dir: Path,
    backend: str,
    timeout_seconds: int,
) -> str:
    """Contrato: convertir un archivo local a Markdown usando la CLI de MinerU.

    Precondiciones: la CLI `mineru` está instalada y `workspace_dir` es escribible.
    Postcondiciones: devuelve el Markdown generado o lanza un error descriptivo.
    """
    if which("mineru") is None:
        raise RuntimeError(
            "MinerU no está instalado. Instalalo con `uv sync --extra dev --extra mineru`."
        )

    output_dir = workspace_dir / "mineru-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    command = [
        "mineru",
        "-p",
        str(path),
        "-o",
        str(output_dir),
        "-b",
        backend,
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"MinerU superó el tiempo máximo configurado de {timeout_seconds} segundos."
        ) from exc

    if completed.returncode != 0:
        error = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"MinerU falló: {error}")

    markdown_path = find_markdown_output(output_dir, path)
    return markdown_path.read_text(encoding="utf-8")
