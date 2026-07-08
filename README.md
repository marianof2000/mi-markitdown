# Mi-Markitdown

Mi-Markitdown es una interfaz web local para convertir documentos a Markdown usando dos motores: [`microsoft/markitdown`](https://github.com/microsoft/markitdown) y, de forma opcional, [`opendatalab/MinerU`](https://github.com/opendatalab/MinerU). Permite subir un archivo desde el navegador, elegir el motor de conversión, ver el Markdown generado, descargarlo y guardarlo automáticamente en un directorio de salida del proyecto.

## Secciones

- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Uso](#uso)
- [Funcionamiento](#funcionamiento)
- [Motores de conversión](#motores-de-conversión)
- [Formatos soportados](#formatos-soportados)
- [Configuración](#configuración)
- [API](#api)
- [Estructura](#estructura)
- [Arquitectura](#arquitectura)
- [Tests](#tests)
- [Notas de desarrollo](#notas-de-desarrollo)
- [¿Por qué Markdown para IA?](#por-qué-markdown-para-ia)

## Requisitos

- Python 3.12
- [`uv`](https://docs.astral.sh/uv/)

## Instalación

Clonar el repositorio e instalar dependencias de desarrollo:

```bash
git clone https://github.com/marianof2000/mi-markitdown.git
cd mi-markitdown
uv sync --extra dev
```

Si también querés usar MinerU:

```bash
uv sync --extra dev --extra mineru
```

`uv` crea y mantiene el entorno virtual local en `.venv/`, que está ignorado por git. El archivo `uv.lock` sí debe versionarse para conservar instalaciones reproducibles.

Los archivos `requirements.txt` y `requirements-mineru.txt` se mantienen solo como alternativa legacy para flujos basados en `pip`; la fuente principal de dependencias es `pyproject.toml`.

Alternativa legacy con `pip`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Alternativa legacy con MinerU:

```bash
pip install -r requirements-mineru.txt
```

MinerU puede requerir modelos, más memoria, más espacio en disco, más procesamiento de CPU y más tiempo de conversión que MarkItDown. La configuración incluida usa el backend `pipeline` para CPU.

## Uso

Levantar la aplicación web:

```bash
uv run python app.py
```

Luego abrir:

```text
http://127.0.0.1:8000
```

Para desarrollo con recarga automática:

```bash
uv run uvicorn app:app --reload
```

También se puede usar la CLI de MarkItDown directamente:

```bash
markitdown archivo.pdf > archivo.md
```

Si MinerU está instalado, también se puede usar desde línea de comandos:

```bash
mineru -p archivo.pdf -o output/mineru -b pipeline
```

MinerU genera su salida dentro del directorio indicado con `-o`; entre esos archivos se incluye el Markdown convertido.

## Funcionamiento

La aplicación recibe el archivo subido, lo copia a un directorio temporal del sistema, lo convierte con el motor elegido y elimina esa copia temporal al terminar. El archivo original no se usa desde su ruta de origen.

Después de cada conversión:

- El Markdown se muestra en la vista previa.
- El navegador permite descargar el `.md`.
- El Markdown generado se guarda en el directorio configurado en `paths.output_dir`; por defecto, `output/`.
- El selector de motor permite convertir con `MarkItDown` o con `MinerU` si está instalado.
- Si `overwrite = false`, no se pisan archivos existentes: se generan nombres como `documento-1.md`.

Los archivos cargados y los generados por conversión no deben entrar al repositorio. Por eso `input/`, `output/`, `uploads/`, `exports/` y `tmp/` están ignorados por git.

## Motores de conversión

La aplicación puede trabajar con dos motores:

- [`MarkItDown`](https://github.com/microsoft/markitdown): es el motor por defecto. Suele ser más rápido y liviano para conversiones generales.
- [`MinerU`](https://github.com/opendatalab/MinerU): es opcional y puede producir resultados más precisos, especialmente en documentos PDF complejos, pero consume más procesamiento de CPU y tarda más tiempo.

## Formatos soportados

La app acepta formatos comunes soportados por MarkItDown, incluyendo PDF, Word, PowerPoint, Excel, HTML, CSV, JSON, XML, TXT, ZIP y EPUB. La lista editable está en `config.toml`.

## Configuración

La configuración principal está en `config.toml`.

```toml
[paths]
input_dir = "input"
output_dir = "output"

[conversion]
default_extension = ".md"
default_engine = "markitdown"
allowed_engines = ["markitdown", "mineru"]
overwrite = false
max_upload_mb = 50
allowed_extensions = [
  ".bmp",
  ".csv",
  ".docx",
  ".epub",
  ".html",
  ".htm",
  ".json",
  ".md",
  ".msg",
  ".jpeg",
  ".jpg",
  ".pdf",
  ".png",
  ".pptx",
  ".tif",
  ".tiff",
  ".txt",
  ".webp",
  ".xls",
  ".xlsx",
  ".xml",
  ".zip",
]

[mineru]
backend = "pipeline"
timeout_seconds = 1800
```

- `paths.input_dir`: carpeta reservada para archivos de entrada si se necesitara un flujo por lotes.
- `paths.output_dir`: carpeta donde se guardan los Markdown generados.
- `conversion.default_extension`: extensión usada para los archivos convertidos.
- `conversion.default_engine`: motor usado por defecto.
- `conversion.allowed_engines`: motores disponibles para el selector web.
- `conversion.overwrite`: si es `false`, no pisa archivos existentes.
- `conversion.max_upload_mb`: tamaño máximo permitido por archivo.
- `conversion.allowed_extensions`: extensiones aceptadas por la API; la lista completa está en `config.toml`.
- `mineru.backend`: backend usado por la CLI de MinerU.
- `mineru.timeout_seconds`: tiempo máximo de espera para MinerU.

## API

La interfaz usa el endpoint:

```text
POST /api/convert
```

Debe enviarse un formulario `multipart/form-data` con el campo `file` y opcionalmente `engine` (`markitdown` o `mineru`).

Respuesta exitosa:

```json
{
  "filename": "documento.md",
  "engine": "markitdown",
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
- Motor de conversión no permitido.
- Error interno de conversión del motor elegido.

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
|-- requirements-mineru.txt
|-- static/
|-- templates/
|-- tests/
|-- uv.lock
`-- .gitignore
```

## Arquitectura

- `app.py`: punto de entrada para `python app.py` y `uvicorn app:app`.
- `mi_markitdown/config.py`: carga `config.toml` y expone rutas, límites y extensiones.
- `mi_markitdown/converter.py`: valida uploads, coordina el motor elegido, guarda el `.md` y arma la respuesta.
- `mi_markitdown/engines/`: contiene las funciones separadas para `MarkItDown` y `MinerU`.
- `mi_markitdown/web.py`: crea la aplicación FastAPI y registra rutas.
- `static/`: JavaScript y estilos de la interfaz.
- `templates/`: HTML principal.
- `tests/`: tests de casos felices y casos borde.

## Tests

```bash
uv run pytest
```

El `pyproject.toml` configura `pytest` para ejecutar la suite con salida resumida.

## Notas de desarrollo

- Usar `pyproject.toml` como fuente principal de dependencias.
- Instalar el entorno local con `uv sync --extra dev`.
- Instalar MinerU solo cuando haga falta con `uv sync --extra dev --extra mineru`.
- Evitar commitear archivos generados, documentos cargados, entornos virtuales o datos sensibles.
- Documentar nuevos comandos de uso en este README.
- El soporte para `markitdown-ocr` queda como mejora futura: requiere habilitar plugins y configurar cliente/modelo LLM.

## ¿Por qué Markdown para IA?

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
