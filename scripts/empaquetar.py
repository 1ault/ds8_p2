"""Empaquetado de entregables.

Genera:
  entregables/Wokwi_Centinela_IoT.zip     proyecto listo para importar en wokwi.com
  entregables/Parcial2_IoT_Seguridad.zip  repositorio completo (codigo, SQL,
                                          pruebas, documentacion e imagenes)
  entregables/MANIFIESTO.txt              tamano y SHA-256 de cada archivo

Uso:
    python scripts/empaquetar.py
    python scripts/empaquetar.py --sin-repo      # solo el ZIP de Wokwi
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ENTREGABLES = RAIZ / "entregables"

# Archivos del firmware que debe contener el proyecto de Wokwi
FIRMWARE = (
    "main.py", "config.py", "hal.py", "bus.py", "fsm.py", "sensors.py",
    "actuators.py", "display.py", "ssd1306.py", "mqtt_client.py", "net.py",
    "app.py",
)

# Carpetas del repositorio que entran en el paquete completo
INCLUIR = ("backend", "firmware", "sql", "scripts", "tests", "docs")
ARCHIVOS_SUELTOS = (
    "README.md", "requirements.txt", "requirements-dev.txt", "pyproject.toml",
    ".env.example", ".gitignore",
)

EXCLUIR_NOMBRES = {
    "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".tmp",
    ".venv", "venv", "env", ".git", ".scratch", ".idea", ".vscode",
}
EXCLUIR_SUFIJOS = (".pyc", ".pyo", ".db-wal", ".db-shm", ".log")


def log(mensaje):
    print("[empaquetar] %s" % mensaje, flush=True)


def sha256(ruta: Path) -> str:
    digest = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(65536), b""):
            digest.update(bloque)
    return digest.hexdigest()


def _ignorar(ruta: Path) -> bool:
    if ruta.name in EXCLUIR_NOMBRES:
        return True
    if ruta.name.startswith("~$"):
        return True
    return ruta.name.endswith(EXCLUIR_SUFIJOS)


def construir_wokwi(destino: Path) -> Path:
    """ZIP con los archivos que Wokwi necesita, todos en la raiz."""
    firmware = RAIZ / "firmware"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as paquete:
        for nombre in FIRMWARE:
            archivo = firmware / nombre
            if not archivo.exists():
                raise FileNotFoundError("falta %s" % archivo)
            paquete.write(archivo, arcname=nombre)
        paquete.write(firmware / "diagram.json", arcname="diagram.json")
        # Variante con placas de pan: misma electricidad, otra presentacion.
        placa = firmware / "diagram_placa.json"
        if placa.exists():
            paquete.write(placa, arcname="diagram_placa.json")
        leeme = firmware / "README_WOKWI.md"
        if leeme.exists():
            paquete.write(leeme, arcname="README_WOKWI.md")
        paquete.writestr(
            "LEEME.txt",
            "Centinela IoT - proyecto Wokwi (ESP32 + MicroPython)\r\n"
            "\r\n"
            "1. Entrar a https://wokwi.com y crear un proyecto ESP32 / MicroPython.\r\n"
            "2. Copiar main.py, config.py, el resto de modulos y diagram.json.\r\n"
            "3. Pulsar Play: el nodo se conecta a Wokwi-GUEST y publica en\r\n"
            "   broker.hivemq.com bajo los topicos centinela/dev01/#.\r\n"
            "\r\n"
            "Dos diagramas, misma electricidad:\r\n"
            "  diagram.json        componentes sueltos (version de referencia)\r\n"
            "  diagram_placa.json  los mismos componentes sobre placas de pan\r\n"
            "\r\n"
            "Detalle en README_WOKWI.md\r\n",
        )
    log("ZIP de Wokwi: %s (%.1f KB)" % (destino.name, destino.stat().st_size / 1024))
    return destino


def construir_repositorio(destino: Path) -> Path:
    """ZIP con el repositorio completo (sin entorno virtual ni base de datos)."""
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as paquete:
        for nombre in ARCHIVOS_SUELTOS:
            archivo = RAIZ / nombre
            if archivo.exists():
                paquete.write(archivo, arcname=nombre)

        for carpeta in INCLUIR:
            base = RAIZ / carpeta
            if not base.exists():
                continue
            for archivo in sorted(base.rglob("*")):
                if archivo.is_dir() or _ignorar(archivo):
                    continue
                relativa = archivo.relative_to(RAIZ)
                paquete.write(archivo, arcname=str(relativa).replace("\\", "/"))
    log("ZIP del repositorio: %s (%.1f KB)" % (
        destino.name, destino.stat().st_size / 1024))
    return destino


DOCUMENTOS = (
    ("Informe_Tecnico_Centinela_IoT", "Informe técnico del proyecto"),
    ("Manual_Tecnico_Centinela_IoT", "Manual técnico del sistema"),
    ("Manual_Usuario_Centinela_IoT", "Manual del usuario"),
    ("Documentacion_Extendida_Centinela_IoT", "Catálogo de módulos y código comentado"),
    ("Guia_Prueba_Monitoreo", "Guía práctica de prueba del monitoreo"),
    ("Guia_Instalacion_Montaje", "Guía de instalación y montaje"),
)

# Carpetas que no entran en el manifiesto
IGNORAR_MANIFIESTO = {"Wokwi_Centinela_IoT"}


def copiar_documentos() -> list[Path]:
    """Copia los documentos finales (DOCX y PDF) a la carpeta de entrega."""
    origen = RAIZ / "docs" / "manuales"
    copiados = []
    for nombre, _descripcion in DOCUMENTOS:
        for extension in (".docx", ".pdf"):
            archivo = origen / (nombre + extension)
            if not archivo.exists():
                log("falta %s (se omite)" % archivo.name)
                continue
            destino = ENTREGABLES / archivo.name
            shutil.copy2(archivo, destino)
            copiados.append(destino)
            log("documento: %s (%.0f KB)" % (destino.name,
                                             destino.stat().st_size / 1024))
    return copiados


LEEME = """# Centinela IoT — paquete de entrega

