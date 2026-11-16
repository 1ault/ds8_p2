"""Genera `firmware/diagram_placa.json`: misma electricidad, con placas de pan.

El diagrama alternativo parte del `diagram.json` real y **no toca ninguna
conexion**: se limita a insertar dos placas de pan (protoboards) como base de
montaje detras de los modulos, de modo que el simulador muestre un montaje
fisico parecido al de un prototipo real.

Se genera por script para garantizar que las 29 conexiones y los 13 componentes
son exactamente los mismos; si alguien edita el diagrama original, basta con
volver a ejecutar este script.

Uso:
    python scripts/generar_diagrama_placa.py
Salida:
    firmware/diagram_placa.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ORIGEN = RAIZ / "firmware" / "diagram.json"
DESTINO = RAIZ / "firmware" / "diagram_placa.json"

# Placas de pan como base de montaje. Van primero en la lista para que el
# simulador las dibuje detras de los modulos.
#
# Geometria medida en el simulador (proyecto 480692575433146369, Chrome headless
# leyendo los rectangulos reales de los elementos):
#
#   * la placa de 830 puntos mide 654 x 208 px sin girar;
#   * `rotate: 90` la gira alrededor de su CENTRO, asi que la caja dibujada es
#     208 x 654 y queda en (left + 223, top - 223) en unidades del diagrama;
#   * los componentes se dibujan en (left, top) con 1 unidad = 1 px.
#
# Grupo de sensores (cajas reales): x[-290..-96]  y[-30..622]
#   caja 208x654 centrada -> esquina (-297, -31) -> left=-520, top=192
# Grupo de actuadores:              x[340..530]  y[20..683]
#   caja centrada -> esquina (331, 24) -> left=108, top=247
#   (la placa es 9 px mas corta que el grupo; se reparte el margen)
PLACAS = [
    {
        "type": "wokwi-breadboard",
        "id": "bb1",
        "top": 192,
        "left": -520,
        "rotate": 90,
        "attrs": {},
    },
    {
        "type": "wokwi-breadboard",
        "id": "bb2",
        "top": 247,
        "left": 108,
        "rotate": 90,
        "attrs": {},
    },
]


def construir() -> dict:
    original = json.loads(ORIGEN.read_text(encoding="utf-8"))

    variante = {
        "version": original.get("version", 1),
        "author": "Parcial #2 - Desarrollo de Software VIII (Centinela IoT) · "
                  "variante con placas de pan",
        "editor": original.get("editor", "wokwi"),
        "parts": list(PLACAS) + list(original["parts"]),
        # Las conexiones se copian tal cual, sin reordenar ni reescribir.
        "connections": [list(conexion) for conexion in original["connections"]],
        "dependencies": dict(original.get("dependencies", {})),
    }
    return variante


def main() -> int:
    if not ORIGEN.exists():
        print("falta", ORIGEN)
        return 1
    original = json.loads(ORIGEN.read_text(encoding="utf-8"))
    variante = construir()

    DESTINO.write_text(
        json.dumps(variante, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Verificacion: mismos componentes y mismas conexiones que el original.
    ids_original = {parte["id"] for parte in original["parts"]}
    ids_variante = {parte["id"] for parte in variante["parts"]}
    nuevas = ids_variante - ids_original
    faltan = ids_original - ids_variante
    iguales = variante["connections"] == original["connections"]

    print("generado:", DESTINO.name)
    print("partes originales:", len(original["parts"]),
          "| partes en la variante:", len(variante["parts"]))
    print("agregadas:", ", ".join(sorted(nuevas)) or "ninguna")
    print("faltantes:", ", ".join(sorted(faltan)) or "ninguna")
    print("conexiones:", len(variante["connections"]),
          "| identicas al original:", "si" if iguales else "NO")
    return 0 if iguales and not faltan else 2


if __name__ == "__main__":
    sys.exit(main())
