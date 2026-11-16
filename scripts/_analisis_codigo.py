"""Analisis estatico del proyecto para la documentacion extendida.

Recorre los modulos Python con `ast` y extrae, sin ejecutar el codigo:

  * constantes y variables de modulo (con su valor y las funciones que las usan)
  * clases, atributos de instancia y metodos que los usan
  * funciones: firma, parametros con anotacion y valor por defecto, retorno
  * rangos de lineas de cada elemento

El resultado alimenta las tablas de los capitulos 1 y 2 del documento; asi los
datos son los reales del repositorio y no una transcripcion manual.
"""

from __future__ import annotations

import ast
import builtins
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# Nombres que no interesa listar como "variables del modulo"
RUIDO = set(dir(builtins)) | {
    "self", "cls", "True", "False", "None", "print", "range", "len", "int",
    "float", "str", "bytes", "bool", "dict", "list", "tuple", "set", "min",
    "max", "abs", "round", "sorted", "enumerate", "isinstance", "hasattr",
    "getattr", "setattr", "super", "Exception", "RuntimeError", "ValueError",
    "TypeError", "asyncio", "json", "time", "math", "random", "os", "sys",
}


def _segmento(fuente: str, nodo: ast.AST) -> str:
    try:
        texto = ast.get_source_segment(fuente, nodo) or ""
    except Exception:  # noqa: BLE001
        return ""
    return " ".join(texto.split())


def _anotacion(nodo) -> str:
    if nodo is None:
        return ""
    return _segmento("", nodo) if False else ast.unparse(nodo)


def _parametros(funcion: ast.AST) -> list[dict]:
    args = funcion.args
    posicionales = [a.arg for a in args.posonlyargs] + [a.arg for a in args.args]
    anotaciones = {}
    for a in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs):
        anotaciones[a.arg] = _anotacion(a.annotation)
    valores = {}
    todos = list(args.posonlyargs) + list(args.args)
    for nombre, defecto in zip(todos[len(todos) - len(args.defaults):], args.defaults):
        valores[nombre] = _segmento("", defecto) if False else ast.unparse(defecto)
    for a, defecto in zip(args.kwonlyargs, args.kw_defaults):
        if defecto is not None:
            valores[a.arg] = ast.unparse(defecto)
    salida = []
    for nombre in posicionales:
        salida.append({"nombre": nombre, "anotacion": anotaciones.get(nombre, ""),
                       "defecto": valores.get(nombre, "")})
    if args.vararg:
        salida.append({"nombre": "*" + args.vararg.arg,
                       "anotacion": _anotacion(args.vararg.annotation), "defecto": ""})
    for nombre in [a.arg for a in args.kwonlyargs]:
        salida.append({"nombre": nombre, "anotacion": anotaciones.get(nombre, ""),
                       "defecto": valores.get(nombre, "")})
    if args.kwarg:
        salida.append({"nombre": "**" + args.kwarg.arg,
                       "anotacion": _anotacion(args.kwarg.annotation), "defecto": ""})
    return salida


def _referencias(nodo: ast.AST) -> set[str]:
    """Nombres y atributos que aparecen dentro de un bloque."""
    nombres = set()
    for hijo in ast.walk(nodo):
        if isinstance(hijo, ast.Name):
            nombres.add(hijo.id)
        elif isinstance(hijo, ast.Attribute):
            nombres.add(hijo.attr)
    return nombres


def _docstring(nodo) -> str:
    texto = ast.get_docstring(nodo) or ""
    primera = texto.strip().split("\n")[0].strip()
    return primera