**Parcial #2 · Desarrollo de Software VIII · Sistema IoT de monitoreo y control inteligente**
Escenario 4: *Sistema de Seguridad — Detección y alertas* · versión {version}

---

## 1. Qué contiene esta carpeta

| Archivo | Contenido |
|---------|-----------|
| `Informe_Tecnico_Centinela_IoT.docx` / `.pdf` | informe del desarrollo, la verificación y los resultados |
| `Manual_Tecnico_Centinela_IoT.docx` / `.pdf` | arquitectura, protocolo, servicios y operación del sistema |
| `Manual_Usuario_Centinela_IoT.docx` / `.pdf` | guía de uso del panel y de las alertas |
| `Documentacion_Extendida_Centinela_IoT.docx` / `.pdf` | módulos con firmas y variables, código y SQL comentados, y análisis de cumplimiento |
| `Guia_Prueba_Monitoreo.docx` / `.pdf` | pasos para probar la interfaz, ubicar las lecturas y consultar el histórico |
| `Guia_Instalacion_Montaje.docx` / `.pdf` | instalación desde cero, nodo en Wokwi, montaje físico y nube |
| `Parcial2_IoT_Seguridad.zip` | repositorio completo: código, SQL, 324 pruebas, documentación, diagramas y capturas |
| `Wokwi_Centinela_IoT.zip` | proyecto listo para importar en <https://wokwi.com> |
| `MANIFIESTO.txt` | tamaño y SHA-256 de cada archivo entregado |

También están disponibles en el repositorio: `README.md`, la documentación técnica en
`docs/` y las capturas de ejecución en `docs/capturas/`.

---

## 2. Cómo probar el sistema en tres pasos

```bat
cd Parcial2_IoT_Seguridad
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt

python -m backend.main --seed          :: panel en http://127.0.0.1:8000
```

Credenciales iniciales: **admin / seguridad2026**. PIN de la cerradura: **2468**.

Para una demostración completa sin depender de Internet:

```bat
python scripts\\demo.py --reset --sembrar --sin-login
```

Para el simulador: importar `Wokwi_Centinela_IoT.zip` en Wokwi y pulsar **Play**.

