"""Interfaz local del nodo en el OLED.

Muestra el estado de seguridad, las lecturas y la salud de la conexion. Si la
pantalla no responde (o no esta conectada), el sistema sigue funcionando: la
pantalla se marca como no disponible y cada refresco se ignora.
"""

import hal
import ssd1306


def _recortar(texto, ancho_caracteres):
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
            self._log("OLED no disponible: %s" % exc)

    # El panel mide 64 px y la fuente 8 px de alto. El bisel del modulo tapa
    # las dos primeras filas, por eso el contenido empieza en y=12 y las
    # lineas van cada 8 px (12, 20, 28, 36, 44, 52).
    Y_INICIO = 12
    ALTO_LINEA = 8

    def _linea(self, fila, texto):
        y = self.Y_INICIO + (fila - 1) * self.ALTO_LINEA
        self._oled.texto(_recortar(texto, self.ancho // 8), 1, y, 1)

    def _linea_inversa(self, texto):
        """Titulo del estado en video inverso, bajo el bisel del modulo."""
        self._oled.rectangulo_relleno(0, 1, self.ancho, 10, 1)
        self._oled.texto(_recortar(texto, self.ancho // 8), 1, 2, 0)

    def mostrar(self, datos):
        """Pinta el estado completo. `datos` es un diccionario plano."""
        if not self.disponible or self._oled is None:
            return False

        estado = datos.get("state", "DISARMED")
        titulo = self.TITULOS.get(estado, estado)
        self._oled.limpiar(0)
        self._linea_inversa(titulo)

        temp = datos.get("temp_c")
        hum = datos.get("hum_pct")
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
            # durante la cuenta regresiva la ultima linea es la barra
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
        if not self.disponible or self._oled is None:
            return False
        self._oled.limpiar(0)
        self._oled.mostrar()
        return True


def _num(valor, decimales=1):
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
