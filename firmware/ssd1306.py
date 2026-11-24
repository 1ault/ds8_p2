# Driver minimo del OLED SSD1306 (I2C 128x64) sobre `framebuf`.
#
# QUE ES
# ------
# El SSD1306 es un controlador de pantallas OLED monocromas. Se conecta por
# **I2C**: dos cables (SDA datos, SCL reloj) y una direccion (aca `0x3C`).
# La pantalla es de 128x64 pixeles, pero **no** se le manda pixel por pixel:
# se le manda una copia entera de la imagen (el *framebuffer*) y ella la pinta.
#
# EL FRAMEBUFFER Y "MONO_VLSB"
# ----------------------------
# Son 128 columnas x 64 filas de 1 bit = 1024 bytes. Se organiza en **8 paginas
# horizontales de 8 filas**: cada byte representa 8 pixeles *verticales* de una
# columna, y el bit menos significativo es el de arriba (por eso el formato se
# llama VLSB: "vertical, least significant bit first").
#
#     byte de la columna x en la pagina p:
#         bit 0 -> pixel (x, p*8 + 0)
#         bit 1 -> pixel (x, p*8 + 1)
#         ...
#         bit 7 -> pixel (x, p*8 + 7)
#
# Por eso el buffer mide `pages * width` = 8 * 128 = 1024 bytes, y `framebuf`
# hace la conversion desde coordenadas (x, y) a ese formato.
#
# I2C: COMANDOS Y DATOS
# ---------------------
# Cada escritura I2C empieza con un **byte de control**:
#
#     0x00  lo que sigue son COMANDOS (configuracion de la pantalla)
#     0x40  lo que sigue son DATOS (bytes del framebuffer)
#
# Por eso `_comando()` arma `bytes([0x00]) + ...` y `_datos()` arma
# `b"\x40" + ...`. Sin ese byte, el OLED interpretaria la imagen como
# comandos y no se veria nada.

import framebuf

# Secuencia de inicializacion recomendada por el fabricante. Cada par o trio
# es: un comando y sus argumentos. Los importantes:
#   0xAE / 0xAF      pantalla apagada / encendida
#   0x20 0x00        modo de direccionamiento horizontal
#   0xA8 0x3F        multiplexacion: 64 filas (0x3F = 63, o sea 1..64)
#   0x8D 0x14        habilitar la bomba de carga (genera el voltaje del OLED)
#   0xD3 0x00        sin desplazamiento vertical
#   0x40             linea de inicio en 0
#   0x81 0xFF        contraste al maximo
#   0xA1 / 0xC8      orientacion: columnas y filas en espejo
#   0xA6             pixeles normales (no invertidos)
_INICIALIZACION = (
    0xAE, 0x20, 0x00, 0xB0, 0xC8, 0x00, 0x10, 0x40, 0x81, 0xFF, 0xA1, 0xA6,
    0xA8, 0x3F, 0xA4, 0xD3, 0x00, 0xD5, 0x80, 0xD9, 0xF1, 0xDA, 0x12, 0xDB,
    0x40, 0x8D, 0x14, 0xAF,
)


class SSD1306:
    # Pantalla OLED monocroma con framebuffer en RAM.

    def __init__(self, i2c, addr=0x3C, width=128, height=64):
        self.i2c = i2c
        self.addr = addr
        self.width = width
        self.height = height
        # 64 filas / 8 filas por pagina = 8 paginas.
        self.pages = height // 8
        # Un byte por columna y por pagina: 1024 bytes para 128x64.
        self.buffer = bytearray(self.pages * width)
        self.fb = framebuf.FrameBuffer(self.buffer, width, height,
                                       framebuf.MONO_VLSB)
        self.iniciar()

    # -- bajo nivel --------------------------------------------------------
    def _comando(self, *valores):
        # Manda uno o varios comandos (0x00 = "esto es un comando").
        self.i2c.writeto(self.addr, bytes([0x00]) + bytes(valores))

    def _datos(self, datos):
        # Manda bytes de imagen (0x40 = "esto es framebuffer").
        self.i2c.writeto(self.addr, b"\x40" + bytes(datos))

    def iniciar(self):
        # Aplica la secuencia de inicio y deja la pantalla limpia.
        self._comando(*_INICIALIZACION)
        self.limpiar()
        self.mostrar()

    def apagar(self):
        self._comando(0xAE)

    def encender(self):
        self._comando(0xAF)

    def contraste(self, valor):
        # Brillo de 0 a 255 (`& 0xFF` deja el valor en un solo byte).
        self._comando(0x81, valor & 0xFF)

    def mostrar(self):
        # Envia el framebuffer a la pantalla pagina por pagina.
        #
        #         Para cada pagina se manda `0xB0 + pagina` (posicionar en esa pagina) y
        #         luego los 128 bytes de esa franja. `inicio = pagina * ancho` es el
        #         desplazamiento dentro del buffer: pagina 0 -> bytes 0..127, pagina 1
        #         -> 128..255, etc.
        ancho = self.width
        for pagina in range(self.pages):
            self._comando(0xB0 + pagina, 0x00, 0x10)
            inicio = pagina * ancho
            self._datos(self.buffer[inicio:inicio + ancho])

    # -- dibujo (delegado a framebuf) --------------------------------------
    def limpiar(self, color=0):
        # Pinta todo el buffer (0 = negro, 1 = encendido).
        self.fb.fill(color)

    def pixel(self, x, y, color=1):
        self.fb.pixel(x, y, color)

    def texto(self, texto, x, y, color=1):
        # Dibuja texto con la fuente de 8x8 incluida en `framebuf`.
        self.fb.text(texto, x, y, color)

    def linea(self, x1, y1, x2, y2, color=1):
        self.fb.line(x1, y1, x2, y2, color)

    def rectangulo(self, x, y, ancho, alto, color=1):
        self.fb.rect(x, y, ancho, alto, color)

    def rectangulo_relleno(self, x, y, ancho, alto, color=1):
        self.fb.fill_rect(x, y, ancho, alto, color)

    def linea_horizontal(self, x, y, ancho, color=1):
        self.fb.hline(x, y, ancho, color)

    def barra(self, x, y, ancho, alto, fraccion, color=1):
        # Dibuja una barra de progreso de 0.0 a 1.0.
        #
        #         Primero el marco vacio y despues el relleno por dentro. `ancho - 2` es
        #         porque hay un pixel de marco a cada lado; `int(...)` redondea hacia
        #         abajo para no dibujar medio pixel de mas.
        self.fb.rect(x, y, ancho, alto, color)
        if fraccion < 0:
            fraccion = 0.0
        if fraccion > 1:
            fraccion = 1.0
        relleno = int((ancho - 2) * fraccion)
        if relleno > 0:
            self.fb.fill_rect(x + 1, y + 1, relleno, alto - 2, color)
