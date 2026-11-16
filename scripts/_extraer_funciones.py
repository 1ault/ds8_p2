"""Extrae el codigo de las funciones criticas con su numero de linea.

Se usa para redactar los listados comentados linea por linea del documento de
documentacion extendida. La salida es texto plano con formato:

    ### ruta::elemento  (lineas a-b)
    a: codigo
    b: codigo
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

SELECCION = [
    ("firmware/fsm.py", "SecurityFSM", "_presencia"),
    ("firmware/mqtt_client.py", None, "encode_connect"),
    ("firmware/app.py", "Controlador", "_ciclo"),
    ("backend/storage.py", "Almacen", "guardar_lectura"),
    ("backend/commands.py", "ServicioComandos", "ejecutar"),
    ("backend/web/app.py", None, "api_stream"),
]


def extraer(ruta: str, clase: str | None, funcion: str) -> str:
    archivo = RAIZ / ruta
    fuente = archivo.read_text(encoding="utf-8")
    lineas = fuente.splitlines()
    arbol = ast.parse(fuente)

    nodo = None
    for elemento in arbol.body:
        if clase and isinstance(elemento, ast.ClassDef) and elemento.name == clase:
            for hijo in elemento.body:
                if isinstance(hijo, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and hijo.name == funcion:
                    nodo = hijo
        elif not clase and isinstance(elemento, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and elemento.name == funcion:
            nodo = elemento

    if nodo is None:
        return "### NO ENCONTRADO %s::%s\n" % (ruta, funcion)

    inicio = nodo.lineno
    fin = getattr(nodo, "end_lineno", inicio)
    etiqueta = "%s::%s" % (ruta, ("%s.%s" % (clase, funcion)) if clase else funcion)
    salida = ["### %s  (lineas %d-%d)" % (etiqueta, inicio, fin)]
    for numero in range(inicio, fin + 1):
        salida.append("%4d: %s" % (numero, lineas[numero - 1]))
    return "\n".join(salida) + "\n"


def main() -> int:
    partes = [extraer(*seleccion) for seleccion in SELECCION]
    destino = RAIZ / ".tmp" / "funciones_criticas.txt"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(partes), encoding="utf-8")
    print("extraidas:", len(partes), "funciones ->", destino.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
