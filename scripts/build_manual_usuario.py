"""Genera el Manual del Usuario del sistema Centinela IoT (DOCX).

Uso:
    python scripts/build_manual_usuario.py
Salida:
    docs/manuales/Manual_Usuario_Centinela_IoT.docx
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
for ruta in (str(RAIZ), str(RAIZ / "scripts")):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

from _manual_estilo import GRIS, Manual  # noqa: E402

IMG = RAIZ / "docs" / "img"
CAP = RAIZ / "docs" / "capturas"
SALIDA = RAIZ / "docs" / "manuales" / "Manual_Usuario_Centinela_IoT.docx"

VERSION = "2.0.0"
RECORTES = RAIZ / ".tmp" / "manual-img"

# Zonas del panel (pantalla de 1680x1050) que conviene mostrar ampliadas
ZONAS = {
    "panel_estado.png": (18, 68, 486, 650),
    "panel_sensores.png": (18, 295, 486, 650),
    "panel_grafica.png": (486, 68, 1186, 455),
    "panel_eventos.png": (486, 452, 1186, 900),
    "panel_controles.png": (1184, 68, 1666, 362),
    "panel_comandos.png": (1184, 362, 1666, 700),
}


def preparar_recortes() -> Path:
    """Recorta zonas del panel para que se lean a tamaño de impresión."""
    from PIL import Image

    RECORTES.mkdir(parents=True, exist_ok=True)
    with Image.open(CAP / "02_panel_alarma.png") as origen:
        for nombre, caja in ZONAS.items():
            destino = RECORTES / nombre
            origen.crop(caja).save(destino)
    return RECORTES


def construir() -> Path:
    recortes = preparar_recortes()
    manual = Manual(
        titulo="Manual del usuario",
        subtitulo="Cómo usar el panel, interpretar las alertas y operar el sistema "
                  "de seguridad sin conocimientos técnicos",
        version=VERSION,
        autor="Estudiante de Desarrollo de Software VIII",
        materia="Parcial #2 · Desarrollo de Software VIII",
        encabezado="Centinela IoT · Manual del usuario",
    )

    manual.portada(
        imagen=CAP / "01_panel_estado.png",
        ancho_imagen_cm=15.4,
        resumen="Guía práctica para el operador del sistema: cómo entrar al panel, armar y "
                "desarmar la vigilancia, qué significan las luces y la sirena, y qué hacer "
                "cuando aparece una alerta.",
    )

    # ------------------------------------------------------------------ indice
    manual.h1("Contenido", nueva_pagina=False)
    manual.parrafo("Esta guía está pensada para usarse mientras se opera el sistema. Si "
                   "busca detalles de instalación o de programación, consulte el manual "
                   "técnico.")
    manual.tabla(
        ["Sección", "Para qué sirve"],
        [
            ["1. Qué es Centinela IoT", "entender qué vigila el sistema y qué avisa"],
            ["2. Antes de empezar", "qué necesita y cómo entrar"],
            ["3. Acceso al panel", "iniciar sesión y salir de forma segura"],
            ["4. La pantalla principal", "reconocer cada zona del panel"],
            ["5. Los cuatro estados", "saber en qué situación está la vigilancia"],
            ["6. Operaciones básicas", "armar, desarmar, silenciar y abrir la cerradura"],
            ["7. Indicadores del equipo", "luces, pantalla y sirena del nodo"],
            ["8. Histórico y eventos", "consultar qué pasó y cuándo"],
            ["9. El pulsador del equipo", "armar sin usar el panel"],
            ["10. Modo demostración", "probar el sistema con datos de ejemplo"],
            ["11. El simulador Wokwi", "ver el equipo funcionando en el navegador"],
            ["12. Los datos en la nube", "consultar ThingSpeak desde el móvil"],
            ["13. Preguntas frecuentes", "dudas habituales resueltas"],
            ["14. Solución de problemas", "qué hacer si algo no responde"],
            ["15. Buenas prácticas", "recomendaciones de uso y seguridad"],
            ["16. Glosario", "palabras técnicas explicadas en simple"],
        ],
        anchos=[4.8, 11.8],
        pie="Guía rápida de las secciones del manual.",
    )

    manual.nota("Las figuras de este manual son capturas reales del sistema en "
                "funcionamiento. Los datos que aparecen (temperaturas, alertas, comandos) "
                "son de una demostración y cambian en cada uso.", "nota")

    # ------------------------------------------------------------ 1. que es
    manual.h1("1. Qué es Centinela IoT")

    manual.parrafo("**Centinela IoT** es un sistema de seguridad para una puerta de acceso. "
                   "Un pequeño equipo colocado en la puerta mide temperatura, humedad, luz, "
                   "movimiento y distancia, y decide por sí mismo si debe sonar una alarma. "
                   "Todo lo que ocurre se guarda y se puede ver en una página web llamada "
                   "**panel**, desde el computador o el móvil.")
    manual.parrafo("El sistema hace tres cosas:")
    manual.vinetas([
        "**Vigila**: mientras está armado, si detecta movimiento o una presencia muy cerca, "
        "se activa la alarma.",
        "**Avisa**: enciende la sirena y el LED rojo, muestra el estado en la pantalla del "
        "equipo y registra el evento con la hora exacta.",
        "**Registra**: guarda cada lectura y cada comando, de modo que usted puede consultar "
        "después qué pasó, cuándo y quién lo hizo.",
    ])
    manual.figura(CAP / "01_panel_estado.png",
                  "Aspecto del panel cuando el sistema funciona con normalidad.",
                  ancho_cm=15.6)

    manual.h2("1.1 Qué puede hacer desde el panel")
    manual.tabla(
        ["Acción", "Para qué sirve"],
        [
            ["Ver el estado", "saber si la vigilancia está desarmada, armándose, armada o en alarma"],
            ["Ver las mediciones", "temperatura, humedad, luz, distancia, movimiento y señal WiFi"],
            ["Armar y desarmar", "activar o desactivar la vigilancia a distancia"],
            ["Silenciar la sirena", "callar la alarma sin desactivar la vigilancia"],
            ["Abrir la cerradura", "liberar el pestillo con un PIN durante unos segundos"],
            ["Consultar el histórico", "revisar las últimas horas en una gráfica"],
            ["Leer los eventos", "ver alarmas, cambios de estado y avisos en orden"],
        ],
        anchos=[4.6, 12.0],
        pie="Acciones disponibles para el operador.",
    )

    # ------------------------------------------------------ 2. antes de empezar
    manual.h1("2. Antes de empezar")

    manual.h2("2.1 Qué necesita")
    manual.tabla(
        ["Elemento", "Detalle"],
        [
            ["Un equipo encendido", "el nodo de la puerta, alimentado y con luz verde o parpadeando"],
            ["Conexión a la red", "el mismo WiFi o red local donde está instalado el sistema"],
            ["Un navegador", "Chrome, Edge o Firefox en versión reciente"],
            ["Usuario y contraseña", "los entrega el instalador; por defecto `admin` / `seguridad2026`"],
            ["El PIN de la cerradura", "cuatro dígitos; por defecto `2468`"],
        ],
        anchos=[4.6, 12.0],
        pie="Requisitos para usar el sistema.",
    )
    manual.nota("Cambie la contraseña y el PIN antes de usar el sistema en una vivienda real. "
                "El manual técnico explica cómo hacerlo (apartados 9 y 10.2).", "aviso")

    manual.h2("2.2 Cómo entrar al panel")
    manual.numerada([
        "Abra el navegador en el computador o en el móvil.",
        "Escriba la dirección que le indicó el instalador. En una instalación local es "
        "`http://127.0.0.1:8000`.",
        "Introduzca su usuario y contraseña.",
        "Pulse **Entrar**. El panel se abre en el estado actual del sistema.",
    ])

    # --------------------------------------------------------- 3. acceso
    manual.h1("3. Acceso al panel")

    manual.h2("3.1 Iniciar sesión")
    manual.parrafo("La pantalla de acceso pide dos datos: usuario y contraseña. Si son "
                   "correctos, el sistema crea una sesión que dura ocho horas; pasado ese "
                   "tiempo deberá volver a entrar.")
    manual.figura(CAP / "03_login.png",
                  "Pantalla de acceso al panel.", ancho_cm=12.2)
    manual.tabla(
        ["Situación", "Qué ocurre", "Qué hacer"],
        [
            ["Credenciales correctas", "entra al panel", "—"],
            ["Contraseña incorrecta", "mensaje «Credenciales incorrectas»", "revisar mayúsculas y volver a escribir"],
            ["Sesión caducada", "el panel pide entrar de nuevo", "volver a iniciar sesión"],
            ["Olvidó la contraseña", "no hay recuperación automática", "pedir al instalador que la restablezca en `.env`"],
        ],
        anchos=[4.2, 6.0, 6.4],
        pie="Situaciones al iniciar sesión.",
    )

    manual.h2("3.2 Salir de forma segura")
    manual.parrafo("Pulse el botón **Salir** en la esquina superior derecha. La sesión se "
                   "cierra en el servidor y la cookie se elimina del navegador. Hágalo "
                   "siempre que use un equipo compartido.")

    manual.nota("No cierre solo la pestaña: la sesión seguiría activa hasta ocho horas. Use "
                "siempre **Salir** si el equipo no es suyo.", "aviso")

    # -------------------------------------------------- 4. pantalla principal
    manual.h1("4. La pantalla principal")

    manual.parrafo("El panel se divide en tres columnas. La de la izquierda resume el estado "
                   "y las mediciones; la del centro muestra la gráfica y los eventos; la de "
                   "la derecha contiene los controles y el historial de comandos.")
    manual.figura(CAP / "02_panel_alarma.png",
                  "Panel durante una alarma: estado en rojo, sirena activa y eventos críticos.",
                  ancho_cm=16.0)

    manual.h2("4.1 Zonas del panel")
    manual.tabla(
        ["Zona", "Qué muestra"],
        [
            ["Barra superior", "nombre del equipo, estado del broker, de la nube, del canal en "
                               "vivo, la hora y el botón Salir"],
            ["Estado de seguridad", "el estado actual, si la cerradura está cerrada, si la "
                                    "sirena suena y cuántas alertas hay"],
            ["Sensores", "temperatura, humedad, luz, distancia, movimiento y señal WiFi"],
            ["Estado del sistema", "broker conectado, nube activa, comandos pendientes, "
                                   "clientes conectados y versión"],
            ["Histórico de sensores", "gráfica de las últimas 1, 6 o 24 horas"],
            ["Eventos del sistema", "lista de lo ocurrido, con hora y gravedad"],
            ["Control remoto", "botones Armar, Desarmar, Silenciar y Abrir cerradura"],
            ["Últimos comandos", "qué se envió, desde dónde, si se ejecutó y cuánto tardó"],
            ["Resumen 24 h", "lecturas, temperatura media, alarmas y tiempo de respuesta"],
        ],
        anchos=[4.2, 12.4],
        pie="Zonas del panel y su contenido.",
    )
    manual.figura(recortes / "panel_estado.png",
                  "Zona de estado: estado de seguridad, cerradura, sirena y alertas.",
                  ancho_cm=8.6)

    manual.h2("4.2 Cómo leer la barra superior")
    manual.tabla(
        ["Indicador", "Significado"],
        [
            ["**MQTT OK**", "el equipo y el panel se están comunicando"],
            ["**MQTT OFF**", "no hay comunicación con el equipo: las órdenes no llegarán"],
            ["**Nube OFF**", "ThingSpeak no está configurado o no responde; el resto funciona igual"],
            ["**En vivo ON**", "el panel recibe los cambios al instante"],
            ["Hora", "hora del servidor, útil para comparar con los eventos"],
        ],
        anchos=[3.6, 13.0],
        pie="Significado de los indicadores superiores.",
    )

    # --------------------------------------------------------- 5. los estados
    manual.h1("5. Los cuatro estados")

    manual.parrafo("El sistema siempre está en uno de estos cuatro estados. El nombre "
                   "aparece en grande en la tarjeta **Estado de seguridad** y también en la "
                   "pantalla del equipo.")
    manual.figura(CAP / "wokwi_03_oled_armado.png",
                  "Pantalla del equipo en estado ARMADO (verde, sin alarma).",
                  ancho_cm=9.4)
    manual.tabla(
        ["Estado", "Qué significa", "Qué debe hacer"],
        [
            ["**DESARMADO**", "la vigilancia está desactivada; se puede abrir la cerradura con PIN",
             "nada, si no necesita vigilancia"],
            ["**ARMANDO**", "cuenta regresiva de 10 segundos antes de activar la vigilancia",
             "salir del área vigilada o cerrar la puerta"],
            ["**ARMADO**", "la vigilancia está activa; cualquier presencia dispara la alarma",
             "ninguna acción; el LED verde queda fijo"],
            ["**ALARMA**", "se detectó una intrusión; suenan la sirena y el LED rojo",
             "verificar qué ocurrió y decidir si desarma o silencia"],
        ],
        anchos=[3.0, 8.2, 5.4],
        pie="Los cuatro estados del sistema.",
    )
    manual.nota("En estado ARMADO, cualquier movimiento frente al sensor o una presencia a "
                "menos de 80 cm dispara la alarma. Avise a las personas que conviven en la "
                "vivienda antes de armar.", "aviso")

    manual.h2("5.1 Cuánto dura cada cosa")
    manual.tabla(
        ["Situación", "Duración"],
        [
            ["Cuenta regresiva al armar", "10 segundos"],
            ["Sirena encendida sin que nadie intervenga", "2 minutos"],
            ["Cerradura abierta antes de cerrarse sola", "8 segundos"],
            ["Bloqueo tras tres PIN incorrectos", "30 segundos"],
            ["Separación mínima entre dos alertas", "5 segundos"],
        ],
        anchos=[10.0, 6.6],
        pie="Tiempos predeterminados del sistema.",
    )

    # ------------------------------------------------------ 6. operaciones
    manual.h1("6. Operaciones básicas")

    manual.h2("6.1 Armar la vigilancia")
    manual.parrafo("Armar significa activar la vigilancia. Al hacerlo, el sistema cierra la "
                   "cerradura y empieza una cuenta regresiva para que usted salga del área.")
    manual.figura(recortes / "panel_controles.png",
                  "Botones de control remoto del panel.", ancho_cm=12.0)
    manual.numerada([
        "Compruebe que el estado sea **DESARMADO**.",
        "Pulse **Armar**. El estado cambia a **ARMANDO** y el LED verde parpadea.",
        "Salga del área vigilada y cierre la puerta.",
        "Espere 10 segundos: el estado pasa a **ARMADO** y el LED verde queda fijo.",
    ])
    manual.nota("Si necesita cancelar el armado, pulse **Desarmar** durante la cuenta "
                "regresiva. Se cancela de inmediato.", "truco")

    manual.h2("6.2 Desarmar")
    manual.parrafo("Pulse **Desarmar**. El estado vuelve a **DESARMADO**, la sirena se apaga "
                   "si estaba sonando y la cerradura queda cerrada pero disponible para "
                   "abrirse con el PIN. Desarmar también sirve para cancelar una alarma.")

    manual.h2("6.3 Silenciar la sirena")
    manual.parrafo("Si la alarma se disparó y ya sabe que no es una intrusión, pulse "
                   "**Silenciar**. La sirena se calla, pero la vigilancia sigue activa y el "
                   "evento queda registrado como alerta. Para dejar de vigilar, use "
                   "**Desarmar**.")
    manual.tabla(
        ["Botón", "Qué hace", "Cuándo usarlo"],
        [
            ["**Armar**", "activa la vigilancia tras 10 segundos", "al salir de casa"],
            ["**Desarmar**", "desactiva la vigilancia y apaga la sirena", "al llegar o al cancelar una falsa alarma"],
            ["**Silenciar**", "calla la sirena sin desactivar la vigilancia", "cuando ya verificó que no hay peligro"],
            ["**Abrir cerradura**", "libera el pestillo 8 segundos previo PIN", "para entrar o dejar entrar a alguien"],
        ],
        anchos=[3.4, 6.6, 6.6],
        pie="Resumen de los botones de control.",
    )

    manual.h2("6.4 Abrir la cerradura con PIN")
    manual.parrafo("La cerradura solo se abre si el sistema está **DESARMADO** y si se "
                   "introduce el PIN correcto.")
    manual.numerada([
        "Pulse **Abrir cerradura**.",
        "Escriba el PIN de cuatro dígitos en la ventana que aparece.",
        "Pulse **Abrir**. La tarjeta muestra la cerradura como «ABIERTA».",
        "La cerradura se cierra sola a los 8 segundos.",
    ])
    manual.figura(CAP / "wokwi_04_oled_alarma.png",
                  "Pantalla del equipo en estado ALARMA: sirena activa y una alerta registrada.",
                  ancho_cm=9.4)

    manual.h2("6.5 Qué pasa si el PIN es incorrecto")
    manual.tabla(
        ["Intento", "Resultado"],
        [
            ["Primer PIN erróneo", "aviso «PIN incorrecto»; no se abre"],
            ["Segundo PIN erróneo", "aviso de nuevo; no se abre"],
            ["Tercer PIN erróneo", "la cerradura se bloquea 30 segundos"],
            ["Intento durante el bloqueo", "aviso «bloqueado»; se rechaza aunque el PIN sea correcto"],
            ["Intentar abrir estando armado", "aviso «desarma antes de abrir»; no se abre"],
        ],
        anchos=[5.4, 11.2],
        pie="Comportamiento ante PIN incorrecto.",
    )
    manual.parrafo("Cada comando, incluidos los rechazados, queda en la tabla **Últimos "
                   "comandos** con su motivo. Así se puede saber si alguien intentó abrir "
                   "sin permiso.")

    # --------------------------------------------------- 7. indicadores
    manual.h1("7. Indicadores del equipo")

    manual.parrafo("El equipo de la puerta tiene tres formas de comunicarse sin necesidad "
                   "del panel: dos luces, una pantalla pequeña y la sirena.")

    manual.h2("7.1 Las luces")
    manual.tabla(
        ["Luz", "Comportamiento", "Significado"],
        [
            ["Verde", "encendida fija", "vigilancia armada, todo normal"],
            ["Verde", "parpadeando", "cuenta regresiva de armado en curso"],
            ["Verde", "encendida en desarmado", "equipo alimentado y funcionando"],
            ["Roja", "parpadeando", "alarma activa"],
            ["Roja", "apagada", "sin alarma"],
        ],
        anchos=[2.6, 4.6, 9.4],
        pie="Significado de las luces del equipo.",
    )

    manual.h2("7.2 La pantalla")
    manual.parrafo("La pantalla muestra siempre la misma estructura: el estado en la primera "
                   "línea, las mediciones, el estado de la cerradura y de la sirena, y la "
                   "conexión. Cuando falta un dato aparece `--`.")
    manual.tabla(
        ["Línea", "Qué muestra"],
        [
            ["Estado", "ARMADO, ARMANDO, LISTO (desarmado) o ALARMA"],
            ["T y H", "temperatura en °C y humedad en %"],
            ["Luz y Dst", "luminosidad en lux y distancia en cm"],
            ["Mov y Alerta", "si hay movimiento y cuántas alertas se acumularon"],
            ["Cerrada", "cerrada o ABIERTA"],
            ["Sir.", "SIRENA o silencio"],
            ["WiFi", "intensidad de la señal y si hay conexión con el servidor"],
        ],
        anchos=[3.6, 13.0],
        pie="Líneas de la pantalla del equipo.",
    )
    manual.figura(CAP / "wokwi_02_serie.png",
                  "Mensajes de arranque del equipo: pantalla lista, WiFi y conexión al servidor.",
                  ancho_cm=15.2)

    manual.h2("7.3 La sirena")
    manual.parrafo("La sirena emite un tono que alterna entre dos frecuencias. Se activa "
                   "solo en estado de alarma y se detiene al desarmar, al silenciar o "
                   "automáticamente a los dos minutos.")

    # ------------------------------------------------- 8. historico y eventos
    manual.h1("8. Histórico y eventos")

    manual.h2("8.1 La gráfica")
    manual.parrafo("El bloque **Histórico de sensores** dibuja la temperatura y la humedad a "
                   "lo largo del tiempo. Los botones **1 h**, **6 h** y **24 h** cambian el "
                   "periodo. La línea roja es la temperatura y la azul la humedad; debajo se "
                   "indica cuántas muestras se están mostrando.")
    manual.parrafo("Si la gráfica está vacía, todavía no hay lecturas suficientes o el "
                   "equipo no está enviando datos.")
    manual.figura(recortes / "panel_grafica.png",
                  "Bloque del histórico con el selector de periodo y la leyenda.",
                  ancho_cm=13.0)

    manual.h2("8.2 Los eventos")
    manual.parrafo("Cada fila de **Eventos del sistema** indica la hora, el mensaje y su "
                   "gravedad. Los eventos críticos aparecen con fondo rojizo y los avisos en "
                   "ámbar, para que se distingan de un simple cambio de estado.")
    manual.figura(CAP / "05_cli_eventos.png",
                  "Consulta de eventos desde la consola del sistema.", ancho_cm=15.2)
    manual.figura(recortes / "panel_eventos.png",
                  "Feed de eventos en el panel, con la hora y la gravedad de cada uno.",
                  ancho_cm=13.0)
    manual.tabla(
        ["Gravedad", "Qué representa", "Ejemplo"],
        [
            ["Informativo", "algo normal ocurrió", "cambio de estado a ARMADO"],
            ["Aviso", "algo requiere atención", "sirena silenciada, conexión perdida"],
            ["Crítico", "requiere revisión inmediata", "presencia detectada, sirena activada"],
        ],
        anchos=[3.0, 6.6, 7.0],
        pie="Gravedad de los eventos.",
    )

    manual.h2("8.3 Los comandos")
    manual.parrafo("La tabla **Últimos comandos** es la auditoría del sistema: qué se envió, "
                   "desde dónde (panel, ThingsSpeak o botón del equipo), si se ejecutó y "
                   "cuántos milisegundos tardó en confirmarse.")
    manual.tabla(
        ["Estado", "Significado"],
        [
            ["OK", "el equipo confirmó la ejecución"],
            ["RECHAZADO", "el equipo lo rechazó por una regla (por ejemplo, PIN incorrecto)"],
            ["TIMEOUT", "el equipo no respondió en 8 segundos"],
            ["PENDIENTE", "se envió y se está esperando la respuesta"],
        ],
        anchos=[3.4, 13.2],
        pie="Estados posibles de un comando.",
    )
    manual.figura(recortes / "panel_comandos.png",
                  "Tabla de últimos comandos: origen, estado y tiempo de respuesta.",
                  ancho_cm=12.0)
    manual.figura(CAP / "07_cli_comandos.png",
                  "El mismo historial de comandos consultado desde la consola.",
                  ancho_cm=15.2)

    # ------------------------------------------------------- 9. el pulsador
    manual.h1("9. El pulsador del equipo")

    manual.parrafo("El equipo tiene un pulsador verde con la etiqueta **ARMAR / DESARMAR**. "
                   "Sirve para operar el sistema sin usar el panel, por ejemplo al entrar o "
                   "salir de casa.")
    manual.vinetas([
        "Un toque corto arma el sistema si estaba desarmado; la cuenta regresiva empieza igual "
        "que desde el panel.",
        "Un toque corto desarma si estaba armado o en alarma.",
        "Mantenerlo pulsado no cambia el comportamiento: el sistema responde al primer toque.",
    ])
    manual.figura(CAP / "wokwi_05_circuito_alarma.png",
                  "Equipo en alarma: el LED rojo parpadea y la sirena está activa.",
                  ancho_cm=11.0)

    # -------------------------------------------------- 10. modo demostracion
    manual.h1("10. Modo demostración")

    manual.parrafo("Si el equipo no está disponible, el sistema incluye un modo de "
                   "demostración que crea un equipo simulado y datos de ejemplo. Es útil para "
                   "aprender a usar el panel o para una presentación.")
    manual.numerada([
        "En el computador, abra la carpeta del proyecto.",
        "Ejecute el comando de demostración que le indique el instalador.",
        "Abra en el navegador la dirección que aparece en la ventana: normalmente "
        "`http://127.0.0.1:8010`.",
        "El panel se abre sin pedir contraseña y empieza a recibir datos del equipo simulado.",
    ])
    manual.nota("En modo demostración no hay contraseña y los datos son inventados. No lo "
                "use para vigilar una vivienda real.", "aviso")
    manual.figura(CAP / "04_cli_historico.png",
                  "Consulta del histórico de las últimas horas desde la consola.",
                  ancho_cm=15.2)

    # ------------------------------------------------------------ 11. wokwi
    manual.h1("11. El simulador Wokwi")

    manual.parrafo("El equipo también puede verse funcionando en un simulador gratuito en "
                   "Internet, sin necesidad de tener el hardware. Es la forma más rápida de "
                   "comprobar que todo funciona antes de instalar el equipo real.")
    manual.numerada([
        "Entre a <https://wokwi.com> y abra el proyecto que le compartieron.",
        "Pulse el botón verde de **Play**.",
        "Observe el monitor serie: aparecen los mensajes «pantalla lista», «WiFi conectado» y "
        "«conexión al servidor».",
        "Accione el pulsador del circuito para armar y espere la cuenta regresiva.",
        "Para provocar la alarma, haga clic en el sensor de movimiento y elija "
        "**Simulate motion**.",
    ])
    manual.figura(CAP / "wokwi_01_circuito.png",
                  "Equipo completo en el simulador: placa, sensores, luces, sirena, cerradura y pantalla.",
                  ancho_cm=11.6)

    # ------------------------------------------------------------ 12. la nube
    manual.h1("12. Los datos en la nube")

    manual.parrafo("Si el instalador configuró ThingSpeak, las mismas mediciones se ven "
                   "también en Internet, con gráficas de las últimas horas y acceso desde el "
                   "móvil. El panel y la nube son independientes: si la nube se cae, la "
                   "vigilancia sigue funcionando.")
    manual.tabla(
        ["En el panel", "En ThingSpeak"],
        [
            ["Temperatura y humedad", "campos 1 y 2"],
            ["Luz y distancia", "campos 3 y 4"],
            ["Movimiento y alarma", "campos 5 y 6"],
            ["Estado del sistema", "campo 7 (0 = desarmado, 3 = alarma)"],
            ["Alertas acumuladas", "campo 8"],
        ],
        anchos=[7.0, 9.6],
        pie="Correspondencia entre el panel y el canal de ThingSpeak.",
    )
    manual.parrafo("ThingSpeak también permite enviar comandos a distancia mediante su "
                   "aplicación **TalkBack**: si alguien escribe `arm` en la cola, el sistema "
                   "arma la vigilancia como si se hubiera pulsado el botón.")

    # ------------------------------------------------------------ 13. faq
    manual.h1("13. Preguntas frecuentes")

    manual.h2("¿Puedo usar el sistema sin Internet?")
    manual.parrafo("Sí, para vigilar y operar en la red local. Sin Internet no se actualiza "
                   "la nube y, si el equipo está lejos del panel, no habrá comunicación "
                   "entre ambos.")

    manual.h2("¿Qué pasa si se va la luz?")
    manual.parrafo("El equipo se reinicia cuando vuelve la corriente y arranca **desarmado**, "
                   "como medida de seguridad para que no quede una alarma sonando sin "
                   "supervisión. Deberá armar de nuevo.")

    manual.h2("¿Se puede abrir la cerradura estando armado?")
    manual.parrafo("No. Primero debe desarmar. Es una protección para que nadie abra la "
                   "puerta mientras la vigilancia está activa, ni siquiera con el PIN.")

    manual.h2("¿Cuántas veces puedo equivocarme con el PIN?")
    manual.parrafo("Tres veces. Después la cerradura se bloquea 30 segundos y el intento "
                   "queda registrado en el historial de comandos.")

    manual.h2("¿La sirena se apaga sola?")
    manual.parrafo("Sí, a los dos minutos. Si desea callarla antes sin desactivar la "
                   "vigilancia, use **Silenciar**.")

    manual.h2("¿Quién puede ver el panel?")
    manual.parrafo("Solo quien tenga usuario y contraseña. La sesión dura ocho horas y se "
                   "cierra con el botón **Salir**.")

    manual.h2("¿Se guardan las imágenes de la cámara?")
    manual.parrafo("El sistema no tiene cámara. Guarda mediciones, eventos y comandos con su "
                   "hora exacta.")

    # ------------------------------------------------------ 14. problemas
    manual.h1("14. Solución de problemas")

    manual.parrafo("Antes de llamar al instalador, revise esta tabla: la mayoría de los "
                   "problemas tienen una causa sencilla.")
    manual.tabla(
        ["Qué ve", "Causa probable", "Qué hacer"],
        [
            ["El panel dice **MQTT OFF**", "el equipo está apagado o sin red",
             "revisar la alimentación y el LED verde del equipo"],
            ["Las mediciones no cambian", "el equipo no está enviando datos",
             "recargar el panel; si sigue igual, revisar el equipo"],
            ["**Desarmar** no responde", "no hay comunicación con el equipo",
             "esperar unos segundos y reintentar; revisar la conexión"],
            ["«PIN incorrecto» con el PIN correcto", "se agotaron los intentos", "esperar 30 segundos y reintentar"],
            ["«Desarma antes de abrir»", "el sistema está armado", "pulsar **Desarmar** y luego abrir"],
            ["La gráfica está vacía", "no hay lecturas en ese periodo",
             "probar con **24 h** o esperar nuevas lecturas"],
            ["No puedo entrar al panel", "contraseña incorrecta o sesión caducada",
             "volver a escribir la contraseña; si persiste, pedir restablecerla"],
            ["La alarma no suena", "el sistema está desarmado o silenciado",
             "armar el sistema y comprobar que la sirena no esté silenciada"],
        ],
        anchos=[4.6, 5.4, 6.6],
        pie="Problemas frecuentes para el operador.",
    )
    manual.nota("Si el problema persiste, anote la hora exacta y el mensaje que aparece: con "
                "esos dos datos el instalador puede encontrar la causa en el registro del "
                "sistema.", "truco")

    # ------------------------------------------------------- 15. buenas practicas
    manual.h1("15. Buenas prácticas")

    manual.vinetas([
        "**Cambie las credenciales iniciales**: la contraseña del panel y el PIN de la "
        "cerradura vienen con valores de fábrica.",
        "**No comparta el PIN** por mensajes ni lo escriba en un papel pegado a la puerta.",
        "**Use Salir** al terminar, sobre todo en equipos compartidos.",
        "**Avise antes de armar** a las personas que viven o trabajan en el lugar.",
        "**Revise los eventos críticos** al final del día; allí quedan las alertas reales.",
        "**Pruebe el sistema** una vez al mes: arme, provoque una detección y desarme.",
        "**Verifique la señal WiFi**: si aparece baja, la comunicación puede fallar.",
        "**Cierre la sesión** antes de desconectar el equipo que usa como panel.",
    ])
    manual.nota("Una alarma que nadie revisa pierde su función. El sistema avisa, pero la "
                "decisión de actuar siempre es humana.", "nota")

    # ------------------------------------------------------------ 16. glosario
    manual.h1("16. Glosario")

    manual.tabla(
        ["Palabra", "Qué significa en este sistema"],
        [
            ["Alarma", "estado en el que se detectó una intrusión y suena la sirena"],
            ["Armar", "activar la vigilancia"],
            ["Broker", "servicio que reparte los mensajes entre el equipo y el panel"],
            ["Comando", "orden enviada al equipo (armar, desarmar, silenciar, abrir)"],
            ["Evento", "algo que ocurrió y quedó registrado con su hora"],
            ["Histórico", "conjunto de lecturas guardadas que se pueden consultar"],
            ["Nodo", "el equipo físico colocado en la puerta"],
            ["Panel", "la página web desde la que se opera el sistema"],
            ["PIN", "contraseña numérica que abre la cerradura"],
            ["Sensor", "dispositivo que mide algo (temperatura, movimiento, distancia, luz)"],
            ["Sirena", "dispositivo que emite el sonido de alarma"],
            ["SSE", "tecnología que permite que el panel se actualice solo, sin recargar"],
            ["Testigo / LED", "luz pequeña que indica el estado del equipo"],
            ["Umbral", "valor a partir del cual el sistema considera que algo es anómalo"],
        ],
        anchos=[3.4, 13.2],
        pie="Glosario para el usuario.",
    )

    manual.parrafo()
    manual.parrafo("— Fin del manual del usuario —", alineacion="centro",
                   cursiva=True, color=GRIS)

    return manual.guardar(SALIDA)


if __name__ == "__main__":
    ruta = construir()
    print("generado:", ruta)
