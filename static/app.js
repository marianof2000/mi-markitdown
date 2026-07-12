const form = document.querySelector("#upload-form");
const input = document.querySelector("#file-input");
const dropZone = document.querySelector("#drop-zone");
const fileLabel = document.querySelector("#file-label");
const statusText = document.querySelector("#status");
const preview = document.querySelector("#preview");
const convertButton = document.querySelector("#convert-button");
const downloadLink = document.querySelector("#download-link");
const copyButton = document.querySelector("#copy-button");
const engineInputs = document.querySelectorAll('input[name="engine"]');
const messages = window.MI_MARKITDOWN_I18N || {};

let markdownBlobUrl = "";
let currentMarkdown = "";
let progressTimer = 0;

/**
 * Contrato: evitar navegación antes de que exista un Markdown descargable.
 * Precondiciones: `event` es un click sobre el enlace de descarga.
 * Postcondiciones: si el enlace está deshabilitado, cancela la navegación.
 */
function handleDownloadClick(event) {
  if (downloadLink.classList.contains("disabled")) {
    event.preventDefault();
  }
}

/**
 * Contrato: obtener un texto localizado y reemplazar variables simples.
 * Precondiciones: `key` identifica un mensaje y `fallback` contiene el texto de respaldo.
 * Postcondiciones: devuelve el texto traducido o el fallback con variables reemplazadas.
 */
function t(key, fallback, values = {}) {
  const template = messages[key] || fallback;
  return Object.entries(values).reduce((text, [name, value]) => {
    return text.replaceAll(`{${name}}`, value);
  }, template);
}

/**
 * Contrato: actualizar el mensaje de estado visible para el usuario.
 * Precondiciones: `statusText` apunta al elemento de estado y `message` es texto mostrable.
 * Postcondiciones: el texto y el estado visual quedan sincronizados en la UI.
 */
function setStatus(message, state = "idle") {
  statusText.textContent = message;
  statusText.dataset.state = state;
}

/**
 * Contrato: mostrar pasos de espera mientras la API procesa la conversión.
 * Precondiciones: hay una conversión en curso.
 * Postcondiciones: actualiza el estado con mensajes no porcentuales hasta que se detenga.
 */
function startConversionProgress(engine) {
  const steps = [
    t("uploading_file", "Subiendo archivo..."),
    t("processing_with", `Procesando con ${engineLabel(engine)}...`, { engine: engineLabel(engine) }),
    t("preparing_markdown", "Preparando Markdown..."),
  ];
  let stepIndex = 0;

  window.clearInterval(progressTimer);
  setStatus(steps[stepIndex], "busy");
  progressTimer = window.setInterval(() => {
    stepIndex = Math.min(stepIndex + 1, steps.length - 1);
    setStatus(steps[stepIndex], "busy");
  }, 1200);
}

/**
 * Contrato: detener los mensajes de progreso de conversión.
 * Precondiciones: puede haber un temporizador activo.
 * Postcondiciones: no quedan actualizaciones periódicas pendientes.
 */
function stopConversionProgress() {
  window.clearInterval(progressTimer);
  progressTimer = 0;
}

/**
 * Contrato: preparar la descarga del Markdown convertido.
 * Precondiciones: `markdown` contiene el texto generado y `filename` es el nombre de salida.
 * Postcondiciones: el enlace de descarga apunta a un Blob vigente y queda habilitado.
 */
function setDownload(markdown, filename) {
  if (markdownBlobUrl) {
    URL.revokeObjectURL(markdownBlobUrl);
  }

  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  markdownBlobUrl = URL.createObjectURL(blob);
  downloadLink.href = markdownBlobUrl;
  downloadLink.download = filename;
  downloadLink.classList.remove("disabled");
}

/**
 * Contrato: obtener el motor seleccionado en el formulario.
 * Precondiciones: `engineInputs` contiene los radios de motores disponibles.
 * Postcondiciones: devuelve el valor marcado o `markitdown` como valor por defecto.
 */
function selectedEngine() {
  for (const engineInput of engineInputs) {
    if (engineInput.checked) {
      return engineInput.value;
    }
  }

  return "markitdown";
}

/**
 * Contrato: convertir un identificador de motor en una etiqueta legible.
 * Precondiciones: `engine` es el valor recibido desde la API o el formulario.
 * Postcondiciones: devuelve el nombre mostrado al usuario.
 */
function engineLabel(engine) {
  return engine === "mineru" ? "MinerU" : "MarkItDown";
}

/**
 * Contrato: convertir una duración en un texto breve para la UI.
 * Precondiciones: `milliseconds` es una duración no negativa medida en milisegundos.
 * Postcondiciones: devuelve una etiqueta en milisegundos o segundos.
 */
function formatElapsedTime(milliseconds) {
  if (milliseconds < 1000) {
    return `${Math.round(milliseconds)} ms`;
  }

  const seconds = milliseconds / 1000;
  return `${seconds.toLocaleString(messages.locale || "es-AR", {
    maximumFractionDigits: 1,
    minimumFractionDigits: 1,
  })} s`;
}

