# AGENTS.md

## Proyecto

Mi-Markitdown es una aplicación web Python orientada a conversión de documentos a Markdown con `markitdown`.

## Instrucciones para agentes

- Usar Python 3.12 como versión objetivo.
- Preferir cambios pequeños y fáciles de revisar.
- Mantener la configuración del proyecto en `config.toml`.
- Declarar dependencias runtime en `requirements.txt`.
- Mantener la interfaz web simple, accesible y usable en escritorio y móvil.
- No commitear archivos generados, credenciales, entornos virtuales ni salidas temporales.
- Actualizar `README.md` cuando se agreguen comandos, flujos de uso o requisitos nuevos.

## Verificación sugerida

Antes de cerrar cambios, revisar:

```bash
python --version
pip install -r requirements.txt
pytest -q
uvicorn app:app --reload
```
