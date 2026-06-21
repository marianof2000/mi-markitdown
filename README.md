# Mi-Markitdown

Mi-Markitdown es una interfaz web para convertir archivos de distintos formatos a Markdown usando [`microsoft/markitdown`](https://github.com/microsoft/markitdown).

## Requisitos

- Python 3.12
- Un entorno virtual activo

## Instalación

Con `pyenv-virtualenv`:

```bash
pyenv install 3.12.7
pyenv virtualenv 3.12.7 mi-markitdown-3.12.7
pyenv local mi-markitdown-3.12.7
pip install -r requirements.txt
```

Alternativa con `venv`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

Levantar la aplicación web:

```bash
python app.py
```

Luego abrir:

```text
http://127.0.0.1:8000
```

Para desarrollo con recarga automática:

```bash
uvicorn app:app --reload
```

También se puede usar la CLI de MarkItDown directamente:

```bash
markitdown archivo.pdf > archivo.md
```

## Funcionamiento

La aplicación expone una interfaz web local para subir un archivo, convertirlo a Markdown y ver el resultado en pantalla. Después de cada conversión:

- El Markdown se muestra en la vista previa.
- El navegador permite descargar el `.md`.
- El archivo generado se guarda en el directorio de salida del proyecto.

## Formatos soportados

La app acepta formatos comunes soportados por MarkItDown, incluyendo PDF, Word, PowerPoint, Excel, HTML, CSV, JSON, XML, TXT, ZIP y EPUB. La lista editable está en `config.toml`.

Cada conversión guarda el Markdown generado dentro del directorio configurado en `paths.output_dir`; por defecto, `output/`.

## Configuración

La configuración principal está en `config.toml`.

```toml
[paths]
output_dir = "output"

[conversion]
overwrite = false
max_upload_mb = 50
allowed_extensions = [".pdf", ".docx", ".xlsx", ".txt"]
```

- `paths.output_dir`: carpeta donde se guardan los Markdown generados.
- `conversion.overwrite`: si es `false`, no pisa archivos existentes y crea nombres como `documento-1.md`.
- `conversion.max_upload_mb`: tamaño máximo permitido por archivo.
- `conversion.allowed_extensions`: extensiones aceptadas por la API.

## API

La interfaz usa el endpoint:

```text
POST /api/convert
```

Debe enviarse un formulario `multipart/form-data` con el campo `file`.

Respuesta exitosa:

```json
{
  "filename": "documento.md",
  "markdown": "# Contenido convertido",
  "output_path": "output/documento.md",
  "size": 22
}
```

Errores contemplados:

- Archivo sin nombre.
- Archivo sin extensión.
- Extensión no permitida.
- Archivo vacío.
- Archivo que supera el límite de tamaño.
- Error interno de conversión de MarkItDown.

## Estructura inicial

```text
.
|-- AGENTS.md
|-- app.py
|-- README.md
|-- config.toml
|-- mi_markitdown/
|-- requirements.txt
|-- static/
|-- templates/
|-- tests/
`-- .gitignore
```

## Arquitectura

- `app.py`: punto de entrada para `uvicorn app:app`.
- `mi_markitdown/config.py`: carga `config.toml` y expone rutas, límites y extensiones.
- `mi_markitdown/converter.py`: valida uploads, convierte con MarkItDown, guarda el `.md` y arma la respuesta.
- `mi_markitdown/web.py`: crea la aplicación FastAPI y registra rutas.
- `static/`: JavaScript y estilos de la interfaz.
- `templates/`: HTML principal.
- `tests/`: tests de casos felices y casos borde.

## Notas de desarrollo

- Mantener las dependencias declaradas en `requirements.txt`.
- Evitar commitear archivos generados, entornos virtuales o datos sensibles.
- Documentar nuevos comandos de uso en este README.
- `output/` está ignorado por git porque contiene resultados generados.
- El soporte para `markitdown-ocr` queda como mejora futura: requiere habilitar plugins y configurar cliente/modelo LLM.

## Tests

```bash
pytest -q
```