---

## 3. Verificación

| Evidencia | Resultado |
|-----------|-----------|
| Pruebas automatizadas | **324 aprobadas**, 0 fallidas (`python -m pytest`) |
| Integración real | broker HiveMQ: telemetría `ARMING → ARMED → ALARM` con sirena activa |
| Capturas del panel | `docs/capturas/01..07` |
| Capturas del simulador | `docs/capturas/wokwi_01..05` |
| Diagramas | `docs/img/` (arquitectura, flujo de datos, circuito, FSM, modelo de datos) |

---

## 4. Antes de subir a Teams o GitHub

1. Ejecutar `python -m pytest` y confirmar las 324 pruebas.
2. Comprobar que `.env` y `data/*.db` **no** se incluyen (ya están en `.gitignore`).
3. Cambiar `WEB_PASSWORD`, `SECRET_KEY` y `UNLOCK_PIN` si el sistema se va a usar fuera del aula.
4. Tomar las capturas propias de ThingSpeak y del repositorio en GitHub
   (guion en `docs/guia_demo.md`).
5. Subir también el informe y los manuales en Word, junto con este paquete.

---

## 5. Nota sobre los documentos

Los tres documentos están en Word (editables) y en PDF (para entregar). Mantienen el mismo
estilo: portada, índice, encabezado con la asignatura, numeración de páginas, figuras y tablas
numeradas. Se regeneran con:

```bat
python scripts\\build_informe_tecnico.py
python scripts\\build_manual_tecnico.py
python scripts\\build_manual_usuario.py
```
"""


def escribir_leeme(version: str = "2.0.0") -> Path:
    destino = ENTREGABLES / "LEEME_ENTREGA.md"
    destino.write_text(LEEME.format(version=version), encoding="utf-8")
    log("guia de entrega: %s" % destino.name)
    return destino


def escribir_manifiesto(archivos: list[Path]) -> Path:
    """Manifiesto con tamano y SHA-256 de todo lo entregado."""
    destino = ENTREGABLES / "MANIFIESTO.txt"

    listado = {}
    for archivo in archivos:
        if archivo.exists():
            listado[archivo.name] = archivo
    for archivo in sorted(ENTREGABLES.rglob("*")):
        if archivo.is_dir() or archivo.name == destino.name:
            continue
        if archivo.parent.name in IGNORAR_MANIFIESTO:
            continue
        listado.setdefault(archivo.name, archivo)

    lineas = [
        "Centinela IoT - Parcial #2 - Desarrollo de Software VIII",
        "Manifiesto generado: %s" % datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "=" * 72,
        "",
    ]
    total = 0.0
    for nombre in sorted(listado):
        archivo = listado[nombre]
        tamano = archivo.stat().st_size / 1024
        total += tamano
        lineas.append("%-46s %9.1f KB" % (archivo.name, tamano))
        lineas.append("    sha256 %s" % sha256(archivo))
        lineas.append("")
    lineas.append("-" * 72)
    lineas.append("TOTAL: %d archivos, %.1f KB" % (len(listado), total))
    destino.write_text("\n".join(lineas), encoding="utf-8")
    log("manifiesto: %s (%d archivos, %.1f KB)" % (destino.name, len(listado), total))
    return destino


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Genera los paquetes de entrega")
    parser.add_argument("--sin-repo", action="store_true",
                        help="no generar el ZIP del repositorio completo")
    parser.add_argument("--sin-documentos", action="store_true",
                        help="no copiar los documentos finales")
    args = parser.parse_args(argv)

    ENTREGABLES.mkdir(parents=True, exist_ok=True)
    generados = [construir_wokwi(ENTREGABLES / "Wokwi_Centinela_IoT.zip")]
    if not args.sin_repo:
        generados.append(construir_repositorio(ENTREGABLES / "Parcial2_IoT_Seguridad.zip"))
    if not args.sin_documentos:
        generados.extend(copiar_documentos())
    generados.append(escribir_leeme())
    escribir_manifiesto(generados)
    return 0


if __name__ == "__main__":
    sys.exit(main())
