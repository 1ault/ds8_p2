"""Genera la guia practica de prueba del monitoreo (DOCX).

Uso:
    python scripts/build_guia_prueba.py
Salida:
    docs/manuales/Guia_Prueba_Monitoreo.docx
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
for ruta in (str(RAIZ), str(RAIZ / "scripts")):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

from _datos_documentacion import SQL_CONSULTAS  # noqa: E402
from _manual_estilo import GRIS, Manual  # noqa: E402

CAP = RAIZ / "docs" / "capturas"
SALIDA = RAIZ / "docs" / "manuales" / "Guia_Prueba_Monitoreo.docx"
VERSION = "2.0.0"


def construir() -> Path:
    manual = Manual(
        titulo="Guía de prueba del monitoreo",
        subtitulo="Cómo arrancar la interfaz, comprobar que registra, ubicar las lecturas "
                  "y consultar los históricos",
        version=VERSION,
        autor="Estudiante de Desarrollo de Software VIII",
        materia="Parcial #2 · Desarrollo de Software VIII",
        encabezado="Centinela IoT · Guía de prueba del monitoreo",
    )

    manual.portada(
        imagen=CAP / "01_panel_estado.png",
        ancho_imagen_cm=15.4,
        resumen="Receta paso a paso para verificar el panel en tiempo real, saber dónde "
                "queda cada lectura en la base de datos y ejecutar las consultas del "
                "histórico por consola, por SQL o por la API.",
    )

    # ------------------------------------------------------------- contenido
    manual.h1("Contenido", nueva_pagina=False)
    manual.tabla(
        ["Sección", "Qué resuelve"],
        [
            ["1. Arrancar la interfaz", "dos caminos: backend normal o demostración sin Internet"],
            ["2. Comprobar la pantalla", "ocho verificaciones concretas con lo que debe verse"],
            ["3. Dónde se guardan las lecturas", "archivo, tablas, columnas y cómo abrirlo"],
            ["4. Ver las consultas", "por consola, por SQL directo y por la API del panel"],
            ["5. Orden sugerido", "secuencia de demostración en ocho pasos"],
            ["6. Problemas frecuentes", "qué hacer si el puerto está ocupado o no hay datos"],
            ["7. Anexo", "todos los comandos en una sola tabla"],
        ],
        anchos=[5.4, 11.2],
        pie="Estructura de la guía.",
    )
    manual.nota("Todos los comandos se ejecutan desde la carpeta del proyecto "
                "(`Parcial2_IoT_Seguridad`) y en Windows. Las rutas de archivo son relativas "
                "a esa carpeta.", "nota")

    # ------------------------------------------------------------- 1. arrancar
    manual.h1("1. Arrancar la interfaz")

    manual.parrafo("Hay dos caminos y conviene conocerlos: el primero levanta el sistema "
                   "completo (panel, broker y base de datos) y el segundo crea un entorno de "
                   "demostración autónomo que funciona sin Internet.")

    manual.h2("1.1 Camino A · backend normal")
    manual.parrafo("Es el sistema real, en el puerto **8000**. Publica y recibe por MQTT y "
                   "guarda todo en SQLite.")
    manual.codigo("""python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python -m backend.main --seed""")
    manual.vinetas([
        "`--seed` carga 288 lecturas de ejemplo para que la gráfica no aparezca vacía. "
        "Omitirlo si quieres empezar de cero.",
        "`--sin-mqtt` arranca solo el panel, sin conexión al broker.",
        "`--sin-login` entra sin pedir credenciales (útil para pruebas rápidas).",
    ])
    manual.parrafo("Abrir después <http://127.0.0.1:8000>. Credenciales iniciales: "
                   "usuario **admin**, contraseña **seguridad2026**.")

    manual.h2("1.2 Camino B · demostración autónoma")
    manual.parrafo("Crea un nodo emulado que publica en bucle, siembra datos y abre el panel "
                   "en el puerto **8010**, sin pedir contraseña.")
    manual.codigo("""python scripts\\demo.py --reset --sembrar""")
    manual.vinetas([
        "`--reset` borra los datos anteriores del dispositivo de ejemplo.",
        "`--sembrar` carga las 288 lecturas de las últimas 24 horas.",
        "`--con-login` obliga a pasar por el formulario de acceso.",
        "`--escenario intruso` fuerza una secuencia de alarma durante la demostración.",
        "`--armar-auto 8` arma el sistema 8 segundos después de arrancar.",
    ])
    manual.parrafo("Abrir <http://127.0.0.1:8010>.")

    manual.h2("1.3 Diferencias entre los dos caminos")
    manual.tabla(
        ["", "Camino A", "Camino B"],
        [
            ["Dirección", "`http://127.0.0.1:8000`", "`http://127.0.0.1:8010`"],
            ["Acceso", "usuario y contraseña", "entra directo"],
            ["Datos que muestra", "los que publique el nodo o el `--seed`", "288 lecturas + nodo emulado en vivo"],
            ["Necesita Internet", "sí, para el broker público", "no"],
            ["Uso recomendado", "prueba real y capturas de entrega", "ensayo de la demostración"],
        ],
        anchos=[3.6, 6.6, 6.4],
        pie="Comparación de los dos modos de arranque.",
    )
    manual.nota("Si no existe archivo `.env`, el sistema arranca igual con valores por "
                "defecto: SQLite local, broker público y sin ThingSpeak. Para cambiar "
                "puerto, credenciales o ruta de la base, copiar `.env.example` a `.env`.", "truco")

    # --------------------------------------------------------- 2. comprobaciones
    manual.h1("2. Comprobar la pantalla")

    manual.parrafo("Estas ocho comprobaciones cubren todo lo que el panel debe demostrar. "
                   "Si las ocho pasan, la interfaz de monitoreo está funcionando.")
    manual.tabla(
        ["#", "Dónde mirar", "Qué debe ocurrir"],
        [
            ["1", "Barra superior", "`MQTT OK`, `NUBE OFF` (normal sin claves) y `EN VIVO ON` "
                                    "en verde; la hora avanza"],
            ["2", "Tarjeta de estado", "`DESARMADO`, cerradura «Cerrada», sirena «Silencio» y "
                                       "alertas en 0"],
            ["3", "Sensores", "seis valores con unidad: 24,3 °C · 55,4 % · 120 lx · 214 cm · "
                              "No · −59 dBm"],
            ["4", "Histórico", "al pulsar `1 H`, `6 H` y `24 H` se redibuja la curva y cambia "
                               "el contador de muestras"],
            ["5", "Eventos", "lista con hora y color de severidad; los críticos en rojo"],
            ["6", "Botón **Armar**", "pasa a `ARMANDO`, el LED verde parpadea y a los 10 s "
                                     "queda en `ARMADO`"],
            ["7", "Botón **Abrir cerradura**", "con el PIN `2468` abre 8 s; con PIN erróneo "
                                               "avisa y al tercer intento bloquea 30 s"],
            ["8", "Últimos comandos", "cada acción aparece con origen, estado (`OK`, "
                                      "`RECHAZADO`, `TIMEOUT`) y milisegundos"],
        ],
        anchos=[0.9, 4.4, 11.3],
        alinear_centro=(0,),
        pie="Las ocho comprobaciones de la interfaz.",
    )
    manual.figura(CAP / "02_panel_alarma.png",
                  "El panel durante una alarma: estado en rojo, sirena activa y eventos "
                  "críticos en el feed.", ancho_cm=16.0)
    manual.nota("Para capturas de pantalla, añadir `?estatico=1` a la dirección: el panel no "
                "abre el canal en vivo y la imagen no cambia a mitad de la captura.", "truco")

    manual.h2("2.1 Qué significa cada píldora")
    manual.tabla(
        ["Indicador", "Significado"],
        [
            ["`MQTT OK` / `MQTT OFF`", "hay o no comunicación con el broker y, por tanto, con el nodo"],
            ["`NUBE OFF`", "ThingSpeak sin configurar; el resto del sistema funciona igual"],
            ["`EN VIVO ON`", "el panel recibe los cambios al instante por el canal SSE"],
            ["Hora de la barra", "hora del servidor; sirve para comparar con los eventos"],
        ],
        anchos=[4.2, 12.4],
        pie="Indicadores de la barra superior.",
    )

    # ------------------------------------------------------------ 3. almacen
    manual.h1("3. Dónde se guardan las lecturas")

    manual.parrafo("Todo lo que muestra el panel está en un archivo **SQLite** dentro del "
                   "proyecto. No hay servidor de base de datos que instalar ni que arrancar.")

    manual.h2("3.1 Ubicación del archivo")
    manual.tabla(
        ["Dato", "Valor"],
        [
            ["Ruta por defecto", "`data\\centinela.db`"],
            ["Variable de entorno", "`DB_PATH` (en el archivo `.env`)"],
            ["Se crea solo", "sí, al arrancar el backend si no existe"],
            ["Versionado en Git", "no: `data/` está en `.gitignore`"],
        ],
        anchos=[4.6, 12.0],
        pie="Datos de conexión de la base.",
    )

    manual.h2("3.2 Tablas")
    manual.tabla(
        ["Tabla", "Qué guarda", "Filas de ejemplo"],
        [
            ["`readings`", "una fila por telemetría, con las ocho magnitudes y el estado",
             "297"],
            ["`events`", "alarmas, cambios de estado y avisos, con severidad", "18"],
            ["`commands`", "cada comando con estado, latencia, resultado y motivo", "7"],
            ["`state_changes`", "transiciones de la máquina de estados con su motivo", "6"],
            ["`devices`", "nodos registrados y su última vez visto", "1"],
        ],
        anchos=[3.2, 9.4, 4.0],
        alinear_centro=(2,),
        pie="Tablas de la base y contenido típico tras la siembra.",
    )
    manual.parrafo("Además hay cinco **vistas** preparadas que resuelven las consultas más "
                   "frecuentes sin escribir el `JOIN` a mano: `v_ultima_lectura`, "
                   "`v_resumen_horario`, `v_salud_comandos`, `v_eventos_criticos` y "
                   "`v_estado_actual`.")

    manual.h2("3.3 Columnas que importan de `readings`")
    manual.tabla(
        ["Columna", "Contenido", "Por qué"],
        [
            ["`id`", "autoincremental", "orden natural de inserción"],
            ["`device_id`", "`dev01`", "permite varios nodos en la misma base"],
            ["`ts_epoch`", "segundos con decimales", "se indexa y se usa para calcular"],
            ["`ts_utc`", "texto ISO-8601 con `Z`", "legible y exportable sin conversiones"],
            ["`temp_c`, `hum_pct`", "temperatura y humedad", "gráfica y promedios"],
            ["`lux`, `dist_cm`", "luminosidad y distancia", "contexto de la detección"],
            ["`motion`, `state`", "movimiento y estado de seguridad", "saber si estaba armado"],
            ["`alarm`, `siren`, `alerts`", "alarma, sirena y contador", "reconstruir un episodio"],
            ["`payload`", "JSON original completo", "auditoría si un dato sorprende"],
        ],
        anchos=[3.6, 5.2, 7.8],
        pie="Columnas principales de la tabla de lecturas.",
    )
    manual.nota("La marca de tiempo la pone **el servidor**, no el nodo: el ESP32 no tiene "
                "reloj y un reinicio rompería el histórico. Las dos columnas de tiempo "
                "existen para poder calcular rápido (`ts_epoch`) y leer sin conversiones "
                "(`ts_utc`).", "nota")

    manual.h2("3.4 Cómo abrirla")
    manual.parrafo("Con **DB Browser for SQLite** (gratuito) se ven las tablas a ojo. Desde "
                   "consola, la consulta directa:")
    manual.codigo("""sqlite3 data\\centinela.db "SELECT ts_utc, temp_c, hum_pct, state
                                  FROM readings ORDER BY ts_epoch DESC LIMIT 10;"
