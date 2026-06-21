# Mi-Markitdown

Mi-Markitdown es una interfaz web local para convertir documentos a Markdown usando [`microsoft/markitdown`](https://github.com/microsoft/markitdown). Permite subir un archivo desde el navegador, ver el Markdown generado, descargarlo y guardarlo automáticamente en un directorio de salida del proyecto.

## Secciones

- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Uso](#uso)
- [Funcionamiento](#funcionamiento)
- [Formatos soportados](#formatos-soportados)
- [Configuración](#configuración)
- [API](#api)
- [Estructura](#estructura)
- [Arquitectura](#arquitectura)
- [Tests](#tests)
- [Notas de desarrollo](#notas-de-desarrollo)
- [¿Por Qué Markdown Para IA?](#por-qué-markdown-para-ia)

## Requisitos

- Python 3.12
- `pip`
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

Instalación editable opcional, útil para desarrollo:

```bash
pip install -e ".[dev]"
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

La aplicación recibe el archivo subido, lo copia a un directorio temporal del sistema, lo convierte con MarkItDown y elimina esa copia temporal al terminar. El archivo original no se usa desde su ruta de origen.

Después de cada conversión:

- El Markdown se muestra en la vista previa.
- El navegador permite descargar el `.md`.
- El Markdown generado se guarda en el directorio configurado en `paths.output_dir`; por defecto, `output/`.
- Si `overwrite = false`, no se pisan archivos existentes: se generan nombres como `documento-1.md`.

Los archivos cargados y los generados por conversión no deben entrar al repositorio. Por eso `input/`, `output/`, `uploads/`, `exports/` y `tmp/` están ignorados por git.

## Formatos soportados

La app acepta formatos comunes soportados por MarkItDown, incluyendo PDF, Word, PowerPoint, Excel, HTML, CSV, JSON, XML, TXT, ZIP y EPUB. La lista editable está en `config.toml`.

## Configuración

La configuración principal está en `config.toml`.

```toml
[paths]
input_dir = "input"
output_dir = "output"

[conversion]
overwrite = false
max_upload_mb = 50
allowed_extensions = [".pdf", ".docx", ".xlsx", ".txt"]
```

- `paths.input_dir`: carpeta reservada para archivos de entrada si se necesitara un flujo por lotes.
- `paths.output_dir`: carpeta donde se guardan los Markdown generados.
- `conversion.overwrite`: si es `false`, no pisa archivos existentes.
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

## Estructura

```text
.
|-- AGENTS.md
|-- app.py
|-- config.toml
|-- mi_markitdown/
|-- pyproject.toml
|-- README.md
|-- requirements.txt
|-- static/
|-- templates/
|-- tests/
`-- .gitignore
```

## Arquitectura

- `app.py`: punto de entrada para `python app.py` y `uvicorn app:app`.
- `mi_markitdown/config.py`: carga `config.toml` y expone rutas, límites y extensiones.
- `mi_markitdown/converter.py`: valida uploads, convierte con MarkItDown, guarda el `.md` y arma la respuesta.
- `mi_markitdown/web.py`: crea la aplicación FastAPI y registra rutas.
- `static/`: JavaScript y estilos de la interfaz.
- `templates/`: HTML principal.
- `tests/`: tests de casos felices y casos borde.

## Tests

```bash
pytest
```

El `pyproject.toml` configura `pytest` para ejecutar la suite con salida resumida.

## Notas de desarrollo

- Mantener sincronizadas las dependencias de `requirements.txt` y `pyproject.toml`.
- Evitar commitear archivos generados, documentos cargados, entornos virtuales o datos sensibles.
- Documentar nuevos comandos de uso en este README.
- El soporte para `markitdown-ocr` queda como mejora futura: requiere habilitar plugins y configurar cliente/modelo LLM.

## ¿Por Qué Markdown Para IA?

Convertir documentos a Markdown facilita el uso de contenidos en herramientas de Inteligencia Artificial, modelos de lenguaje, sistemas RAG y pipelines de análisis de texto. Muchos formatos originales, como PDF, Word, PowerPoint o Excel, incluyen información visual, estilos, metadatos y estructuras internas que pueden dificultar la extracción limpia del contenido.

Markdown, en cambio, es texto plano con estructura explícita. Permite conservar títulos, subtítulos, listas, tablas simples y bloques de código de una forma fácil de procesar.

Ventajas principales:

- Texto más limpio y con menos ruido visual.
- Mejor interpretación por modelos de lenguaje.
- Mayor compatibilidad con editores, Git, notebooks y herramientas de IA.
- Mejor control de versiones.
- Fragmentación más simple para sistemas RAG.
- Trazabilidad más clara del contenido usado por una IA.

Convertir a Markdown no reemplaza al documento original. En muchos casos conviene conservar ambos: el original como fuente primaria y el Markdown como formato optimizado para procesamiento automático.
