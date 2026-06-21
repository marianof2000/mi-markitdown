const form = document.querySelector("#upload-form");
const input = document.querySelector("#file-input");
const dropZone = document.querySelector("#drop-zone");
const fileLabel = document.querySelector("#file-label");
const statusText = document.querySelector("#status");
const preview = document.querySelector("#preview");
const convertButton = document.querySelector("#convert-button");
const downloadLink = document.querySelector("#download-link");
const copyButton = document.querySelector("#copy-button");

let markdownBlobUrl = "";
let currentMarkdown = "";

function setStatus(message, state = "idle") {
  statusText.textContent = message;
  statusText.dataset.state = state;
}

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

function setSelectedFile(file) {
  fileLabel.textContent = file
    ? `${file.name} - ${(file.size / 1024 / 1024).toFixed(2)} MB`
    : "PDF, Word, Excel, PowerPoint, HTML, CSV, JSON, XML, TXT, ZIP o EPUB";
}

input.addEventListener("change", () => {
  setSelectedFile(input.files[0]);
});

for (const eventName of ["dragenter", "dragover"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("dragging");
  });
}

for (const eventName of ["dragleave", "drop"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragging");
  });
}

dropZone.addEventListener("drop", (event) => {
  const file = event.dataTransfer.files[0];
  if (!file) return;

  const dataTransfer = new DataTransfer();
  dataTransfer.items.add(file);
  input.files = dataTransfer.files;
  setSelectedFile(file);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const file = input.files[0];
  if (!file) {
    setStatus("Seleccioná un archivo primero.", "error");
    return;
  }

  const body = new FormData();
  body.append("file", file);

  convertButton.disabled = true;
  downloadLink.classList.add("disabled");
  setStatus("Convirtiendo archivo...", "busy");
  preview.textContent = "";

  try {
    const response = await fetch("/api/convert", {
      method: "POST",
      body,
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "No se pudo convertir el archivo.");
    }

    currentMarkdown = payload.markdown || "";
    preview.textContent = currentMarkdown || "La conversión no devolvió contenido.";
    setDownload(currentMarkdown, payload.filename || "documento.md");
    setStatus(
      `Conversión lista - guardado en ${payload.output_path} - ${(payload.size / 1024).toFixed(1)} KB Markdown`,
      "success",
    );
  } catch (error) {
    currentMarkdown = "";
    preview.textContent = "No hay contenido para mostrar.";
    setStatus(error.message, "error");
  } finally {
    convertButton.disabled = false;
  }
});

copyButton.addEventListener("click", async () => {
  if (!currentMarkdown) {
    setStatus("Todavía no hay Markdown para copiar.", "error");
    return;
  }

  await navigator.clipboard.writeText(currentMarkdown);
  setStatus("Markdown copiado al portapapeles.", "success");
});