""")
    manual.parrafo("Si `sqlite3` no está instalado, sirve Python, que ya viene con el "
                   "proyecto:")
    manual.codigo("""python -c "import sqlite3; c = sqlite3.connect('data/centinela.db');
[print(f) for f in c.execute('SELECT ts_utc, state FROM readings ORDER BY ts_epoch DESC LIMIT 5')]"
""")

    # ------------------------------------------------------------ 4. consultas
    manual.h1("4. Ver las consultas")

    manual.parrafo("Hay tres formas de consultar el histórico y las tres devuelven lo mismo. "
                   "La primera es la más cómoda para demostrar; la segunda, la que conviene "
                   "mostrar si piden SQL; la tercera es la que usa el panel por dentro.")

    manual.h2("4.1 Por consola, con el CLI del proyecto")
    manual.codigo("""python -m backend.cli resumen
python -m backend.cli historico --horas 6 --limite 20
python -m backend.cli eventos --severidad critical
python -m backend.cli comandos --limite 15
python -m backend.cli estadisticas
python -m backend.cli cambios
python -m backend.cli agregado --horas 24
python -m backend.cli dispositivos""")
    manual.tabla(
        ["Subcomando", "Qué muestra", "Opciones"],
        [
            ["`resumen`", "última lectura y estado actual", "`--device`"],
            ["`historico`", "lecturas de las últimas horas", "`--horas`, `--limite`"],
            ["`eventos`", "eventos registrados", "`--limite`, `--severidad`"],
            ["`comandos`", "comandos con estado y latencia", "`--limite`"],
            ["`estadisticas`", "agregados generales", "`--device`"],
            ["`cambios`", "transiciones de estado", "`--limite`"],
            ["`agregado`", "promedios por hora", "`--horas`"],
            ["`dispositivos`", "nodos registrados", "—"],
            ["`purgar`", "borra datos anteriores a N días", "`--dias`"],
        ],
        anchos=[3.4, 8.4, 4.8],
        pie="Subcomandos del CLI. Añadir `--json` para salida JSON y `--bd` para otra base.",
    )

    manual.h2("4.2 Por SQL directo")
    manual.parrafo("El archivo `sql\\consultas.sql` contiene **doce consultas comentadas**, "
                   "una por cada necesidad del histórico. Usan parámetros (`:horas`, "
                   "`:limite`, `:device_id`), así que se ejecutan así:")
    manual.codigo("""sqlite3 data\\centinela.db
