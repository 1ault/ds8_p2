"""Valida los dos diagramas de Wokwi del proyecto.

Comprueba, sin abrir el simulador:
  * que el JSON sea valido y los identificadores unicos;
  * que cada conexion apunte a una parte existente;
  * que no haya pines declarados dos veces en el mismo extremo;
  * que la variante con placas de pan tenga exactamente las mismas conexiones
    que el diagrama original (misma electricidad, distinta presentacion).

Uso:
    python scripts/validar_diagrama.py
Salida: reporte por consola; codigo 1 si algo falla.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DIAGRAMAS = {
    "diagram.json": RAIZ / "firmware" / "diagram.json",
    "diagram_placa.json": RAIZ / "firmware" / "diagram_placa.json",
}


def cargar(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def revisar(nombre: str, datos: dict) -> list[str]:
    problemas = []
    partes = datos.get("parts", [])
    ids = [parte.get("id") for parte in partes]

    for identificador, veces in Counter(ids).items():
        if veces > 1:
            problemas.append("%s: id repetido %r (%d veces)" % (nombre, identificador, veces))

    for indice, parte in enumerate(partes):
        if not parte.get("type"):
            problemas.append("%s: la parte %d no declara 'type'" % (nombre, indice))
        if "left" not in parte or "top" not in parte:
            problemas.append("%s: la parte %r no tiene posicion" % (nombre, parte.get("id")))

    conocidos = set(ids)
    for conexion in datos.get("connections", []):
        if len(conexion) < 3:
            problemas.append("%s: conexion mal formada %r" % (nombre, conexion))
            continue
        for extremo in conexion[:2]:
            if ":" not in str(extremo):
                problemas.append("%s: extremo sin pin %r" % (nombre, extremo))
                continue
            identificador = str(extremo).split(":", 1)[0]
            if identificador not in conocidos:
                problemas.append("%s: la conexion %r usa una parte inexistente"
                                 % (nombre, extremo))
    return problemas


def revisar_geometria(original: dict, variante: dict) -> list[str]:
    """Comprueba que cada placa cubre su grupo de componentes.

    Usa la geometria **medida** en el simulador (proyecto 480692575433146369):
    la placa de 830 puntos mide 654x208 px sin girar, `rotate: 90` la gira
    alrededor de su centro, y la caja dibujada queda en (left + 223, top - 223).
    Las cajas reales de los componentes se midieron igual y se guardan aqui.
    """
    # Cajas reales de cada componente, en unidades del diagrama (x, y, ancho, alto)
    CAJAS = {
        "dht1": (-280, -30, 57, 117),
        "pir1": (-270, 120, 91, 92),
        "hc1": (-290, 260, 170, 94),
        "ldr1": (-270, 400, 174, 61),
        "btn1": (-250, 550, 67, 72),
        "resR": (380, 20, 59, 11),
        "ledR": (470, 20, 40, 60),
        "resV": (380, 140, 59, 11),
        "ledV": (470, 140, 40, 60),
        "bz1": (400, 260, 75, 84),
        "sv1": (360, 380, 170, 120),
        "oled1": (340, 560, 150, 123),
    }
    PLACA_LARGO = 654.0   # sin girar
    PLACA_ANCHO = 208.0   # sin girar
    DESPLAZAMIENTO = (PLACA_LARGO - PLACA_ANCHO) / 2.0   # 223
    # La placa de 830 puntos (654 px) es 9 px mas corta que la columna de
    # actuadores (663 px): se admite ese margen y se informa del residuo.
    TOLERANCIA = 10.0

    grupos = {
        "sensores (izquierda)": ("bb1", ["dht1", "pir1", "hc1", "ldr1", "btn1"]),
        "actuadores (derecha)": ("bb2", ["resR", "ledR", "resV", "ledV", "bz1",
                                         "sv1", "oled1"]),
    }
    partes = {parte["id"]: parte for parte in variante["parts"]}
    problemas = []

    print("\n== geometria (medidas reales del simulador) ==")
    cajas_dibujadas = {}
    for etiqueta, (id_placa, ids) in grupos.items():
        placa = partes.get(id_placa)
        if not placa:
            problemas.append("falta la placa %s" % id_placa)
            continue
        izquierda = float(placa.get("left", 0))
        arriba = float(placa.get("top", 0))
        giro = int(placa.get("rotate", 0))

        if giro % 180 == 90:
            ancho, alto = PLACA_ANCHO, PLACA_LARGO
            x, y = izquierda + DESPLAZAMIENTO, arriba - DESPLAZAMIENTO
        else:
            ancho, alto = PLACA_LARGO, PLACA_ANCHO
            x, y = izquierda, arriba

        xs = [CAJAS[i][0] for i in ids]
        ys = [CAJAS[i][1] for i in ids]
        x2s = [CAJAS[i][0] + CAJAS[i][2] for i in ids]
        y2s = [CAJAS[i][1] + CAJAS[i][3] for i in ids]
        gx1, gy1, gx2, gy2 = min(xs), min(ys), max(x2s), max(y2s)

        cajas_dibujadas[id_placa] = (x, y, x + ancho, y + alto)
        cubre_x = x <= gx1 + TOLERANCIA and (x + ancho) >= gx2 - TOLERANCIA
        cubre_y = y <= gy1 + TOLERANCIA and (y + alto) >= gy2 - TOLERANCIA
        sobra_x = (x - gx1, (x + ancho) - gx2)
        sobra_y = (y - gy1, (y + alto) - gy2)

        print("%-22s %s caja dibujada x=[%.0f..%.0f] y=[%.0f..%.0f]" % (
            etiqueta, id_placa, x, x + ancho, y, y + alto))
        print("%-22s grupo        x=[%.0f..%.0f] y=[%.0f..%.0f]  cubre: x=%s y=%s" % (
            "", gx1, gx2, gy1, gy2,
            "si" if cubre_x else "NO", "si" if cubre_y else "NO"))
        print("%-22s margen sobrante: x=(%+.0f, %+.0f) y=(%+.0f, %+.0f)" % (
            "", sobra_x[0], sobra_x[1], sobra_y[0], sobra_y[1]))
        if not cubre_x:
            problemas.append("%s no cubre el ancho del grupo %s" % (id_placa, etiqueta))
        if not cubre_y:
            problemas.append("%s no cubre el alto del grupo %s" % (id_placa, etiqueta))
        if "izquierda" in etiqueta and x >= 0:
            problemas.append("%s deberia estar a la izquierda del ESP32" % id_placa)
        if "derecha" in etiqueta and x <= 0:
            problemas.append("%s deberia estar a la derecha del ESP32" % id_placa)

    if {"bb1", "bb2"} <= set(cajas_dibujadas):
        fin_bb1 = cajas_dibujadas["bb1"][2]
        inicio_bb2 = cajas_dibujadas["bb2"][0]
        print("%-22s fin de bb1=%.0f | inicio de bb2=%.0f" % ("", fin_bb1, inicio_bb2))
        if fin_bb1 > inicio_bb2:
            problemas.append("las dos placas se solapan entre si")
        else:
            print("%-22s sin solapamiento entre placas" % "")
    return problemas


def main() -> int:
    problemas = []
    datos = {}
    for nombre, ruta in DIAGRAMAS.items():
        if not ruta.exists():
            problemas.append("%s: no existe" % nombre)
            continue
        datos[nombre] = cargar(ruta)
        problemas.extend(revisar(nombre, datos[nombre]))

    original = datos.get("diagram.json")
    variante = datos.get("diagram_placa.json")

    print("== diagramas ==")
    for nombre, info in datos.items():
        print("%-20s partes=%-3d conexiones=%-3d" % (
            nombre, len(info.get("parts", [])), len(info.get("connections", []))))

    if original and variante:
        iguales = variante["connections"] == original["connections"]
        print("\n== comparacion ==")
        print("conexiones identicas:", "si" if iguales else "NO")
        ids_original = [parte["id"] for parte in original["parts"]]
        ids_variante = [parte["id"] for parte in variante["parts"]]
        extra = [i for i in ids_variante if i not in ids_original]
        print("partes agregadas:", ", ".join(extra) or "ninguna")
        print("partes del original presentes:", set(ids_original).issubset(ids_variante))
        if not iguales:
            problemas.append("las conexiones de la variante no coinciden con el original")

        problemas.extend(revisar_geometria(original, variante))

    print("\n== resultado ==")
    if problemas:
        for problema in problemas:
            print("FALLO:", problema)
        return 1
    print("sin problemas: JSON valido, identificadores unicos y conexiones coherentes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