/**
 * Contrato: reflejar en la UI el archivo seleccionado.
 * Precondiciones: `file` es un `File` del navegador o un valor vacío.
 * Postcondiciones: la etiqueta muestra nombre y tamaño, o el texto de formatos aceptados.
 */
function setSelectedFile(file) {
  fileLabel.textContent = file
    ? `${file.name} - ${(file.size / 1024 / 1024).toFixed(2)} MB`
    : t("file_label", "PDF, Word, Excel, PowerPoint, HTML, CSV, JSON, XML, TXT, ZIP o EPUB");
}

/**
 * Contrato: manejar la selección manual de archivo.
 * Precondiciones: el input de archivo puede exponer `files`.
 * Postcondiciones: la etiqueta de archivo queda actualizada.
 */
function handleFileInputChange() {
  setSelectedFile(input.files[0]);
}

/**
 * Contrato: activar el estado visual de arrastre sobre la zona de carga.
 * Precondiciones: `event` es un evento de drag del navegador.
 * Postcondiciones: se previene la acción por defecto y se marca la zona como activa.
 */
function markDropZoneDragging(event) {
  event.preventDefault();
  dropZone.classList.add("dragging");
}

/**
 * Contrato: desactivar el estado visual de arrastre sobre la zona de carga.
 * Precondiciones: `event` es un evento de drag o drop del navegador.
 * Postcondiciones: se previene la acción por defecto y se limpia el estado activo.
 */
function clearDropZoneDragging(event) {
  event.preventDefault();
  dropZone.classList.remove("dragging");
}

/**
 * Contrato: aceptar un archivo soltado sobre la zona de carga.
 * Precondiciones: `event.dataTransfer` puede contener archivos.
 * Postcondiciones: el primer archivo queda asignado al input y visible en la etiqueta.
 */
function handleDrop(event) {
  const file = event.dataTransfer.files[0];
  if (!file) return;

  const dataTransfer = new DataTransfer();
  dataTransfer.items.add(file);
  input.files = dataTransfer.files;
  setSelectedFile(file);
}

/**
 * Contrato: enviar el archivo seleccionado a la API de conversión.
 * Precondiciones: el formulario existe y puede contener un archivo seleccionado.
 * Postcondiciones: actualiza vista previa, descarga y estado, o muestra el error recibido.
 */
async function handleSubmit(event) {
  event.preventDefault();

  const file = input.files[0];
  if (!file) {
    setStatus(t("select_file_first", "Seleccioná un archivo primero."), "error");
    return;
  }

  const body = new FormData();
  const engine = selectedEngine();
  body.append("file", file);
  body.append("engine", engine);

  convertButton.disabled = true;
  downloadLink.classList.add("disabled");
  startConversionProgress(engine);
  preview.textContent = "";
  const startedAt = performance.now();

  try {
    const response = await fetch("/api/convert", {
      method: "POST",
      body,
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || t("conversion_failed", "No se pudo convertir el archivo."));
    }

    currentMarkdown = payload.markdown || "";
    setStatus(t("saving_markdown", "Guardando Markdown..."), "busy");
    preview.textContent = currentMarkdown || t("empty_conversion", "La conversión no devolvió contenido.");
    setDownload(currentMarkdown, payload.filename || "documento.md");
    const elapsedTime = formatElapsedTime(performance.now() - startedAt);
    setStatus(
      t("conversion_done", `Se convirtió con ${engineLabel(payload.engine)} en ${elapsedTime} - guardado en ${payload.output_path} - ${(payload.size / 1024).toFixed(1)} KB Markdown`, {
        engine: engineLabel(payload.engine),
        elapsed: elapsedTime,
        path: payload.output_path,
        size: (payload.size / 1024).toFixed(1),
      }),
      "success",
    );
  } catch (error) {
    currentMarkdown = "";
    preview.textContent = t("no_preview", "No hay contenido para mostrar.");
    setStatus(error.message, "error");
  } finally {
    stopConversionProgress();
    convertButton.disabled = false;
  }
}

/**
 * Contrato: copiar el Markdown convertido al portapapeles.
 * Precondiciones: el navegador expone `navigator.clipboard` y puede haber Markdown actual.
 * Postcondiciones: copia el Markdown o informa que todavía no hay contenido para copiar.
 */
async function handleCopy() {
  if (!currentMarkdown) {
    setStatus(t("no_markdown_to_copy", "Todavía no hay Markdown para copiar."), "error");
    return;
  }

  try {
    await navigator.clipboard.writeText(currentMarkdown);
    setStatus(t("copied", "Markdown copiado al portapapeles."), "success");
  } catch (_error) {
    setStatus(t("copy_failed", "No se pudo copiar el Markdown al portapapeles."), "error");
  }
}

input.addEventListener("change", handleFileInputChange);

for (const eventName of ["dragenter", "dragover"]) {
  dropZone.addEventListener(eventName, markDropZoneDragging);
}

for (const eventName of ["dragleave", "drop"]) {
  dropZone.addEventListener(eventName, clearDropZoneDragging);
}

dropZone.addEventListener("drop", handleDrop);
form.addEventListener("submit", handleSubmit);
copyButton.addEventListener("click", handleCopy);
downloadLink.addEventListener("click", handleDownloadClick);