.param set :horas 6
.param set :limite 50
.param set :device_id dev01
.read sql/consultas.sql""")
    manual.tabla(["Consulta", "Para qué sirve"], SQL_CONSULTAS,
                 anchos=[6.4, 10.2], fuente=7.6, primera_columna_negrita=False)
    manual.parrafo("Las dos que más se usan en la demostración:")
    manual.codigo("""-- 01. Ultima lectura de cada dispositivo
SELECT device_id, ts_utc, temp_c, hum_pct, state, alarm
  FROM v_ultima_lectura ORDER BY device_id;

-- 05. Historial de comandos con latencia
SELECT ts_utc, cmd, source, status, latency_ms, reason
  FROM commands ORDER BY ts_epoch DESC LIMIT :limite;""")

    manual.h2("4.3 Por la API del panel")
    manual.parrafo("Son los mismos datos que consume la interfaz. Requieren sesión, porque "
                   "el panel está protegido; el formulario de acceso espera los campos "
                   "`usuario` y `clave`.")
    manual.tabla(
        ["Ruta", "Devuelve", "Parámetros"],
        [
            ["`/api/estado`", "lectura actual, MQTT, nube, comandos y clientes", "—"],
            ["`/api/lecturas`", "serie de tiempo y agregados por hora",
             "`horas` (0,1–720), `limite` (10–5000)"],
            ["`/api/eventos`", "últimos eventos", "`limite`, `severidad`"],
            ["`/api/comandos`", "historial de comandos", "`limite`"],
            ["`/api/estadisticas`", "agregados del dispositivo", "—"],
            ["`/api/estado-seguridad`", "transiciones de la máquina de estados", "—"],
            ["`/api/stream`", "canal de eventos en vivo (SSE)", "—"],
        ],
        anchos=[4.4, 7.0, 5.2],
        pie="API REST del panel.",
    )
    manual.codigo("""curl -c cookie.txt -X POST -d "usuario=admin&clave=seguridad2026" ^
     http://127.0.0.1:8000/login
