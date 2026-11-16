"""Driver minimo del OLED SSD1306 (I2C 128x64) sobre `framebuf`.

Solo incluye lo necesario para la interfaz local del nodo: inicializacion,
volcado del framebuffer y utilidades de texto/lineas heredadas de framebuf.
"""

import framebuf

# Secuencia de inicializacion recomendada por el fabricante
_INICIALIZACION = (
    0xAE, 0x20, 0x00, 0xB0, 0xC8, 0x00, 0x10, 0x40, 0x81, 0xFF, 0xA1, 0xA6,
    0xA8, 0x3F, 0xA4, 0xD3, 0x00, 0xD5, 0x80, 0xD9, 0xF1, 0xDA, 0x12, 0xDB,
    0x40, 0x8D, 0x14, 0xAF,
)


class SSD1306:
    """Pantalla OLED monocroma con framebuffer en RAM."""

    def __init__(self, i2c, addr=0x3C, width=128, height=64):
        self.i2c = i2c
        self.addr = addr
        self.width = width
        self.height = height
        self.pages = height // 8
        self.buffer = bytearray(self.pages * width)
        self.fb = framebuf.FrameBuffer(self.buffer, width, height,
                                       framebuf.MONO_VLSB)
        self.iniciar()

    # -- bajo nivel --------------------------------------------------------
    def _comando(self, *valores):
        self.i2c.writeto(self.addr, bytes([0x00]) + bytes(valores))

    def _datos(self, datos):
        self.i2c.writeto(self.addr, b"\x40" + bytes(datos))

    def iniciar(self):
        self._comando(*_INICIALIZACION)
        self.limpiar()
        self.mostrar()

    def apagar(self):
        self._comando(0xAE)

    def encender(self):
        self._comando(0xAF)

    def contraste(self, valor):
        self._comando(0x81, valor & 0xFF)

    def mostrar(self):
        """Envia el framebuffer a la pantalla pagina por pagina."""
        ancho = self.width
        for pagina in range(self.pages):
            self._comando(0xB0 + pagina, 0x00, 0x10)
            inicio = pagina * ancho
            self._datos(self.buffer[inicio:inicio + ancho])

    # -- dibujo (delegado a framebuf) --------------------------------------
    def limpiar(self, color=0):
        self.fb.fill(color)

    def pixel(self, x, y, color=1):
        self.fb.pixel(x, y, color)

    def texto(self, texto, x, y, color=1):
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
        """Dibuja una barra de progreso de 0.0 a 1.0."""
        self.fb.rect(x, y, ancho, alto, color)
        if fraccion < 0:
            fraccion = 0.0
        if fraccion > 1:
            fraccion = 1.0
        relleno = int((ancho - 2) * fraccion)
        if relleno > 0:
            self.fb.fill_rect(x + 1, y + 1, relleno, alto - 2, color)
