"""Interfaz local del nodo en el OLED.

QUE MUESTRA
-----------
El estado de seguridad (LISTO / ARMANDO / ARMADO / ALARMA), las lecturas de
los sensores, cuantas alertas hubo, si la cerradura esta cerrada, si la sirena
suena y como anda el WiFi/MQTT. Es la "cara" del nodo cuando no estas mirando
la computadora.

SI NO HAY PANTALLA
------------------
El sistema **no depende** del OLED. Si el modulo no responde (cable suelto,
otra direccion I2C, una placa sin pantalla como la maqueta fisica), el
constructor atrapa el error, deja `disponible = False` y cada refresco
devuelve `False` sin hacer nada. La seguridad sigue funcionando igual.

COMO SE DIBUJA
--------------
La fuente de `framebuf` mide 8x8 pixeles: cada caracter ocupa 8 de ancho y 8
de alto. Sobre 128 pixeles de ancho entran 128 / 8 = **16 caracteres** por
renglon, y sobre 64 de alto entran 8 renglones.
"""

import hal
import ssd1306


def _recortar(texto, ancho_caracteres):
    """Corta el texto si no entra (`texto[:n]` toma los primeros n)."""
    texto = str(texto)
    if len(texto) > ancho_caracteres:
        return texto[:ancho_caracteres]
    return texto


class Pantalla:
    """Vista local del sistema sobre el OLED SSD1306."""

    TITULOS = {
        "DISARMED": "LISTO",
        "ARMING": "ARMANDO",
        "ARMED": "ARMADO",
        "ALARM": "ALARMA",
    }

    def __init__(self, pin_sda, pin_scl, freq_hz, addr, ancho, alto, log=None):
        self._log = log or (lambda mensaje: None)
        self.ancho = ancho
        self.alto = alto
        self.disponible = False
        self._oled = None
        try:
            i2c = hal.I2C(pin_sda, pin_scl, freq_hz)
            self._oled = ssd1306.SSD1306(i2c, addr=addr, width=ancho, height=alto)
            self.disponible = True
            self._log("OLED listo en 0x%02X" % addr)
        except Exception as exc:  # noqa: BLE001
            # Sin pantalla el nodo arranca igual: esto no es un error fatal.
            self._log("OLED no disponible: %s" % exc)

    # El panel mide 64 px y la fuente 8 px de alto. El bisel del modulo tapa
    # las dos primeras filas, por eso el contenido empieza en y=12 y las
    # lineas van cada 8 px (12, 20, 28, 36, 44, 52).
    Y_INICIO = 12
    ALTO_LINEA = 8

    def _linea(self, fila, texto):
        """Escribe un renglon: la fila 1 va en y=12, la 2 en y=20, etc."""
        y = self.Y_INICIO + (fila - 1) * self.ALTO_LINEA
        self._oled.texto(_recortar(texto, self.ancho // 8), 1, y, 1)

    def _linea_inversa(self, texto):
        """Titulo del estado en video inverso, bajo el bisel del modulo.

        Se pinta un rectangulo blanco relleno y despues el texto en negro
        (color 0): eso es el "video inverso" que hace que el estado salte a la
        vista.
        """
        self._oled.rectangulo_relleno(0, 1, self.ancho, 10, 1)
        self._oled.texto(_recortar(texto, self.ancho // 8), 1, 2, 0)

    def mostrar(self, datos):
        """Pinta el estado completo. `datos` es un diccionario plano."""
        if not self.disponible or self._oled is None:
            return False

        estado = datos.get("state", "DISARMED")
        # Si el estado no esta en TITULOS se escribe tal cual (por las dudas).
        titulo = self.TITULOS.get(estado, estado)
        self._oled.limpiar(0)
        self._linea_inversa(titulo)

        temp = datos.get("temp_c")
        hum = datos.get("hum_pct")
        # `%-5s` alinea a la izquierda en 5 caracteres: asi los numeros no
        # "bailan" cuando pasan de 9.9 a 10.0.
        self._linea(1, "T %-5s H %-5s" % (_num(temp), _num(hum)))

        lux = datos.get("lux")
        dist = datos.get("dist_cm")
        self._linea(2, "Luz %-3s Dst %-3s" % (_num(lux, 0), _num(dist, 0)))

        movimiento = "SI" if datos.get("motion") else "no"
        self._linea(3, "Mov %-3s Alerta %s" % (movimiento, datos.get("alerts", 0)))

        cerrada = "cerrada" if datos.get("locked") else "ABIERTA"
        sirena = "SIRENA" if datos.get("siren") else "silencio"
        self._linea(4, "Cerrada %-7s" % cerrada)
        self._linea(5, "Sir. %s" % sirena)

        wifi = datos.get("rssi")
        enlace = "MQTT ok" if datos.get("mqtt") else "MQTT --"
        restante = datos.get("arm_in_s")
        if restante:
            # Durante la cuenta regresiva la ultima linea es la barra.
            # `fraccion` = 0 al empezar y 1 al terminar: se dibuja lo que ya
            # paso, por eso es 1 menos lo que falta sobre el total.
            fraccion = 1.0 - (float(restante) / float(datos.get("exit_delay", 10)))
            self._oled.texto("Salida %2ds" % int(restante), 1, 52, 1)
            self._oled.barra(74, 52, 52, 9, fraccion, 1)
        else:
            self._linea(6, "WiFi %-4s %s" % (_num(wifi, 0), enlace))

        self._oled.mostrar()
        return True

    def aviso(self, texto):
        """Mensaje puntual (por ejemplo, durante el arranque)."""
        if not self.disponible or self._oled is None:
            return False
        self._oled.limpiar(0)
        self._linea(2, "CENTINELA IoT")
        self._linea(4, texto)
        self._oled.mostrar()
        return True

    def limpiar(self):
        """Deja la pantalla en negro."""
        if not self.disponible or self._oled is None:
            return False
        self._oled.limpiar(0)
        self._oled.mostrar()
        return True


def _num(valor, decimales=1):
    """Formatea un numero para el OLED; `--` cuando no hay lectura.

    `("%.1f" % 24.5)` da "24.5"; el `try` existe porque un sensor puede
    devolver algo raro y la pantalla nunca debe romperse por eso.
    """
    if valor is None:
        return "--"
    try:
        if decimales == 0:
            return str(int(round(float(valor))))
        return ("%." + str(decimales) + "f") % float(valor)
    except (TypeError, ValueError):
        return "--"


def construir_desde_config(cfg, log=None):
    return Pantalla(cfg.PIN_I2C_SDA, cfg.PIN_I2C_SCL, cfg.I2C_FREQ_HZ,
                    cfg.OLED_ADDR, cfg.OLED_WIDTH, cfg.OLED_HEIGHT, log=log)