curl -b cookie.txt "http://127.0.0.1:8000/api/lecturas?horas=6&limite=50"
""")
    manual.nota("Si prefieres no usar `curl`, abre el panel, pulsa **F12 → Network** y mira "
                "las peticiones: el panel llama exactamente a esas rutas cada 5 segundos.",
                "truco")

    # -------------------------------------------------------------- 5. orden
    manual.h1("5. Orden sugerido para la demostración")

    manual.parrafo("Esta secuencia muestra en ocho pasos que el sistema registra, que audita "
                   "y que sus datos se pueden consultar por tres vías distintas.")
    manual.numerada([
        "Arrancar el backend con `python -m backend.main --seed` y abrir el panel.",
        "Señalar las tres píldoras de la barra y el estado `DESARMADO`.",
        "Pulsar **Armar** y esperar los 10 segundos hasta `ARMADO`.",
        "Abrir la cerradura con `2468` y después fallar el PIN dos veces.",
        "Ir a **Últimos comandos** y mostrar estado, origen y latencia de cada uno.",
        "Cambiar la gráfica a `24 H` y mostrar los eventos críticos.",
        "En otra consola: `python -m backend.cli historico --horas 6` y una consulta del "
        "archivo SQL con `sqlite3`.",
        "Cerrar sesión con **Salir** y comprobar que el panel vuelve al formulario de acceso.",
    ])
    manual.tabla(
        ["Paso", "Qué demuestra", "Tiempo"],
        [
            ["1–2", "el panel está vivo y sin alarmas", "30 s"],
            ["3", "la cuenta regresiva y el cambio de estado", "20 s"],
            ["4", "el control de acceso con PIN y el bloqueo", "40 s"],
            ["5", "la auditoría de comandos con latencia", "30 s"],
            ["6", "el histórico y los eventos", "40 s"],
            ["7", "las consultas por consola y por SQL", "60 s"],
            ["8", "la sesión protegida", "15 s"],
        ],
        anchos=[2.4, 9.8, 4.4],
        alinear_centro=(0, 2),
        pie="Guion de tiempos para una demostración de unos cuatro minutos.",
    )

    # --------------------------------------------------------- 6. problemas
    manual.h1("6. Problemas frecuentes")

    manual.tabla(
        ["Qué ves", "Causa", "Solución"],
        [
            ["`OSError: [WinError 10048]`", "el puerto ya está ocupado por otro proceso",
             "usar `--puerto 8001` o cerrar la otra ventana"],
            ["El panel dice `MQTT OFF`", "no hay salida a Internet o el broker no responde",
             "probar con `python scripts\\demo.py`, que no depende de Internet"],
            ["Las lecturas no cambian", "el nodo no está publicando",
             "revisar el monitor serie del nodo o usar el modo demostración"],
            ["La gráfica está vacía", "no hay datos en ese periodo",
             "arrancar con `--seed` o cambiar a `24 H`"],
            ["`database is locked`", "dos procesos escribiendo la misma base",
             "cerrar el otro proceso; el backend serializa las escrituras, no las comparte"],
            ["El login rechaza las credenciales", "contraseña distinta en `.env`",
             "revisar `WEB_PASSWORD`, o entrar con `--sin-login`"],
            ["404 en `/api/...`", "se pidió sin sesión y el middleware redirige",
             "iniciar sesión primero y reutilizar la cookie"],
        ],
        anchos=[4.4, 5.6, 6.6],
        pie="Problemas al probar el monitoreo.",
    )
    manual.nota("Si algo falla, anota la hora exacta y el mensaje de la consola: con esos dos "
                "datos el problema se localiza en el registro del propio sistema.", "truco")

    # ------------------------------------------------------------- 7. anexo
    manual.h1("7. Anexo · todos los comandos")

    manual.h2("7.1 Arranque")
    manual.codigo("""python -m backend.main --seed                # panel real en :8000
