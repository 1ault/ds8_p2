"""Genera la documentacion extendida (DOCX) del proyecto Centinela IoT.

Tres bloques:
  1. Catalogo de modulos: funciones, parametros tipados, retornos y variables
     con las funciones donde se usan.
  2. Codigo y SQL comentados: que hace cada elemento y listados linea por
     linea de las funciones criticas.
  3. Analisis funcional: como funciona, a quien detecta y cumplimiento.

Los datos de firmas y usos vienen del analizador AST; los textos editoriales,
de `_datos_documentacion`.

Uso:
    python scripts/build_documentacion_extendida.py
Salida:
    docs/manuales/Documentacion_Extendida_Centinela_IoT.docx
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
for ruta in (str(RAIZ), str(RAIZ / "scripts")):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

import _datos_documentacion as datos  # noqa: E402
from _manual_estilo import GRIS, Manual  # noqa: E402

SALIDA = (RAIZ / "docs" / "manuales" /
          "Documentacion_Extendida_Centinela_IoT.docx")
ANALISIS = RAIZ / ".tmp" / "analisis_codigo.json"
VERSION = "2.0.0"

MONO_FUENTE = 7.4
FUENTE_TABLA = 7.8


# ---------------------------------------------------------------------------
# Utilidades de formato
# ---------------------------------------------------------------------------
def firma(elemento: dict) -> str:
    """Reconstruye la firma con tipos y valores por defecto."""
    partes = []
    for parametro in elemento.get("parametros", []):
        trozo = parametro["nombre"]
        if parametro.get("anotacion"):
            trozo += ": " + parametro["anotacion"]
        if parametro.get("defecto"):
            trozo += " = " + parametro["defecto"]
        partes.append(trozo)
    retorno = elemento.get("retorno") or ""
    texto = "%s(%s)" % (elemento["nombre"], ", ".join(partes))
    if retorno:
        texto += " -> " + retorno
    return texto


def parametros(elemento: dict) -> str:
    """Lista de parametros; omite el tipo cuando no hay anotacion."""
    filas = []
    for parametro in elemento.get("parametros", []):
        trozo = parametro["nombre"]
        if parametro.get("anotacion"):
            trozo += ": %s" % parametro["anotacion"]
        defecto = parametro.get("defecto")
        if defecto:
            trozo += " = %s" % defecto
        filas.append(trozo)
    return "; ".join(filas) if filas else "—"


def con_anotaciones(elementos) -> bool:
    """True si el modulo declara al menos un tipo."""
    for _nombre, elemento in elementos:
        if elemento.get("retorno"):
            return True
        for parametro in elemento.get("parametros", []):
            if parametro.get("anotacion"):
                return True
    return False


def descripcion(ruta: str, nombre: str, docstring: str) -> str:
    """Descripcion editorial, con clave calificada por modulo si existe."""
    clave = "%s::%s" % (ruta, nombre)
    return (datos.ELEMENTOS.get(clave)
            or datos.ELEMENTOS.get(nombre)
            or docstring
            or "—")


def recortar(texto: str, limite: int = 120) -> str:
    texto = " ".join((texto or "").split())
    return texto if len(texto) <= limite else texto[:limite - 1] + "…"


def ruta_corta(ruta: str) -> str:
    return ruta.replace("firmware/", "").replace("backend/", "")


# ---------------------------------------------------------------------------
# Tablas especiales
# ---------------------------------------------------------------------------
def tabla_listado(manual: Manual, ruta: Path, comentarios: dict[int, str]) -> None:
    """Tabla linea por linea: numero, codigo y comentario."""
    if not ruta.exists():
        manual.parrafo("**[Archivo no disponible]**")
        return
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    filas = []
    for numero in sorted(comentarios):
        codigo = lineas[numero - 1].expandtabs(4)
        if len(codigo) > 84:
            codigo = codigo[:81] + "..."
        filas.append((str(numero), codigo.replace(" ", "\u00a0"), comentarios[numero]))
    manual.tabla(["Línea", "Código", "Qué hace"],
                 filas, anchos=[1.1, 8.1, 7.2], fuente=MONO_FUENTE,
                 alinear_centro=(0,), primera_columna_negrita=False)


def tabla_lineas(manual: Manual, modulo: dict) -> None:
    """Rangos de lineas y descripcion de cada elemento del modulo."""
    ruta = modulo["ruta"]
    filas = []
    for clase in modulo["clases"]:
        filas.append(("%d-%d" % (clase["linea"], clase["fin"]),
                      "class " + clase["nombre"],
                      descripcion(ruta, clase["nombre"], clase["doc"])))
        for metodo in clase["metodos"]:
            nombre = "%s.%s" % (clase["nombre"], metodo["nombre"])
            filas.append(("%d-%d" % (metodo["linea"], metodo["fin"]),
                          nombre, descripcion(ruta, nombre, metodo["doc"])))
    for funcion in modulo["funciones"]:
        filas.append(("%d-%d" % (funcion["linea"], funcion["fin"]),
                      funcion["nombre"],
                      descripcion(ruta, funcion["nombre"], funcion["doc"])))
    if not filas:
        manual.parrafo("El modulo solo contiene constantes.")
        return
    manual.tabla(["Líneas", "Elemento", "Qué hace"], filas,
                 anchos=[1.8, 4.0, 10.6], fuente=FUENTE_TABLA,
                 alinear_centro=(0,))


# ---------------------------------------------------------------------------
# Capitulo 1
# ---------------------------------------------------------------------------
def capitulo_modulos(manual: Manual, modulos: list[dict]) -> None:
    manual.h1("1. Catálogo de módulos")
    manual.parrafo("Este capítulo es la referencia rápida del código: qué hace cada módulo, "
                   "qué funciones y clases expone, **qué parámetros recibe cada una con su "
                   "tipo**, qué devuelve y **en qué parte del módulo se usa cada variable**.")
    manual.nota("El firmware está escrito para MicroPython y **no usa anotaciones de tipo** "
                "(no aportan nada en el dispositivo y consumen memoria). Por eso sus "
                "parámetros aparecen con el nombre y, cuando importa, el dominio de valores "
                "en la descripción. El backend, que corre en CPython, sí está tipado: allí "
                "se muestra el tipo anotado y el valor por defecto.", "nota")

    manual.h2("1.1 Cómo leer las tablas")
    manual.tabla(
        ["Columna", "Significado"],
        [
            ["Elemento", "nombre de la función o método, precedido por la clase cuando aplica"],
            ["Parámetros", "nombre, tipo anotado (si existe) y valor por defecto"],
            ["Retorno", "tipo declarado; «—» cuando la función no devuelve nada"],
            ["Usado en", "funciones y métodos del propio módulo que leen esa variable"],
            ["Líneas", "rango de líneas en el archivo, para localizarlo en el editor"],
        ],
        anchos=[3.0, 13.6],
        pie="Convenciones de las tablas de este capítulo.",
    )

    manual.h2("1.2 Resumen del código")
    total_lineas = sum(m["lineas"] for m in modulos)
    total_funciones = sum(len(m["funciones"]) + sum(len(c["metodos"]) for c in m["clases"])
                          for m in modulos)
    total_clases = sum(len(m["clases"]) for m in modulos)
    total_constantes = sum(len(m["constantes"]) for m in modulos)
    manual.tabla(
        ["Indicador", "Valor"],
        [
            ["Módulos analizados", "%d (12 de firmware y 12 de backend)" % len(modulos)],
            ["Líneas de código", "%d" % total_lineas],
            ["Clases", "%d" % total_clases],
            ["Funciones y métodos", "%d" % total_funciones],
            ["Constantes y variables de módulo", "%d" % total_constantes],
        ],
        anchos=[6.6, 10.0],
        pie="Dimensiones del código analizado.",
    )

    manual.h2("1.3 Módulos del firmware")
    for modulo in modulos:
        if not modulo["ruta"].startswith("firmware/"):
            continue
        _ficha_modulo(manual, modulo)

    manual.h2("1.4 Módulos del backend")
    for modulo in modulos:
        if not modulo["ruta"].startswith("backend/"):
            continue
        _ficha_modulo(manual, modulo)

    manual.h2("1.5 Archivos SQL y del panel")
    manual.parrafo("Los tres archivos SQL y los cuatro del panel no son módulos Python, así "
                   "que no tienen firmas ni tipos; se documentan en el capítulo 2 junto con "
                   "el resto del código comentado. El panel se compone de `index.html`, "
                   "`login.html`, `styles.css` y `app.js`.")
    manual.tabla(
        ["Archivo", "Líneas", "Contenido"],
        [
            ["`sql/schema.sql`", "126", "5 tablas, 7 índices y 5 vistas"],
            ["`sql/seed.sql`", "118", "288 lecturas, 7 eventos, 6 comandos y 3 transiciones"],
            ["`sql/consultas.sql`", "196", "12 consultas de históricos documentadas"],
            ["`backend/web/static/index.html`", "205", "estructura del panel"],
            ["`backend/web/static/login.html`", "44", "formulario de acceso"],
            ["`backend/web/static/styles.css`", "559", "tema oscuro y rejilla adaptable"],
            ["`backend/web/static/app.js`", "448", "lógica del panel y canal SSE"],
        ],
        anchos=[6.4, 2.0, 8.2],
        alinear_centro=(1,),
        pie="Archivos no Python del proyecto.",
    )


def _ficha_modulo(manual: Manual, modulo: dict) -> None:
    info = datos.MODULOS.get(modulo["ruta"], {})
    manual.h3("%s  ·  %d líneas" % (modulo["ruta"], modulo["lineas"]))
    manual.parrafo(info.get("proposito") or modulo.get("doc") or "—")
    if info.get("depende"):
        manual.parrafo("**Depende de:** %s" % info["depende"], espacio_despues=8)

    if modulo["constantes"]:
        filas = []
        for constante in modulo["constantes"]:
            valor = constante["valor"]
            if len(valor) > 46:
                valor = valor[:43] + "..."
            usos = constante["usos"]
            resumen = ", ".join(usos[:4]) if usos else "—"
            if len(usos) > 4:
                resumen += " (+%d)" % (len(usos) - 4)
            filas.append(("`%s`" % constante["nombre"], valor.replace(" ", "\u00a0"),
                          resumen))
        manual.tabla(["Variable o constante", "Valor", "Usado en"],
                     filas, anchos=[5.2, 5.8, 6.6], fuente=7.4,
                     primera_columna_negrita=False)

    if modulo["clases"]:
        filas = []
        for clase in modulo["clases"]:
            atributos = clase["atributos"]
            if atributos:
                detalle = "; ".join(
                    "%s (%s)" % (nombre, ", ".join(usos[:3]) if usos else "—")
                    for nombre, usos in list(atributos.items())[:6])
                if len(atributos) > 6:
                    detalle += "; +%d" % (len(atributos) - 6)
            else:
                detalle = "—"
            filas.append(("**%s**" % clase["nombre"],
                          descripcion(modulo["ruta"], clase["nombre"], clase["doc"]),
                          detalle))
        manual.tabla(["Clase", "Propósito", "Atributos (métodos que los usan)"],
                     filas, anchos=[3.4, 6.4, 7.8], fuente=7.4)

    elementos = []
    for clase in modulo["clases"]:
        for metodo in clase["metodos"]:
            elementos.append(("%s.%s" % (clase["nombre"], metodo["nombre"]), metodo))
    for funcion in modulo["funciones"]:
        elementos.append((funcion["nombre"], funcion))

    if elementos:
        tipados = con_anotaciones(elementos)
        filas = []
        for nombre, elemento in elementos:
            prefijo = "async " if elemento.get("tipo") == "async" else ""
            if tipados:
                filas.append(("%s`%s`" % (prefijo, nombre),
                              firma(elemento), parametros(elemento),
                              elemento.get("retorno") or "—"))
            else:
                filas.append(("%s`%s`" % (prefijo, nombre),
                              firma(elemento), parametros(elemento)))
        if tipados:
            manual.tabla(["Elemento", "Firma", "Parámetros (tipo)", "Retorno"],
                         filas, anchos=[3.4, 6.0, 4.6, 2.6], fuente=7.0,
                         primera_columna_negrita=False)
        else:
            manual.tabla(["Elemento", "Firma", "Parámetros"],
                         filas, anchos=[3.6, 7.2, 5.8], fuente=7.2,
                         primera_columna_negrita=False)


# ---------------------------------------------------------------------------
# Capitulo 2
# ---------------------------------------------------------------------------
def capitulo_codigo(manual: Manual, modulos: list[dict]) -> None:
    manual.h1("2. Código y SQL comentados")
    manual.parrafo("Este capítulo responde a «qué hace cada función y cada componente». Se "
                   "organiza en tres partes: el firmware, el backend y los archivos SQL y del "
                   "panel. Cada módulo incluye una tabla con el rango de líneas de **todos** "
                   "sus elementos y, a continuación, las funciones críticas aparecen con un "
                   "**listado línea por línea**: número de línea, código real y explicación.")

    manual.nota("Un listado línea por línea de las 15 000 líneas del proyecto sería "
                "ilegible y no aportaría nada: la mayoría son líneas de formato. Por eso se "
                "comenta **cada elemento en bloque** (todas las funciones y clases) y se "
                "desciende a línea por línea en las seis funciones donde se decide la "
                "seguridad y la integridad de los datos.", "truco")

    manual.h2("2.1 Firmware")
    for modulo in modulos:
        if not modulo["ruta"].startswith("firmware/"):
            continue
        _ficha_codigo(manual, modulo)

    manual.h2("2.2 Funciones críticas del firmware, línea por línea")
    for clave in ("firmware/fsm.py::SecurityFSM._presencia",
                  "firmware/mqtt_client.py::encode_connect",
                  "firmware/app.py::Controlador._ciclo"):
        _listado(manual, clave)

    manual.h2("2.3 Backend")
    for modulo in modulos:
        if not modulo["ruta"].startswith("backend/"):
            continue
        _ficha_codigo(manual, modulo)

    manual.h2("2.4 Funciones críticas del backend, línea por línea")
    for clave in ("backend/storage.py::Almacen.guardar_lectura",
                  "backend/commands.py::ServicioComandos.ejecutar",
                  "backend/web/app.py::api_stream"):
        _listado(manual, clave)

    _sql(manual)
    _frontend(manual)


def _ficha_codigo(manual: Manual, modulo: dict) -> None:
    info = datos.MODULOS.get(modulo["ruta"], {})
    manual.h3("%s  ·  %d líneas" % (modulo["ruta"], modulo["lineas"]))
    manual.parrafo(info.get("proposito") or "—", espacio_despues=6)
    tabla_lineas(manual, modulo)


def _listado(manual: Manual, clave: str) -> None:
    ruta_texto, _, elemento = clave.partition("::")
    manual.h4("%s — `%s`" % (ruta_texto, elemento))
    manual.parrafo("Listado completo con el número de línea real del archivo:")
    tabla_listado(manual, RAIZ / ruta_texto, datos.LISTADOS.get(clave, {}))


def _sql(manual: Manual) -> None:
    manual.h2("2.5 Archivos SQL")

    manual.h3("`sql/schema.sql` · estructura")
    manual.parrafo("Cada sentencia del esquema y su función:")
    manual.tabla(["Objeto", "Qué hace"], datos.SQL_SCHEMA,
                 anchos=[6.2, 10.4], fuente=7.6, primera_columna_negrita=False)

    manual.parrafo("Ejemplo de una tabla completa, con todas sus columnas y restricciones:")
    manual.codigo("""CREATE TABLE IF NOT EXISTS readings (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id      TEXT NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    ts_epoch       REAL NOT NULL,
    ts_utc         TEXT NOT NULL,
    temp_c         REAL,
    hum_pct        REAL,
    lux            REAL,
    dist_cm        REAL,
    motion         INTEGER NOT NULL DEFAULT 0,
    state          TEXT    NOT NULL DEFAULT 'DESCONOCIDO',
    alarm          INTEGER NOT NULL DEFAULT 0,
    alerts         INTEGER NOT NULL DEFAULT 0,
    payload        TEXT,
    CHECK (state IN ('DISARMED', 'ARMING', 'ARMED', 'ALARM', 'DESCONOCIDO')),
    CHECK (motion IN (0, 1))
);""")
    manual.parrafo("La columna `ts_epoch` sirve para calcular e indexar; `ts_utc` existe para "
                   "que el dato se pueda leer y exportar sin conversiones. El `CHECK` impide "
                   "que un estado desconocido entre en la base.")

    manual.h3("`sql/consultas.sql` · las 12 consultas")
    manual.tabla(["Consulta", "Para qué sirve"], datos.SQL_CONSULTAS,
                 anchos=[6.4, 10.2], fuente=7.6, primera_columna_negrita=False)
    manual.parrafo("Las dos consultas que más se usan en la operación:")
    manual.codigo("""-- 01. Ultima lectura de cada dispositivo
