"""Consultas de historicos por consola.

Uso:
    python -m backend.cli dispositivos
    python -m backend.cli resumen
    python -m backend.cli historico --horas 6 --limite 20
    python -m backend.cli eventos --limite 15 --severidad critical
    python -m backend.cli comandos --limite 15
    python -m backend.cli estadisticas
    python -m backend.cli cambios
    python -m backend.cli agregado --horas 24
    python -m backend.cli purgar --dias 30
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from . import config as config_mod
from .storage import Almacen


def _tabla(filas: list[dict], columnas: list[str]) -> str:
    """Tabla de texto simple, sin dependencias."""
    if not filas:
        return "(sin resultados)"
    datos = [[_texto(fila.get(columna)) for columna in columnas] for fila in filas]
    anchos = []
    for indice, columna in enumerate(columnas):
        largo = max([len(columna)] + [len(fila[indice]) for fila in datos])
        anchos.append(min(largo, 34))

    linea = "  ".join(c.upper().ljust(anchos[i]) for i, c in enumerate(columnas))
    separador = "  ".join("-" * anchos[i] for i in range(len(columnas)))
    cuerpo = ["  ".join(fila[i][:anchos[i]].ljust(anchos[i])
                        for i in range(len(columnas))) for fila in datos]
    return "\n".join([linea, separador] + cuerpo)


def _texto(valor) -> str:
    if valor is None:
        return "-"
    if isinstance(valor, float):
        return "%.2f" % valor
    return str(valor)


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="backend.cli",
        description="Consultas de historicos del sistema Centinela IoT")
    parser.add_argument("--bd", default=None, help="ruta de la base SQLite")
    parser.add_argument("--json", action="store_true", help="salida en JSON")

    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("dispositivos", help="dispositivos registrados")

    p_resumen = sub.add_parser("resumen", help="ultima lectura y estado")
    p_resumen.add_argument("--device", default=None)

    p_hist = sub.add_parser("historico", help="lecturas de las ultimas horas")
    p_hist.add_argument("--horas", type=float, default=6.0)
    p_hist.add_argument("--limite", type=int, default=20)
    p_hist.add_argument("--device", default=None)

    p_ev = sub.add_parser("eventos", help="eventos registrados")
    p_ev.add_argument("--limite", type=int, default=15)
    p_ev.add_argument("--severidad", default=None,
                      choices=["info", "warning", "critical"])
    p_ev.add_argument("--device", default=None)

    p_cmd = sub.add_parser("comandos", help="comandos y su resultado")
    p_cmd.add_argument("--limite", type=int, default=15)

    p_est = sub.add_parser("estadisticas", help="agregados generales")
    p_est.add_argument("--device", default=None)

    p_cam = sub.add_parser("cambios", help="transiciones de estado")
    p_cam.add_argument("--limite", type=int, default=15)
    p_cam.add_argument("--device", default=None)

    p_agr = sub.add_parser("agregado", help="promedios por hora")
    p_agr.add_argument("--horas", type=float, default=24.0)
    p_agr.add_argument("--device", default=None)

    p_pur = sub.add_parser("purgar", help="borra datos antiguos")
    p_pur.add_argument("--dias", type=int, default=30)

    return parser


async def ejecutar(args) -> int:
    cfg = config_mod.cargar()
    ruta = args.bd or cfg.ruta_bd
    device = getattr(args, "device", None) or cfg.device_id

    almacen = Almacen(ruta)
    if not ruta.exists():
        print("No existe la base %s. Arranca el backend o usa --seed." % ruta,
              file=sys.stderr)
        return 2

    await almacen.abrir()
    try:
        if args.comando == "dispositivos":
            datos = await almacen.dispositivos()
            if args.json:
                print(json.dumps(datos, indent=2, ensure_ascii=False))
            else:
                print(_tabla(datos, ["device_id", "nombre", "ubicacion",
                                     "visto_utc", "firmware"]))
            return 0

        if args.comando == "resumen":
            lectura = await almacen.ultima_lectura(device)
            if args.json:
                print(json.dumps(lectura, indent=2, ensure_ascii=False))
            elif lectura:
                print("Dispositivo : %s" % device)
                print("Momento     : %s" % lectura.get("ts_utc"))
                print("Estado      : %s" % lectura.get("state"))
                print("Temperatura : %s C" % _texto(lectura.get("temp_c")))
                print("Humedad     : %s %%" % _texto(lectura.get("hum_pct")))
                print("Luz         : %s lx" % _texto(lectura.get("lux")))
                print("Distancia   : %s cm" % _texto(lectura.get("dist_cm")))
                print("Movimiento  : %s" % ("si" if lectura.get("motion") else "no"))
                print("Alarma      : %s" % ("si" if lectura.get("alarm") else "no"))
                print("Alertas     : %s" % lectura.get("alerts"))
            else:
                print("Sin lecturas para %s" % device)
            return 0

        if args.comando == "historico":
            filas = await almacen.historico(device, args.horas, args.limite)
            if args.json:
                print(json.dumps(filas, indent=2, ensure_ascii=False))
            else:
                print(_tabla(filas, ["ts_utc", "temp_c", "hum_pct", "lux",
                                     "dist_cm", "motion", "state"]))
            return 0

        if args.comando == "eventos":
            filas = await almacen.eventos(device, args.limite, args.severidad)
            if args.json:
                print(json.dumps(filas, indent=2, ensure_ascii=False))
            else:
                print(_tabla(filas, ["ts_utc", "severity", "kind", "message", "state"]))
            return 0

        if args.comando == "comandos":
            filas = await almacen.comandos(args.limite)
            if args.json:
                print(json.dumps(filas, indent=2, ensure_ascii=False))
            else:
                print(_tabla(filas, ["emitido_utc", "cmd", "source", "estado",
                                     "latencia_ms", "motivo"]))
            return 0

        if args.comando == "estadisticas":
            datos = await almacen.estadisticas(device)
            if args.json:
                print(json.dumps(datos, indent=2, ensure_ascii=False, default=str))
            else:
                for clave in sorted(datos):
                    print("%-24s %s" % (clave, _texto(datos[clave])))
            return 0

        if args.comando == "cambios":
            filas = await almacen.cambios_estado(device, args.limite)
            if args.json:
                print(json.dumps(filas, indent=2, ensure_ascii=False))
            else:
                print(_tabla(filas, ["ts_utc", "desde", "hacia", "motivo"]))
            return 0

        if args.comando == "agregado":
            filas = await almacen.agregado_horario(device, args.horas)
            if args.json:
                print(json.dumps(filas, indent=2, ensure_ascii=False))
            else:
                print(_tabla(filas, ["desde_utc", "muestras", "temp_media",
                                     "temp_min", "temp_max", "hum_media", "alarmas"]))
            return 0

        if args.comando == "purgar":
            resultado = await almacen.purgar(args.dias)
            print("Registros borrados: %s" % resultado)
            return 0

        print("Comando desconocido: %s" % args.comando, file=sys.stderr)
        return 2
    finally:
        await almacen.cerrar()


def main(argv=None) -> int:
    args = construir_parser().parse_args(argv)
    return asyncio.run(ejecutar(args))


if __name__ == "__main__":
    sys.exit(main())