python -m backend.main --sin-mqtt --sin-login    # solo panel, sin broker ni login
python -m backend.main --puerto 8001             # otro puerto
python scripts\\demo.py --reset --sembrar       # demostracion autonoma en :8010
python scripts\\demo.py --escenario intruso      # fuerza una alarma""")

    manual.h2("7.2 Consultas")
    manual.codigo("""python -m backend.cli resumen
python -m backend.cli historico --horas 6 --limite 20
python -m backend.cli eventos --severidad critical
python -m backend.cli comandos
python -m backend.cli estadisticas
python -m backend.cli agregado --horas 24
python -m backend.cli purgar --dias 30""")

    manual.h2("7.3 Base de datos")
    manual.codigo("""sqlite3 data\\centinela.db
.tables                     -- tablas y vistas
.schema readings            -- estructura de una tabla
SELECT COUNT(*) FROM readings;""")

    manual.h2("7.4 Documentos relacionados")
    manual.tabla(
        ["Documento", "Para qué"],
        [
            ["`docs/guia_demo.md`", "guion completo de la demostración"],
            ["`docs/base_datos.md`", "esquema, vistas y consultas explicadas"],
            ["`docs/manuales/Manual_Usuario_Centinela_IoT.docx`", "uso del panel sin tecnicismos"],
            ["`docs/manuales/Manual_Tecnico_Centinela_IoT.docx`", "arquitectura y protocolo"],
            ["`docs/manuales/Documentacion_Extendida_Centinela_IoT.docx`", "código y SQL comentados"],
        ],
        anchos=[8.6, 8.0],
        pie="Dónde ampliar cada tema.",
    )

    manual.parrafo()
    manual.parrafo("— Fin de la guía —", alineacion="centro", cursiva=True, color=GRIS)

    return manual.guardar(SALIDA)


if __name__ == "__main__":
    ruta = construir()
    print("generado:", ruta)
