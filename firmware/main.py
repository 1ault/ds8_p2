"""Punto de entrada del nodo Centinela IoT (ESP32 + MicroPython).

Este es el archivo que Wokwi ejecuta al pulsar "Play": debe llamarse
``main.py``. Solo ARRANCA el sistema; la logica de seguridad vive en
``app.py`` (controlador) y ``fsm.py`` (maquina de estados).

Orden de arranque
-----------------
1. Pantalla OLED: se enciende primero para dar feedback aunque falle la red.
2. WiFi: se intenta conectar con reintentos; sin red el nodo sigue en local.
3. Sensores, actuadores y maquina de estados: se construyen desde ``config``.
4. Controlador: lanza las tareas asincronas (MQTT, muestreo, telemetria,
   LEDs, pantalla, comandos y boton) y espera hasta que lo cancelen.

Convenciones
------------
* Las llamadas usan **argumentos con nombre** (``param=valor``): asi se lee
  que recibe cada funcion sin depender de comentarios por argumento.
* Los tipos van en el docstring de cada funcion (``Args``), porque
  MicroPython no aplica anotaciones de tipo en tiempo de ejecucion.
* Los pines, umbrales y topicos salen de ``config.py``; aqui no hay numeros
  magicos ni credenciales escritas a mano.

Notas de red
------------
* ``WIFI_SSID`` es ``Wokwi-GUEST`` y no lleva contrasena; esa red da salida
  real a Internet, que es lo que permite llegar a ``broker.hivemq.com``.
* El cliente MQTT solo se construye aqui; la conexion la hace el controlador
  dentro de su bucle, para poder reintentar si el broker no responde.
"""

import asyncio

# Modulos propios del nodo (todos en la misma carpeta que este archivo).
import actuators          # LEDs, buzzer y servo-cerradura
import config as cfg      # unica fuente de pines, umbrales y credenciales
import display            # OLED SSD1306
import fsm                # maquina de estados de seguridad
import mqtt_client        # cliente MQTT 3.1.1 propio
import net                # WiFi con reintentos
import sensors            # DHT22, PIR, HC-SR04 y LDR
from app import Controlador


def log(mensaje):
    """Escribe una linea de traza en el monitor serie de Wokwi.

    Args:
        mensaje (str): texto del evento. Se imprime con el prefijo
            ``[centinela]`` para poder filtrar la salida del sistema.

    Returns:
        None

    Example:
        >>> log("WiFi conectado: 10.13.37.2")
        [centinela] WiFi conectado: 10.13.37.2
    """
    print("[centinela] %s" % mensaje)


async def arrancar():
    """Construye el nodo en orden y ejecuta el controlador hasta el apagado.

    No recibe argumentos: toda la configuracion se lee del modulo ``config``,
    de modo que el arranque es identico en Wokwi y en hardware real.

    Args:
        Ninguno.

    Returns:
        None. La corrutina termina cuando ``Controlador.ejecutar`` deja de
        correr (por cancelacion o por un error no controlado).

    Raises:
        asyncio.CancelledError: si se cancela el bucle de eventos (apagado).
        Exception: cualquier fallo al construir un periferico se propaga; el
            bloque ``finally`` apaga los actuadores y cierra el cliente MQTT.
    """
    # Traza de arranque: identidad y version del firmware en el monitor serie.
    log("arranque %s (%s) firmware %s" % (cfg.DEVICE_NAME, cfg.DEVICE_ID,
                                          cfg.FIRMWARE_VERSION))

    # 1) Pantalla local primero: si el WiFi falla, el OLED igual muestra el
    #    estado del nodo y las lecturas.
    pantalla = display.construir_desde_config(cfg=cfg, log=log)
    pantalla.aviso(texto="Iniciando...")

    # 2) WiFi con reintentos. Si no hay red, el nodo sigue en local y el
    #    controlador vuelve a intentar la conexion mas adelante.
    wifi = net.Wifi(
        ssid=cfg.WIFI_SSID,
        password=cfg.WIFI_PASSWORD,
        timeout_s=cfg.WIFI_TIMEOUT_S,
        log=log,
    )
    pantalla.aviso(texto="Conectando WiFi")
    conectado = await wifi.conectar()
    pantalla.aviso(texto="WiFi OK" if conectado else "Sin WiFi")

    # 3) Actuadores, sensores y maquina de estados: cada constructor lee sus
    #    pines y umbrales de config, sin numeros magicos en este archivo.
    panel = actuators.construir_desde_config(cfg=cfg)
    suite = sensors.construir_desde_config(cfg=cfg)
    maquina = fsm.crear_desde_config(cfg=cfg)

    # 4) Cliente MQTT (todavia no conecta: el controlador lo hace en su bucle).
    cliente = mqtt_client.MqttClient(
        host=cfg.MQTT_HOST,
        port=cfg.MQTT_PORT,
        client_id=cfg.MQTT_CLIENT_ID,
        keepalive=cfg.MQTT_KEEPALIVE_S,
        tls=cfg.MQTT_TLS,
        usuario=cfg.MQTT_USER,
        clave=cfg.MQTT_PASSWORD,
        log=log,
    )

    # 5) Controlador: recibe las piezas ya construidas y arranca las tareas.
    controlador = Controlador(
        cfg=cfg,
        wifi=wifi,
        cliente=cliente,
        sensores=suite,   # ojo: el parametro se llama "sensores", no "suite"
        panel=panel,
        pantalla=pantalla,
        maquina=maquina,
        log=log,
    )
    try:
        await controlador.ejecutar()  # -> None; corre hasta que lo cancelen
    finally:
        # Pase lo que pase: cancela tareas, cierra MQTT y apaga actuadores.
        await controlador.detener()   # -> None


def main():
    """Punto de entrada sincrono del programa.

    Crea el bucle de eventos con ``asyncio.run`` y convierte ``Ctrl+C`` en un
    cierre ordenado. Wokwi ejecuta este archivo automaticamente porque se
    llama ``main.py``.

    Args:
        Ninguno.

    Returns:
        None
    """
    try:
        asyncio.run(arrancar())
    except KeyboardInterrupt:
        log("detenido por el usuario")


# ---------------------------------------------------------------------------
# Punto de entrada del programa
# ---------------------------------------------------------------------------
# ``__name__`` es un dunder: un nombre con doble guion bajo a cada lado
# ("double underscore" en ingles). Python lo crea en cada archivo y le asigna:
#   * "__main__" si el archivo se ejecuta directamente
#     (Wokwi al pulsar Play, o ``python main.py`` desde la consola);
#   * el nombre del modulo ("main") si otro archivo hace ``import main``.
#
# La comparacion ``__name__ == "__main__"`` se conoce como el bloque
# "if __name__ == '__main__'" (en la documentacion, "top-level code
# environment"). No es una funcion ni una palabra reservada: es un idiom.
# Sirve para que el nodo arranque solo cuando este archivo es el programa
# principal, y no cuando se importa desde las pruebas o el REPL.
if __name__ == "__main__":
    main()