def _clase(nodo: ast.ClassDef, fuente: str) -> dict:
    metodos = []
    atributos = {}
    for hijo in nodo.body:
        if isinstance(hijo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            refs = _referencias(hijo)
            for nombre in refs:
                if isinstance(nombre, str):
                    pass
            metodos.append({
                "nombre": hijo.name,
                "tipo": "async" if isinstance(hijo, ast.AsyncFunctionDef) else "def",
                "parametros": _parametros(hijo),
                "retorno": _anotacion(hijo.returns),
                "doc": _docstring(hijo),
                "linea": hijo.lineno,
                "fin": getattr(hijo, "end_lineno", hijo.lineno),
                "decoradores": [ast.unparse(d) for d in hijo.decorator_list],
                "refs": refs,
            })
            # atributos self.x asignados dentro del metodo
            for sub in ast.walk(hijo):
                if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) \
                        and sub.value.id == "self" and isinstance(sub.ctx, ast.Store):
                    atributos.setdefault(sub.attr, set())

    # segunda pasada: quien usa cada atributo
    for metodo in metodos:
        for nombre in atributos:
            if nombre in metodo["refs"]:
                atributos[nombre].add(metodo["nombre"])

    return {
        "nombre": nodo.name,
        "bases": [ast.unparse(b) for b in nodo.bases],
        "doc": _docstring(nodo),
        "linea": nodo.lineno,
        "fin": getattr(nodo, "end_lineno", nodo.lineno),
        "metodos": metodos,
        "atributos": {k: sorted(v) for k, v in sorted(atributos.items())},
    }


def analizar_modulo(ruta: Path) -> dict:
    fuente = ruta.read_text(encoding="utf-8")
    arbol = ast.parse(fuente)

    constantes = []
    for nodo in arbol.body:
        if isinstance(nodo, (ast.Assign, ast.AnnAssign)):
            objetivos = nodo.targets if isinstance(nodo, ast.Assign) else [nodo.target]
            for objetivo in objetivos:
                if not isinstance(objetivo, ast.Name):
                    continue
                nombre = objetivo.id
                if nombre in RUIDO:
                    continue
                try:
                    valor = ast.unparse(nodo.value)
                except Exception:  # noqa: BLE001
                    valor = ""
                if len(valor) > 70:
                    valor = valor[:67] + "..."
                constantes.append({
                    "nombre": nombre,
                    "valor": valor,
                    "linea": nodo.lineno,
                })

    funciones = []
    clases = []
    for nodo in arbol.body:
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funciones.append({
                "nombre": nodo.name,
                "tipo": "async" if isinstance(nodo, ast.AsyncFunctionDef) else "def",
                "parametros": _parametros(nodo),
                "retorno": _anotacion(nodo.returns),
                "doc": _docstring(nodo),
                "linea": nodo.lineno,
                "fin": getattr(nodo, "end_lineno", nodo.lineno),
                "decoradores": [ast.unparse(d) for d in nodo.decorator_list],
                "refs": _referencias(nodo),
            })
        elif isinstance(nodo, ast.ClassDef):
            clases.append(_clase(nodo, fuente))

    # uso de constantes por funcion o metodo
    bloques = []
    for funcion in funciones:
        bloques.append((funcion["nombre"], funcion["refs"]))
    for clase in clases:
        for metodo in clase["metodos"]:
            bloques.append(("%s.%s" % (clase["nombre"], metodo["nombre"]),
                            metodo["refs"]))

    for constante in constantes:
        usos = [nombre for nombre, refs in bloques if constante["nombre"] in refs]
        constante["usos"] = usos

    return {
        "archivo": ruta.name,
        "ruta": str(ruta.relative_to(RAIZ)).replace("\\", "/"),
        "lineas": len(fuente.splitlines()),
        "doc": _docstring(arbol),
        "constantes": constantes,
        "funciones": funciones,
        "clases": clases,
    }


def analizar_proyecto() -> list[dict]:
    modulos = []
    for carpeta in ("firmware", "backend"):
        for ruta in sorted((RAIZ / carpeta).rglob("*.py")):
            if "__pycache__" in ruta.parts:
                continue
            modulos.append(analizar_modulo(ruta))
    return modulos


if __name__ == "__main__":
    import json

    datos = analizar_proyecto()
    destino = RAIZ / ".tmp" / "analisis_codigo.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(datos, ensure_ascii=False, indent=1,
                   default=lambda o: sorted(o) if isinstance(o, set) else str(o)),
        encoding="utf-8")
    total_funciones = sum(len(m["funciones"]) + sum(len(c["metodos"]) for c in m["clases"])
                          for m in datos)
    total_clases = sum(len(m["clases"]) for m in datos)
    total_constantes = sum(len(m["constantes"]) for m in datos)
    print("modulos:", len(datos), "| clases:", total_clases,
          "| funciones:", total_funciones, "| constantes:", total_constantes)