SELECT device_id AS dispositivo, ts_utc AS momento, temp_c, hum_pct, lux,
       dist_cm, state AS estado, alarm AS alarma
  FROM v_ultima_lectura ORDER BY device_id;

-- 11. Huecos de telemetria (caidas del nodo)
SELECT ts_utc, ROUND(siguiente - ts_epoch, 1) AS segundos_sin_datos
  FROM (SELECT ts_epoch, ts_utc,
               LEAD(ts_epoch) OVER (ORDER BY ts_epoch) AS siguiente
          FROM readings WHERE device_id = :device_id)
 WHERE siguiente - ts_epoch > 30 ORDER BY ts_epoch DESC LIMIT 20;""")

    manual.h3("`sql/seed.sql` · datos de demostración")
    manual.tabla(["Bloque", "Qué hace"], datos.SQL_SEED,
                 anchos=[4.6, 12.0], fuente=7.6)
    manual.parrafo("El bloque que genera las 24 horas de histórico usa una consulta "
                   "recursiva y una función seno para simular el ciclo día-noche:")
    manual.codigo("""WITH RECURSIVE serie(n) AS (
    SELECT 0 UNION ALL SELECT n + 1 FROM serie WHERE n < 287
)
INSERT INTO readings (device_id, ts_epoch, ts_utc, temp_c, hum_pct, lux, ...)
SELECT 'dev01',
       strftime('%s', 'now', '-24 hours', '+' || (n * 5) || ' minutes') + 0.0,
       strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-24 hours', '+' || (n * 5) || ' minutes'),
       ROUND(24.0 + 3.0 * sin((n % 288) * 3.14159 / 144.0) + ..., 1),
       ...
  FROM serie;""")


def _frontend(manual: Manual) -> None:
    manual.h2("2.6 Panel: HTML, CSS y JavaScript")
    for archivo, elementos in datos.FRONTEND.items():
        manual.h3("`%s`" % archivo)
        manual.parrafo(datos.MODULOS.get(archivo, {}).get("proposito")
                       or "Componente del panel del operador.")
        manual.tabla(["Elemento", "Qué hace"], elementos,
                     anchos=[5.0, 11.6], fuente=7.6, primera_columna_negrita=False)


# ---------------------------------------------------------------------------
# Capitulo 3
# ---------------------------------------------------------------------------
def capitulo_analisis(manual: Manual) -> None:
    manual.h1("3. Cómo funciona, a quién detecta y cumplimiento")

    manual.h2("3.1 Recorrido de una lectura")
    manual.parrafo("Cada 50 ms el nodo revisa si algún sensor cumplió su periodo. Cuando lo "
                   "hace, guarda la lectura, avanza los temporizadores de la máquina de "
                   "estados y evalúa tres reglas: movimiento con flanco de subida estando "
                   "armado, distancia menor o igual al umbral estando armado, y temperatura "
                   "por encima del límite. Si alguna se cumple, la máquina devuelve efectos y "
                   "el controlador los aplica: enciende la sirena, marca la cerradura, "
                   "actualiza los LEDs y publica un evento.")
    manual.parrafo("En paralelo, cada 5 segundos publica la telemetría por MQTT. El backend "
                   "la recibe, la guarda en SQLite con la hora del servidor, la empuja al "
                   "panel por SSE y, si hay claves configuradas, la sube a ThingSpeak.")
    manual.tabla(
        ["Paso", "Qué ocurre", "Tiempo"],
        [
            ["1", "el bucle revisa los periodos de los cuatro sensores", "cada 50 ms"],
            ["2", "lectura con validación y mediana", "según el sensor"],
            ["3", "avance de temporizadores de la máquina de estados", "cada ciclo"],
            ["4", "evaluación de las tres reglas de seguridad", "cada ciclo"],
            ["5", "aplicación de efectos (sirena, cerradura, LEDs, eventos)", "al ocurrir"],
            ["6", "publicación de telemetría por MQTT QoS 0", "cada 5 s"],
            ["7", "guardado en SQLite con `ts_epoch` y `ts_utc`", "al recibir"],
            ["8", "evento SSE al panel y actualización de la gráfica", "inmediato"],
            ["9", "subida al canal de ThingSpeak", "cada 20 s"],
        ],
        anchos=[1.4, 11.6, 3.6],
        alinear_centro=(0, 2),
        pie="Recorrido completo de una lectura.",
    )

    manual.h2("3.2 Recorrido de un comando")
    manual.parrafo("Un comando puede nacer en el panel, en ThingSpeak o en el pulsador del "
                   "nodo. Los tres caminos llegan al mismo servicio, que primero valida "
                   "(lista blanca, tipos y rangos), después **guarda el comando como "
                   "PENDIENTE**, luego lo publica y finalmente espera la confirmación. Si el "
                   "nodo responde, el comando se cierra como `OK` o `RECHAZADO` con su "
                   "latencia; si no responde en 8 segundos, queda como `TIMEOUT`. Nada queda "
                   "sin estado final.")
    manual.tabla(
        ["Situación", "Qué ve el operador", "Qué queda registrado"],
        [
            ["Comando inválido", "«comando no permitido»", "no se publica; solo el intento"],
            ["Sin broker", "«sin conexión MQTT»", "rechazo en el contador de la sesión"],
            ["Nodo ejecuta", "«confirmado por el nodo»", "`OK` con latencia en milisegundos"],
            ["Nodo rechaza (PIN mal)", "el motivo del nodo", "`RECHAZADO` con el motivo"],
            ["Nodo no responde", "aviso de timeout", "`TIMEOUT` a los 8 s"],
            ["Falla la publicación", "error de envío", "`ERROR` con el motivo"],
        ],
        anchos=[4.2, 5.8, 6.6],
        pie="Resultados posibles de un comando y su registro.",
    )

    manual.h2("3.3 A quién detecta")
    manual.parrafo("El sistema detecta **presencia física** en el área vigilada: una persona "
                   "que se mueve frente al sensor de infrarrojos o que se acerca a menos de "
                   "80 cm del sensor de distancia. No identifica a nadie; avisa de que algo "
                   "se movió y deja constancia. La tabla resume qué mide cada sensor y qué "
                   "provoca.")
    manual.tabla(["Sensor", "Magnitud", "Condición", "Alcance", "Consecuencia"],
                 datos.DETECCION, anchos=[3.0, 3.4, 4.2, 3.4, 2.6], fuente=7.4)
    manual.nota("El umbral de 80 cm y la temperatura de 45 °C son configurables por comando "
                "(`set_config`), sin necesidad de reprogramar el nodo.", "truco")

    manual.h2("3.4 Qué no detecta")
    manual.parrafo("Ser explícito con los límites es parte de la seguridad: un sistema que "
                   "promete más de lo que hace genera falsas expectativas.")
    manual.vinetas(datos.NO_DETECTA)
    manual.nota("Para cubrir la apertura de puertas y ventanas habría que añadir un sensor "
                "magnético de contacto; para humo o gas, un detector específico. La "
                "arquitectura admite ambos sin cambiar el backend: bastaría un sensor nuevo y "
                "un campo más en la telemetría.", "aviso")

    manual.h2("3.5 Cumplimiento de los requisitos del parcial")
    manual.parrafo("La siguiente tabla contrasta cada requisito del enunciado con la "
                   "evidencia concreta en el repositorio. La columna «Estado» distingue lo "
                   "que está implementado y verificado de lo que depende de una acción del "
                   "estudiante.")
    filas = [("%s" % requisito, "**%s**" % estado, evidencia, donde)
             for requisito, estado, evidencia, donde in datos.CUMPLIMIENTO]
    manual.tabla(["Requisito del enunciado", "Estado", "Evidencia", "Dónde"],
                 filas, anchos=[4.6, 2.6, 5.6, 5.2], fuente=7.2,
                 alinear_centro=(1,), primera_columna_negrita=False)

    manual.h2("3.6 Salvedades y cómo cerrarlas")
    manual.parrafo("Tres puntos no pueden darse por cerrados sin intervención del estudiante "
                   "o de un navegador visible. Se documentan con su causa y su solución:")
    manual.tabla(["Salvedad", "Por qué", "Cómo se cierra"], datos.SALVEDADES,
                 anchos=[4.6, 7.0, 5.0], fuente=7.4)

    manual.h2("3.7 Veredicto")
    manual.parrafo("**Dieciséis de los diecisiete requisitos funcionales** están "
                   "implementados, documentados y verificados con pruebas o capturas; el "
                   "restante (publicar el repositorio en GitHub) es un paso administrativo "
                   "que depende de crear el remoto y hacer `push`. De los entregables "
                   "documentales, todos están presentes: README, `requirements.txt`, tres "
                   "scripts SQL, cinco diagramas, capturas del panel y del simulador, informe "
                   "técnico, manual técnico, manual del usuario y este anexo.")
    manual.parrafo("Las tres salvedades no afectan al cumplimiento del enunciado: dos son "
                   "limitaciones del simulador documentadas de forma explícita y la tercera "
                   "requiere las claves de una cuenta propia de ThingSpeak. Ninguna se "
                   "presenta como resuelta.")

    manual.parrafo()
    manual.parrafo("— Fin de la documentación extendida —", alineacion="centro",
                   cursiva=True, color=GRIS)


# ---------------------------------------------------------------------------
# Construccion
# ---------------------------------------------------------------------------
def construir() -> Path:
    if not ANALISIS.exists():
        raise SystemExit("Falta el analisis: ejecute scripts/_analisis_codigo.py")
    modulos = json.loads(ANALISIS.read_text(encoding="utf-8"))

    manual = Manual(
        titulo="Documentación extendida",
        subtitulo="Catálogo de módulos, código y SQL comentados, y análisis funcional "
                  "del sistema",
        version=VERSION,
        autor="Estudiante de Desarrollo de Software VIII",
        materia="Parcial #2 · Desarrollo de Software VIII",
        encabezado="Centinela IoT · Documentación extendida",
    )

    manual.portada(
        imagen=RAIZ / "docs" / "img" / "flujo_datos.png",
        ancho_imagen_cm=14.6,
        resumen="Anexo de referencia del código: qué hace cada módulo y cada función, qué "
                "parámetros recibe con su tipo, dónde se usa cada variable, el código y el "
                "SQL comentados, y el análisis de funcionamiento, detección y cumplimiento "
                "de los requisitos del parcial.",
        metadatos=[
            ("Asignatura", "Desarrollo de Software VIII"),
            ("Documento", "Documentación extendida (anexo técnico)"),
            ("Versión del sistema", "v%s" % VERSION),
            ("Autor", "Estudiante de Desarrollo de Software VIII"),
            ("Fecha", manual.fecha),
        ],
    )

    manual.h1("Contenido", nueva_pagina=False)
    manual.tabla(
        ["Capítulo", "Qué encontrarás"],
        [
            ["1. Catálogo de módulos", "propósito, dependencias, clases, atributos, firmas "
                                        "con tipos y uso de cada variable"],
            ["2. Código y SQL comentados", "qué hace cada elemento con su rango de líneas y "
                                           "seis listados línea por línea"],
            ["3. Cómo funciona y a quién detecta", "recorrido de lecturas y comandos, "
                                                   "alcance real de la detección"],
            ["3.5–3.7 Cumplimiento", "requisito por requisito, salvedades y veredicto"],
        ],
        anchos=[4.4, 12.2],
        pie="Estructura del anexo.",
    )

    manual.h2("Cómo se generó este documento")
    manual.parrafo("Las firmas, los parámetros con su tipo, los rangos de líneas y la lista de "
                   "funciones que usa cada variable **no se escribieron a mano**: se extraen "
                   "del código con un analizador sintáctico (`scripts/_analisis_codigo.py`), "
                   "de modo que el documento no puede contradecir al repositorio. Los textos "
                   "explicativos sí son editoriales y viven en "
                   "`scripts/_datos_documentacion.py`.")
    manual.codigo("""python scripts\\_analisis_codigo.py            # firmas, tipos y usos
python scripts\\build_documentacion_extendida.py  # este documento""")

    capitulo_modulos(manual, modulos)
    capitulo_codigo(manual, modulos)
    capitulo_analisis(manual)
    return manual.guardar(SALIDA)


if __name__ == "__main__":
    ruta = construir()
    print("generado:", ruta)
