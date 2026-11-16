#!/usr/bin/env python3
"""Genera los diagramas PNG del informe de Centinela IoT (Parcial #2).

Salidas (docs/img):
    arquitectura.png    capas del sistema
    flujo_datos.png     secuencia de ida y vuelta (telemetria / comandos)
    circuito.png        esquema de conexiones del ESP32 DevKit C V4
    fsm.png             maquina de estados de seguridad
    modelo_datos.png    modelo entidad-relacion de SQLite

Solo usa Pillow y la libreria estandar.

Uso:
    .venv\\Scripts\\python.exe scripts\\generar_diagramas.py
    .venv\\Scripts\\python.exe scripts\\generar_diagramas.py fsm circuito
"""

from __future__ import annotations

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, "docs", "img")

# ---------------------------------------------------------------------------
# Paleta
# ---------------------------------------------------------------------------
BLANCO = (255, 255, 255)
NEGRO = (17, 24, 39)

AZUL = (29, 78, 216)
AZUL_BG = (239, 246, 255)
VERDE = (21, 128, 61)
VERDE_BG = (240, 253, 244)
VIOLETA = (109, 40, 217)
VIOLETA_BG = (245, 243, 255)
AMBAR = (180, 83, 9)
AMBAR_BG = (255, 251, 235)
GRIS = (51, 65, 85)
GRIS_MED = (100, 116, 139)
GRIS_SUAVE = (148, 163, 184)
BORDE = (203, 213, 225)
FONDO_NOTA = (248, 250, 252)
ROJO = (185, 28, 28)
ROJO_BG = (254, 242, 242)

# Colores de cable (circuito)
C_DHT = (8, 145, 178)
C_PIR = (234, 88, 12)
C_TRIG = (124, 58, 237)
C_ECHO = (192, 38, 211)
C_LDR = (202, 138, 4)
C_LEDR = (225, 29, 72)
C_LEDV = (21, 128, 61)
C_BUZZ = (219, 39, 119)
C_SERVO = (13, 148, 136)
C_SDA = (37, 99, 235)
C_SCL = (14, 165, 233)
C_BTN = (71, 85, 105)

PIE = "Centinela IoT - Parcial #2 - Desarrollo de Software VIII"

_CACHE: dict[tuple[int, bool], ImageFont.FreeTypeFont] = {}
_AVISO_FUENTE = [False]


def _rutas_fuente(negrita: bool):
    if negrita:
        nombres = ("segoeuib.ttf", "arialbd.ttf", "calibrib.ttf", "lucon.ttf")
    else:
        nombres = ("segoeui.ttf", "arial.ttf", "calibri.ttf", "lucon.ttf")
    bases = []
    windir = os.environ.get("WINDIR", r"C:\Windows")
    bases.append(os.path.join(windir, "Fonts"))
    bases.append(r"C:\Windows\Fonts")
    local = os.environ.get("LOCALAPPDATA")
    if local:
        bases.append(os.path.join(local, "Microsoft", "Windows", "Fonts"))
    for nombre in nombres:
        yield nombre
        for base in bases:
            yield os.path.join(base, nombre)


def fuente(tam, negrita: bool = False):
    """Devuelve una fuente TrueType; si no hay ninguna, la de Pillow con size."""
    tam = max(6, int(round(tam)))
    clave = (tam, bool(negrita))
    if clave in _CACHE:
        return _CACHE[clave]
    elegida = None
    for ruta in _rutas_fuente(negrita):
        try:
            elegida = ImageFont.truetype(ruta, tam)
            break
        except Exception:
            continue
    if elegida is None:
        try:
            elegida = ImageFont.load_default(size=tam)
        except TypeError:  # Pillow < 10
            elegida = ImageFont.load_default()
        if not _AVISO_FUENTE[0]:
            print("aviso: no se encontro TrueType; se usa load_default()", file=sys.stderr)
            _AVISO_FUENTE[0] = True
    _CACHE[clave] = elegida
    return elegida


def mezclar(color, k: float = 0.9):
    """Aclara un color hacia blanco (k=0 deja el color, k=1 da blanco)."""
    return tuple(int(c + (255 - c) * k) for c in color)


# ---------------------------------------------------------------------------
# Panel de dibujo con utilidades de texto, cajas y flechas
# ---------------------------------------------------------------------------
class Panel:
    def __init__(self, ancho: int, alto: int, titulo: str, subtitulo: str = ""):
        self.ancho = ancho
        self.alto = alto
        self.img = Image.new("RGB", (ancho, alto), BLANCO)
        self.d = ImageDraw.Draw(self.img)
        self.avisos: list[str] = []
        self.nombre = titulo
        self._cabecera(titulo, subtitulo)

    # -- medidas ---------------------------------------------------------
    def ancho_txt(self, texto, f):
        return self.d.textlength(texto, font=f)

    @staticmethod
    def alto_linea(f):
        asc, desc = f.getmetrics()
        return asc + desc

    def envolver(self, texto, f, ancho_max):
        lineas = []
        for parrafo in str(texto).split("\n"):
            actual = ""
            for palabra in parrafo.split(" "):
                prueba = palabra if not actual else actual + " " + palabra
                if not actual or self.ancho_txt(prueba, f) <= ancho_max:
                    actual = prueba
                else:
                    lineas.append(actual)
                    actual = palabra
            lineas.append(actual)
        return lineas

    # -- primitivas ------------------------------------------------------
    def caja(self, x, y, w, h, relleno=BLANCO, borde=AZUL, radio=16, grosor=2):
        radio = int(min(radio, max(2, min(w, h) / 2 - 1)))
        self.d.rounded_rectangle(
            (int(x), int(y), int(x + w), int(y + h)),
            radius=radio, fill=relleno, outline=borde, width=int(grosor),
        )

    def punto(self, x, y, color, r=4):
        self.d.ellipse((x - r, y - r, x + r, y + r), fill=color)

    def linea(self, pts, color=BORDE, grosor=2, dash=None, saltos=None):
        """Polilinea; opcionalmente discontinua y con huecos en x dadas."""
        pts = [(float(a), float(b)) for a, b in pts]
        for i in range(len(pts) - 1):
            (x1, y1), (x2, y2) = pts[i], pts[i + 1]
            if dash:
                self._trazos_discontinuos(x1, y1, x2, y2, color, grosor, dash)
                continue
            if saltos and abs(y1 - y2) < 0.5:
                cortes = sorted(s for s in saltos if min(x1, x2) < s < max(x1, x2))
                trozos = []
                ini = min(x1, x2)
                fin = max(x1, x2)
                for s in cortes:
                    trozos.append((ini, s - 5))
                    ini = s + 5
                trozos.append((ini, fin))
                for a, b in trozos:
                    if b - a > 0.5:
                        self.d.line((a, y1, b, y2), fill=color, width=int(grosor))
                continue
            self.d.line((x1, y1, x2, y2), fill=color, width=int(grosor))

    def _trazos_discontinuos(self, x1, y1, x2, y2, color, grosor, dash):
        largo = math.hypot(x2 - x1, y2 - y1)
        if largo < 1:
            return
        ux, uy = (x2 - x1) / largo, (y2 - y1) / largo
        pos = 0.0
        on = True
        while pos < largo:
            seg = min(dash[0] if on else dash[1], largo - pos)
            if on:
                self.d.line(
                    (x1 + ux * pos, y1 + uy * pos, x1 + ux * (pos + seg), y1 + uy * (pos + seg)),
                    fill=color, width=int(grosor),
                )
            pos += seg
            on = not on

    def flecha(self, pts, color=GRIS, grosor=3, punta=13, ancho_punta=11,
               dash=None, saltos=None):
        """Polilinea con punta de flecha rellena en el ultimo punto."""
        pts = [(float(a), float(b)) for a, b in pts]
        if len(pts) < 2:
            return
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        ang = math.atan2(y2 - y1, x2 - x1)
        bx, by = x2 - punta * math.cos(ang), y2 - punta * math.sin(ang)
        cuerpo = pts[:-1] + [(bx, by)]
        self.linea(cuerpo, color=color, grosor=grosor, dash=dash, saltos=saltos)
        px, py = -math.sin(ang), math.cos(ang)
        self.d.polygon(
            [(x2, y2),
             (bx + px * ancho_punta / 2, by + py * ancho_punta / 2),
             (bx - px * ancho_punta / 2, by - py * ancho_punta / 2)],
            fill=color,
        )

    def curva(self, p0, p1, p2, color=GRIS, grosor=3, punta=13, ancho_punta=11, n=44):
        pts = []
        for i in range(n + 1):
            t = i / n
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
            y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
            pts.append((x, y))
        self.flecha(pts, color=color, grosor=grosor, punta=punta, ancho_punta=ancho_punta)

    def texto(self, x, y, texto, tam=16, color=GRIS, negrita=False, anchor="la"):
        self.d.text((x, y), texto, font=fuente(tam, negrita), fill=color, anchor=anchor)

    def bloque(self, x, y, ancho, lineas, f, color, interlinea=1.15, alinear="center"):
        paso = self.alto_linea(f) * interlinea
        for i, linea in enumerate(lineas):
            yy = y + i * paso
            if alinear == "center":
                self.d.text((x + ancho / 2, yy), linea, font=f, fill=color, anchor="ma")
            elif alinear == "right":
                self.d.text((x + ancho, yy), linea, font=f, fill=color, anchor="ra")
            else:
                self.d.text((x, yy), linea, font=f, fill=color, anchor="la")
        return len(lineas) * paso

    def parrafo(self, x, y, ancho, alto, texto, tam=14, color=GRIS, negrita=False,
                minimo=8, alinear="center", valign="middle", interlinea=1.18,
                registrar=True):
        """Texto ajustado a una caja: reduce el tamano o parte en lineas."""
        tam_actual = int(round(tam))
        while True:
            f = fuente(tam_actual, negrita)
            lineas = self.envolver(texto, f, ancho)
            paso = self.alto_linea(f) * interlinea
            total = paso * len(lineas)
            ancho_real = max(self.ancho_txt(l, f) for l in lineas)
            if (total <= alto and ancho_real <= ancho + 0.5) or tam_actual <= minimo:
                break
            tam_actual -= 1
        if registrar and (total > alto + 1.0 or ancho_real > ancho + 1.0):
            self.avisos.append(
                "texto no cabe (%s): %r" % (self.nombre, texto[:60])
            )
        if valign == "middle":
            y0 = y + (alto - total) / 2
        elif valign == "bottom":
            y0 = y + alto - total
        else:
            y0 = y
        self.bloque(x, y0, ancho, lineas, f, color, interlinea=interlinea, alinear=alinear)
        return total

    def etiqueta(self, cx, cy, texto, tam=14, color=None, negrita=False,
                 relleno=BLANCO, borde=None, pad_x=8, pad_y=4, radio=7,
                 ancho_max=None, anclaje="centro"):
        color = color or GRIS
        f = fuente(tam, negrita)
        lineas = self.envolver(texto, f, ancho_max) if ancho_max else texto.split("\n")
        w = max(self.ancho_txt(l, f) for l in lineas)
        alto = self.alto_linea(f) * 1.15 * len(lineas)
        if anclaje == "izq":
            x0 = cx
        elif anclaje == "der":
            x0 = cx - w - 2 * pad_x
        else:
            x0 = cx - w / 2 - pad_x
        y0 = cy - alto / 2 - pad_y + 2
        self.d.rounded_rectangle(
            (x0, y0, x0 + w + 2 * pad_x, y0 + alto + 2 * pad_y),
            radius=radio, fill=relleno,
            outline=borde if borde else None, width=1 if borde else 0,
        )
        self.bloque(x0 + pad_x, y0 + pad_y - 1, w, lineas, f, color, interlinea=1.15)
        return (x0, y0, w + 2 * pad_x, alto + 2 * pad_y)

    def tarjeta(self, x, y, w, h, titulo, detalle="", relleno=AZUL_BG, borde=AZUL,
                color_titulo=None, tam_titulo=17, tam_detalle=13, radio=14,
                grosor=2, pad=10, alinear="center", separacion=5):
        """Caja con titulo (negrita) y detalle, encogiendo hasta encajar."""
        self.caja(x, y, w, h, relleno=relleno, borde=borde, radio=radio, grosor=grosor)
        color_titulo = color_titulo or borde
        disp_w = w - 2 * pad
        disp_h = h - 2 * pad
        tt, td = tam_titulo, tam_detalle
        while True:
            ft = fuente(tt, True)
            fd = fuente(td)
            lt = self.envolver(titulo, ft, disp_w)
            ld = self.envolver(detalle, fd, disp_w) if detalle else []
            paso_t = self.alto_linea(ft) * 1.12
            paso_d = self.alto_linea(fd) * 1.2
            total = paso_t * len(lt) + (paso_d * len(ld) + separacion if ld else 0)
            if total <= disp_h or tt <= 9 or td <= 8:
                break
            tt -= 1
            td = max(8, td - 0.7)
        if total > disp_h + 1:
            self.avisos.append("tarjeta no cabe (%s): %r" % (self.nombre, titulo))
        y0 = y + (h - total) / 2
        self.bloque(x + pad, y0, disp_w, lt, ft, color_titulo, interlinea=1.12, alinear=alinear)
        if ld:
            self.bloque(x + pad, y0 + paso_t * len(lt) + separacion, disp_w, ld, fd,
                        GRIS, interlinea=1.2, alinear=alinear)

    # -- cabecera y pie --------------------------------------------------
    def _cabecera(self, titulo, subtitulo):
        self.d.text((48, 22), titulo, font=fuente(42, True), fill=GRIS, anchor="la")
        y = 78
        if subtitulo:
            self.d.rounded_rectangle((48, y + 7, 56, y + 15), radius=3, fill=AZUL)
            self.d.text((68, y), subtitulo, font=fuente(18), fill=GRIS_MED, anchor="la")
            y = 112
        self.d.line((48, y + 6, self.ancho - 48, y + 6), fill=BORDE, width=1)

    def pie(self):
        y = self.alto - 34
        self.d.line((48, y - 16, self.ancho - 48, y - 16), fill=BORDE, width=1)
        self.d.text((self.ancho / 2, y), PIE, font=fuente(16), fill=GRIS_SUAVE, anchor="ma")

    def guardar(self, nombre):
        os.makedirs(SALIDA, exist_ok=True)
        ruta = os.path.join(SALIDA, nombre)
        self.img.save(ruta, "PNG", optimize=True)
        return ruta


# ---------------------------------------------------------------------------
# 1) Arquitectura por capas
# ---------------------------------------------------------------------------
def dibujar_arquitectura(nombre="arquitectura.png"):
    p = Panel(1600, 1000, "Arquitectura del sistema — Centinela IoT",
              "ESP32 (Wokwi) → broker MQTT → backend asyncio (SQLite + SSE) → dashboard y nube")
    p.pie()

    capas = [
        (136, 228, "CAPA 1", "DISPOSITIVO\n(ESP32 / Wokwi)", AZUL, AZUL_BG),
        (412, 92, "CAPA 2", "BROKER MQTT", VERDE, VERDE_BG),
        (552, 172, "CAPA 3", "BACKEND PYTHON\n(asyncio)", VIOLETA, VIOLETA_BG),
        (772, 134, "CAPA 4", "USUARIO / NUBE", AMBAR, AMBAR_BG),
    ]
    for (y, h, num, titulo, col, bg) in capas:
        p.caja(48, y, 232, h, relleno=bg, borde=col, radio=18)
        p.texto(164, y + 14, num, tam=13, color=col, negrita=True, anchor="ma")
        p.parrafo(60, y + 36, 208, h - 54, titulo, tam=19, color=col, negrita=True,
                  interlinea=1.1, valign="middle")

    # --- Capa 1 -------------------------------------------------------
    celdas = [
        ("DHT22", "temp / humedad"), ("PIR", "movimiento"),
        ("HC-SR04", "distancia"), ("LDR", "luz"),
    ]
    xs = (322, 502)
    ys = (160, 256)
    for i, (tit, det) in enumerate(celdas):
        x = xs[i % 2]
        y = ys[i // 2]
        p.tarjeta(x, y, 168, 84, tit, det, relleno=AZUL_BG, borde=AZUL,
                  tam_titulo=18, tam_detalle=12)

    p.tarjeta(740, 160, 372, 180, "MicroPython asyncio:",
              "FSM de seguridad\ncliente MQTT propio\nbucle de 50 ms por tarea",
              relleno=AZUL_BG, borde=AZUL, tam_titulo=19, tam_detalle=13)

    actuadores = [
        ("LED rojo / verde", "estado del sistema"), ("Sirena", "PWM bitonal"),
        ("Cerradura", "servo SG90"), ("OLED SSD1306", "I2C 128x64"),
    ]
    for i, (tit, det) in enumerate(actuadores):
        x = xs[i % 2] + 860
        y = ys[i // 2]
        p.tarjeta(x, y, 168, 84, tit, det, relleno=AZUL_BG, borde=AZUL,
                  tam_titulo=15, tam_detalle=11.5)

    for yy in (200, 300):
        p.flecha([(670, yy), (740, yy)], color=GRIS_MED, grosor=2.5, punta=10, ancho_punta=9)
        p.flecha([(1112, yy), (1182, yy)], color=GRIS_MED, grosor=2.5, punta=10, ancho_punta=9)

    # --- Capa 2 -------------------------------------------------------
    p.caja(322, 412, 1208, 92, relleno=VERDE_BG, borde=VERDE, radio=14)
    p.texto(926, 424, "HiveMQ  ·  broker.hivemq.com:1883  /  TLS 8883",
            tam=19, color=VERDE, negrita=True, anchor="ma")
    p.texto(926, 452, "tópicos  centinela/dev01/#   (telemetry · events · status · cmd · ack · config)",
            tam=14, color=GRIS, anchor="ma")
    p.texto(926, 474, "QoS 0 y 1  +  Last Will (LWT) para detectar la caída del nodo",
            tam=13.5, color=GRIS_MED, anchor="ma")

    # --- Capa 3 -------------------------------------------------------
    p.linea([(302, 638), (1550, 638)], color=(226, 232, 240), grosor=2,
            dash=(7, 7))
    piezas = [
        (302, 200, "puente MQTT", "cliente asyncio\nQoS 0 y 1"),
        (524, 236, "servicio de comandos (ACK)", "valida, audita\ny espera el ACK"),
        (782, 288, "SQLite (lecturas, eventos, comandos)", "WAL · índices por\ndevice_id y ts_epoch"),
        (1092, 218, "API REST + SSE", "dashboard web\n/api/stream"),
        (1332, 218, "cliente ThingSpeak", "canal de 8 campos\n+ TalkBack"),
    ]
    for (x, w, tit, det) in piezas:
        p.tarjeta(x, 576, w, 124, tit, det, relleno=VIOLETA_BG, borde=VIOLETA,
                  tam_titulo=15, tam_detalle=11.5)

    # --- Capa 4 -------------------------------------------------------
    p.tarjeta(376, 787, 340, 104, "Dashboard web (navegador)",
              "HTML + JS · SSE en vivo", relleno=AMBAR_BG, borde=AMBAR,
              tam_titulo=16, tam_detalle=12)
    p.tarjeta(760, 787, 372, 104, "ThingSpeak: canal de 8 campos",
              "gráficas históricas en la nube", relleno=AMBAR_BG, borde=AMBAR,
              tam_titulo=16, tam_detalle=12)
    p.tarjeta(1176, 787, 300, 104, "ThingSpeak TalkBack",
              "cola de comandos remota", relleno=AMBAR_BG, borde=AMBAR,
              tam_titulo=15, tam_detalle=12)

    # --- Flechas verticales -------------------------------------------
    tramos = [
        (364, 412, "telemetría / eventos", "comandos / ACK"),
        (504, 552, "comandos / ACK (QoS 1)", "telemetría / eventos"),
        (724, 772, "HTTP (REST + SSE)", "HTTPS (ThingSpeak)"),
    ]
    for (y0, y1, sube, baja) in tramos:
        medio = (y0 + y1) / 2
        p.flecha([(470, y0 + 3), (470, y1 - 3)], color=AZUL, grosor=3, punta=12,
                 ancho_punta=10)
        p.etiqueta(484, medio, sube, tam=13, color=AZUL, relleno=BLANCO, anclaje="izq")
        p.flecha([(1090, y1 - 3), (1090, y0 + 3)], color=VIOLETA, grosor=3, punta=12,
                 ancho_punta=10)
        p.etiqueta(1104, medio, baja, tam=13, color=VIOLETA, relleno=BLANCO, anclaje="izq")

    return p


# ---------------------------------------------------------------------------
# 2) Flujo de datos (ida y vuelta)
# ---------------------------------------------------------------------------
def dibujar_flujo(nombre="flujo_datos.png"):
    p = Panel(1600, 1270, "Flujo de datos — ida (telemetría) y vuelta (comandos)",
              "14 pasos · el nodo y el backend nunca se hablan directo: todo pasa por el broker MQTT")
    p.pie()

    # cabeceras de columna
    for (cx, texto, col, bg) in (
        (305, "NODO ESP32 (Wokwi)", AZUL, AZUL_BG),
        (1265, "NUBE / BACKEND PYTHON", VIOLETA, VIOLETA_BG),
    ):
        f = fuente(15, True)
        w = p.ancho_txt(texto, f) + 34
        p.caja(cx - w / 2, 142, w, 32, relleno=bg, borde=col, radio=16, grosor=2)
        p.texto(cx, 150, texto, tam=15, color=col, negrita=True, anchor="ma")

    def paso(x, y, w, num, titulo, detalle, col, bg):
        h = 70
        p.caja(x, y, w, h, relleno=bg, borde=col, radio=13, grosor=2)
        cx, cy = x + 30, y + h / 2
        p.d.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), fill=col)
        p.texto(cx, cy, str(num), tam=14, color=BLANCO, negrita=True, anchor="mm")
        disp_w = w - 58
        ft = fuente(15.5, True)
        fd = fuente(12.5)
        lt = p.envolver(titulo, ft, disp_w)
        ld = p.envolver(detalle, fd, disp_w)
        total = p.alto_linea(ft) * 1.1 * len(lt) + p.alto_linea(fd) * 1.2 * len(ld) + 3
        y0 = y + (h - total) / 2
        p.bloque(x + 52, y0, disp_w, lt, ft, GRIS, interlinea=1.1, alinear="left")
        p.bloque(x + 52, y0 + p.alto_linea(ft) * 1.1 * len(lt) + 3, disp_w, ld, fd,
                 GRIS_MED, interlinea=1.2, alinear="left")

    XI, WI = 90, 430     # columna nodo
    XD, WD = 1030, 470   # columna nube/backend
    Y = {1: 196, 2: 290, 3: 384, 4: 478, 5: 478, 6: 572, 7: 666, 8: 760,
         9: 854, 10: 948, 11: 1042, 12: 1042, 13: 1136, 14: 1136}

    nodo = [
        (1, "Sensores", "DHT22 · PIR · HC-SR04 · LDR"),
        (2, "Lectura + filtro de mediana", "3 muestras por sensor, descarta outliers"),
        (3, "FSM decide el estado", "DISARMED / ARMING / ARMED / ALARM"),
        (4, "Publica telemetría (QoS 0)", "cada 5 s: temp, hum, lux, dist, motion, state"),
    ]
    for (n, tit, det) in nodo:
        paso(XI, Y[n], WI, n, tit, det, AZUL, AZUL_BG)

    nube = [
        (5, "Broker MQTT (HiveMQ)", "recibe, enruta y publica el Last Will"),
        (6, "Backend guarda en SQLite", "readings + events con ts_epoch y ts_utc"),
        (7, "SSE al panel", "text/event-stream, sin recargar la página"),
        (8, "Navegador (dashboard)", "gráficas, estado y alarmas en vivo"),
        (9, "Panel: el operador ordena", "arm / disarm / mute / unlock + PIN"),
        (10, "API REST valida + audita", "token, rol, argumentos y auditoría"),
        (11, "Publica en …/cmd (QoS 1)", "espera el ACK con timeout"),
    ]
    for (n, tit, det) in nube:
        col, bg = (VERDE, VERDE_BG) if n == 5 else (VIOLETA, VIOLETA_BG)
        paso(XD, Y[n], WD, n, tit, det, col, bg)

    paso(XI, Y[12], WI, 12, "Nodo ejecuta el comando", "decodifica el JSON y aplica la acción",
         AZUL, AZUL_BG)
    paso(XI, Y[13], WI, 13, "ACK con resultado", "ok / rechazado + motivo y estado nuevo",
         AZUL, AZUL_BG)
    paso(XD, Y[14], WD, 14, "Backend marca el comando",
         "OK / RECHAZADO / TIMEOUT + latencia_ms", VIOLETA, VIOLETA_BG)

    # flechas verticales dentro de cada columna
    def vertical(x, y_from, y_to, col):
        p.flecha([(x, y_from + 3), (x, y_to - 3)], color=col, grosor=2.5, punta=10,
                 ancho_punta=9)

    for a, b in ((1, 2), (2, 3), (3, 4)):
        vertical(XI + WI / 2, Y[a] + 70, Y[b], AZUL)
    for a, b in ((5, 6), (6, 7), (7, 8), (8, 9), (9, 10), (10, 11)):
        vertical(XD + WD / 2, Y[a] + 70, Y[b], VIOLETA)
    vertical(XI + WI / 2, Y[12] + 70, Y[13], AZUL)

    # trayectos entre columnas
    p.flecha([(XI + WI, 513), (XD, 513)], color=VERDE, grosor=3.2, punta=13, ancho_punta=11)
    p.etiqueta(775, 502, "PUBLISH  centinela/dev01/telemetry  ·  QoS 0", tam=14.5,
               color=VERDE, negrita=True)
    p.etiqueta(775, 527, "el backend está suscrito a  centinela/dev01/#", tam=12,
               color=GRIS_MED)

    p.flecha([(XD, 1077), (XI + WI, 1077)], color=VIOLETA, grosor=3.2, punta=13,
             ancho_punta=11)
    p.etiqueta(775, 1066, "PUBLISH  centinela/dev01/cmd  ·  QoS 1", tam=14.5,
               color=VIOLETA, negrita=True)
    p.etiqueta(775, 1091, "el nodo está suscrito a ese tópico desde el arranque", tam=12,
               color=GRIS_MED)

    p.flecha([(XI + WI, 1171), (XD, 1171)], color=AZUL, grosor=3.2, punta=13, ancho_punta=11)
    p.etiqueta(775, 1160, "PUBLISH  centinela/dev01/ack  ·  QoS 1", tam=14.5,
               color=AZUL, negrita=True)
    p.etiqueta(775, 1185, "resultado, motivo, estado nuevo y latencia", tam=12,
               color=GRIS_MED)

    # panel de topicos (hueco de la izquierda)
    x, y, w, h = XI, 560, WI, 460
    p.caja(x, y, w, h, relleno=FONDO_NOTA, borde=BORDE, radio=16, grosor=2)
    p.texto(x + 20, y + 16, "Contrato MQTT — tópicos del sistema", tam=15, color=GRIS,
            negrita=True)
    p.linea([(x + 20, y + 42), (x + w - 20, y + 42)], color=BORDE, grosor=1)
    topicos = [
        ("centinela/dev01/telemetry", "QoS 0 · cada 5 s", AZUL),
        ("centinela/dev01/events", "QoS 1 · alarmas y cambios", AMBAR),
        ("centinela/dev01/status", "QoS 0 · cada 30 s · LWT", VERDE),
        ("centinela/dev01/cmd", "QoS 1 · backend → nodo", VIOLETA),
        ("centinela/dev01/ack", "QoS 1 · nodo → backend", AZUL),
        ("centinela/dev01/config", "QoS 0 · configuración", GRIS_MED),
    ]
    for i, (top, det, col) in enumerate(topicos):
        yy = y + 56 + i * 36
        p.d.rectangle((x + 20, yy + 4, x + 23, yy + 15), fill=col)
        p.texto(x + 32, yy, top, tam=12.5, color=GRIS, negrita=True)
        p.texto(x + 32, yy + 16, det, tam=11.5, color=GRIS_MED)
    p.texto(x + 20, y + 284, "Payload (contrato v1):", tam=12.5, color=GRIS, negrita=True)
    p.parrafo(x + 20, y + 304, w - 40, 74,
              '{ "v": 1, "device_id": "dev01", "seq": 42, "ts": 1730000000.5, '
              '"temp_c": 24.1, "hum_pct": 55.2, "lux": 12.0, "dist_cm": 145.0, '
              '"motion": 0, "state": "ARMED", "alarm": 0, ... }',
              tam=11, color=GRIS_MED, alinear="left", valign="top", interlinea=1.3)
    p.linea([(x + 20, y + 386), (x + w - 20, y + 386)], color=BORDE, grosor=1)
    p.texto(x + 20, y + 396, "QoS 0 = telemetría (se pierde antes que bloquear);",
            tam=11.5, color=GRIS_MED)
    p.texto(x + 20, y + 414, "QoS 1 = comandos, ACK y eventos (reintento hasta ACK);",
            tam=11.5, color=GRIS_MED)
    p.texto(x + 20, y + 432, "LWT: sin PINGREQ el broker avisa de la caída del nodo.",
            tam=11.5, color=GRIS_MED)

    # panel derecho (hueco superior)
    x, y, w, h = XD, 196, WD, 248
    p.caja(x, y, w, h, relleno=FONDO_NOTA, borde=BORDE, radio=16, grosor=2)
    p.texto(x + 20, y + 16, "Dos clientes MQTT propios", tam=15, color=GRIS, negrita=True)
    p.linea([(x + 20, y + 42), (x + w - 20, y + 42)], color=BORDE, grosor=1)
    p.parrafo(x + 20, y + 54, w - 40, 184,
              "El nodo implementa su propio cliente MQTT sobre sockets (MicroPython): "
              "CONNECT, PUBLISH, SUBSCRIBE y PINGREQ, con reconexión exponencial de 2 a 60 s.\n\n"
              "El backend usa otro cliente asyncio contra el mismo broker. Ninguno abre "
              "puertos: el broker es el único punto de encuentro, lo que permite tener el "
              "nodo detrás de NAT y varios backends suscritos al mismo tópico.",
              tam=12, color=GRIS_MED, alinear="left", valign="top", interlinea=1.28)
    return p


# ---------------------------------------------------------------------------
# 3) Esquema de conexiones
# ---------------------------------------------------------------------------
def dibujar_circuito(nombre="circuito.png"):
    p = Panel(1600, 1130, "Esquema de conexiones — ESP32 DevKit C V4",
              "10 módulos · 12 señales GPIO + bus de 3V3 y GND · rojo = 3V3, negro = GND")
    p.pie()

    BX, BY, BW, BH = 640, 170, 320, 750
    PY0, PPASO = 250, 44

    izquierda = [
        ("3V3", ROJO), ("EN", None), ("VP / 36", None), ("VN / 39", None),
        ("GPIO34", C_LDR), ("GPIO35", None), ("GPIO32", None), ("GPIO33", None),
        ("GPIO25", C_BUZZ), ("GPIO26", C_PIR), ("GPIO27", C_DHT), ("GPIO14", None),
        ("GPIO12", None), ("GPIO13", C_SERVO), ("GND", NEGRO),
    ]
    derecha = [
        ("GPIO23", C_LEDR), ("GPIO22", C_SCL), ("TX0 / 1", None), ("RX0 / 3", None),
        ("GPIO21", C_SDA), ("GPIO19", C_LEDV), ("GPIO18", C_ECHO), ("GPIO5", C_TRIG),
        ("TX2 / 17", None), ("RX2 / 16", None), ("GPIO4", C_BTN), ("GPIO2", None),
        ("GPIO15", None), ("GND", NEGRO), ("3V3", ROJO),
    ]

    def y_pin(i):
        return PY0 + i * PPASO

    # --- buses de alimentacion (antes que todo lo demas) --------------
    p.linea([(626, y_pin(0)), (620, y_pin(0)), (620, 150), (46, 150), (46, 880)],
            color=ROJO, grosor=3)
    p.linea([(626, y_pin(14)), (614, y_pin(14)), (614, 930), (28, 930), (28, 180)],
            color=NEGRO, grosor=3)
    p.linea([(974, y_pin(14)), (980, y_pin(14)), (980, 930), (1554, 930), (1554, 180)],
            color=ROJO, grosor=3)
    p.linea([(974, y_pin(13)), (986, y_pin(13)), (986, 960), (1572, 960), (1572, 180)],
            color=NEGRO, grosor=3)

    # --- tarjetas de modulo -------------------------------------------
    modulos_izq = [
        ("LDR (sensor de luz)", C_LDR,
         ["VCC → 3V3 · AO → GPIO34 · GND → GND", "AO: entrada analógica ADC1 (solo lectura)"]),
        ("Buzzer (sirena)", C_BUZZ,
         ["positivo → GPIO25 · negativo → GND", "PWM bitonal 2400 / 2900 Hz"]),
        ("PIR (movimiento)", C_PIR,
         ["VCC → 3V3 · OUT → GPIO26 · GND → GND", "salida digital 3V3 al detectar movimiento"]),
        ("DHT22 (temp / humedad)", C_DHT,
         ["VCC → 3V3 · DATA → GPIO27 · GND → GND", "lectura cada 5 s con 3 reintentos"]),
        ("Servo SG90 (cerradura)", C_SERVO,
         ["PWM → GPIO13 · V+ → 3V3 · GND → GND", "50 Hz · 0° cerrado / 90° abierto"]),
    ]
    modulos_der = [
        ("LED rojo (alarma)", C_LEDR,
         ["GPIO23 → R 220 Ω → ánodo · cátodo → GND", "enciende en ALARM"]),
        ("OLED SSD1306 (128x64)", C_SDA,
         ["SDA → GPIO21 · SCL → GPIO22 · VCC → 3V3 · GND → GND", "I2C 400 kHz · dirección 0x3C"]),
        ("LED verde (estado)", C_LEDV,
         ["GPIO19 → R 220 Ω → ánodo · cátodo → GND", "enciende en DISARMED"]),
        ("HC-SR04 (distancia)", C_ECHO,
         ["VCC → 3V3 · TRIG → GPIO5 · ECHO → GPIO18 · GND → GND", "umbral de intrusión: < 80 cm"]),
        ("Pulsador (arm / disarm)", C_BTN,
         ["GPIO4 → terminal 1 · GND → terminal 2", "INPUT_PULLUP · antirrebote 250 ms"]),
    ]

    FY = [180, 322, 464, 606, 748]
    FH = 132
    VCC_DY, GND_DY = 102, 118
    for i, (tit, col, lineas) in enumerate(modulos_izq):
        y = FY[i]
        p.caja(60, y, 410, FH, relleno=mezclar(col, 0.93), borde=col, radio=13)
        p.d.rectangle((60, y + 8, 64, y + FH - 8), fill=col)
        p.texto(78, y + 12, tit, tam=15.5, color=GRIS, negrita=True)
        for j, ln in enumerate(lineas):
            p.texto(78, y + 44 + j * 20, ln, tam=12.5, color=GRIS_MED)
        p.punto(60, y + FH / 2, col, r=4)

    for i, (tit, col, lineas) in enumerate(modulos_der):
        y = FY[i]
        p.caja(1130, y, 410, FH, relleno=mezclar(col, 0.93), borde=col, radio=13)
        p.d.rectangle((1536, y + 8, 1540, y + FH - 8), fill=col)
        p.texto(1148, y + 12, tit, tam=15.5, color=GRIS, negrita=True)
        for j, ln in enumerate(lineas):
            p.texto(1148, y + 44 + j * 20, ln, tam=12.5, color=GRIS_MED)
        p.punto(1540, y + FH / 2, col, r=4)

    # --- stubs de alimentacion (con hueco al cruzar el otro bus) -----
    for i in range(5):
        y = FY[i]
        p.linea([(60, y + VCC_DY), (46, y + VCC_DY)], color=ROJO, grosor=3)
        p.punto(46, y + VCC_DY, ROJO, r=3.5)
        p.linea([(60, y + GND_DY), (50, y + GND_DY)], color=NEGRO, grosor=3)
        p.linea([(42, y + GND_DY), (28, y + GND_DY)], color=NEGRO, grosor=3)
        p.punto(28, y + GND_DY, NEGRO, r=3.5)
        p.linea([(1540, y + VCC_DY), (1554, y + VCC_DY)], color=ROJO, grosor=3)
        p.punto(1554, y + VCC_DY, ROJO, r=3.5)
        p.linea([(1540, y + GND_DY), (1548, y + GND_DY)], color=NEGRO, grosor=3)
        p.linea([(1562, y + GND_DY), (1572, y + GND_DY)], color=NEGRO, grosor=3)
        p.punto(1572, y + GND_DY, NEGRO, r=3.5)

    # --- cables de senal ---------------------------------------------
    # (pin, y_tarjeta, color, x_carril)
    cables_izq = [
        (4, FY[0] + FH / 2, C_LDR, 545),
        (8, FY[1] + FH / 2, C_BUZZ, 562),
        (9, FY[2] + FH / 2, C_PIR, 579),
        (10, FY[3] + FH / 2, C_DHT, 596),
        (13, FY[4] + FH / 2, C_SERVO, 613),
    ]
    for (idx, ytar, col, carril) in cables_izq:
        yy = y_pin(idx)
        p.linea([(626, yy), (carril, yy), (carril, ytar), (470, ytar)],
                color=col, grosor=2.8)
        p.punto(626, yy, col, r=3.5)
        p.punto(470, ytar, col, r=3.5)

    cables_der = [
        (0, FY[0] + FH / 2, C_LEDR, 1030),
        (1, FY[1] + FH / 2 - 30, C_SCL, 1044),
        (4, FY[1] + FH / 2 + 26, C_SDA, 1058),
        (5, FY[2] + FH / 2, C_LEDV, 1072),
        (6, FY[3] + FH / 2 - 22, C_ECHO, 1086),
        (7, FY[3] + FH / 2 + 26, C_TRIG, 1100),
        (10, FY[4] + FH / 2, C_BTN, 1114),
    ]
    for (idx, ytar, col, carril) in cables_der:
        yy = y_pin(idx)
        p.linea([(974, yy), (carril, yy), (carril, ytar), (1130, ytar)],
                color=col, grosor=2.8)
        p.punto(974, yy, col, r=3.5)
        p.punto(1130, ytar, col, r=3.5)

    # --- placa --------------------------------------------------------
    p.caja(BX, BY, BW, BH, relleno=(248, 250, 252), borde=GRIS, radio=14, grosor=2.5)
    p.texto(BX + BW / 2, BY + 22, "ESP32 DevKit C V4", tam=18, color=GRIS, negrita=True,
            anchor="ma")
    p.d.rounded_rectangle((BX + 85, 420, BX + 235, 610), radius=8, fill=(51, 65, 85))
    p.bloque(BX + 90, 448, 145, ["ESP32", "WROOM-32"], fuente(12.5, True), BLANCO,
             interlinea=1.15)
    p.bloque(BX + 90, 520, 145, ["240 MHz", "Wi-Fi + BT"], fuente(11), (203, 213, 225),
             interlinea=1.15)
    p.d.rounded_rectangle((BX + 130, 892, BX + 190, 918), radius=4, fill=(148, 163, 184))
    p.texto(BX + 160, 899, "USB", tam=9.5, color=BLANCO, negrita=True, anchor="ma")

    for i, (etiqueta, col) in enumerate(izquierda):
        y = y_pin(i)
        usado = col is not None
        p.d.rounded_rectangle((626, y - 5, 640, y + 5), radius=2,
                              fill=col if usado else (203, 213, 225))
        p.texto(650, y - 9, etiqueta, tam=12, color=GRIS if usado else GRIS_SUAVE,
                negrita=usado)
    for i, (etiqueta, col) in enumerate(derecha):
        y = y_pin(i)
        usado = col is not None
        p.d.rounded_rectangle((960, y - 5, 974, y + 5), radius=2,
                              fill=col if usado else (203, 213, 225))
        p.texto(950, y - 9, etiqueta, tam=12, color=GRIS if usado else GRIS_SUAVE,
                negrita=usado, anchor="ra")

    # --- leyenda ------------------------------------------------------
    p.caja(48, 1000, 1504, 62, relleno=FONDO_NOTA, borde=BORDE, radio=12, grosor=2)
    p.texto(66, 1018, "Leyenda", tam=14, color=GRIS, negrita=True)
    items = [
        ("3V3 — alimentación", ROJO), ("GND — tierra", NEGRO),
        ("señal digital", (37, 99, 235)), ("ADC / analógica", C_LDR),
        ("I2C (SDA / SCL)", C_TRIG), ("PWM (servo)", C_SERVO),
    ]
    x = 150
    for (texto, col) in items:
        p.d.line((x, 1031, x + 26, 1031), fill=col, width=3)
        p.texto(x + 34, 1024, texto, tam=12.5, color=GRIS_MED)
        x += 34 + p.ancho_txt(texto, fuente(12.5)) + 22
    p.texto(1540, 1024, "LED: 220 Ω en serie  ·  pulsador INPUT_PULLUP", tam=12.5,
            color=GRIS_MED, anchor="ra")
    return p


# ---------------------------------------------------------------------------
# 4) Maquina de estados
# ---------------------------------------------------------------------------
def dibujar_fsm(nombre="fsm.png"):
    p = Panel(1600, 1000, "Máquina de estados de seguridad (FSM)",
              "4 estados · transiciones por comando, temporizador o lectura de sensores")
    p.pie()

    est = {
        "DISARMED": (180, 240, 280, 150, AZUL, AZUL_BG, "sistema desactivado",
                     "cerradura abierta con PIN · LED verde"),
        "ARMING": (900, 240, 280, 150, AMBAR, AMBAR_BG, "cuenta de salida 10 s",
                   "LED ámbar parpadea · sirena no suena"),
        "ARMED": (900, 660, 280, 150, VERDE, VERDE_BG, "vigilando",
                  "PIR + HC-SR04 + DHT22 activos"),
        "ALARM": (180, 660, 280, 150, ROJO, ROJO_BG, "alarma activa",
                  "sirena bitonal + LED rojo"),
    }
    for (nombre_est, (x, y, w, h, col, bg, sub, det)) in est.items():
        p.caja(x, y, w, h, relleno=bg, borde=col, radio=18, grosor=3)
        p.texto(x + w / 2, y + 20, nombre_est, tam=32, color=col, negrita=True, anchor="ma")
        p.texto(x + w / 2, y + 68, sub, tam=13.5, color=col, negrita=True, anchor="ma")
        p.parrafo(x + 16, y + 92, w - 32, 44, det, tam=12.5, color=GRIS,
                  alinear="center", valign="top")

    # inicio
    p.punto(110, 315, GRIS, r=7)
    p.flecha([(117, 315), (180, 315)], color=GRIS, grosor=2.5, punta=11, ancho_punta=9)
    p.texto(120, 286, "inicio", tam=12, color=GRIS_MED)

    # DISARMED -> ARMING  (arm)
    p.flecha([(460, 315), (900, 315)], color=AZUL, grosor=3, punta=13, ancho_punta=11)
    p.etiqueta(680, 296, "arm", tam=14, color=AZUL, negrita=True)

    # ARMING -> DISARMED  (disarm)
    p.curva((900, 276), (680, 130), (460, 276), color=AMBAR, grosor=2.6, punta=12,
            ancho_punta=10)
    p.etiqueta(680, 170, "disarm", tam=13, color=AMBAR, negrita=True)

    # ARMING -> ARMED  (fin de cuenta)
    p.flecha([(1040, 390), (1040, 660)], color=VERDE, grosor=3, punta=13, ancho_punta=11)
    p.etiqueta(1054, 525, "fin de cuenta\n(10 s)", tam=13, color=VERDE, negrita=True,
               anclaje="izq")

    # ARMED -> ALARM  presencia
    p.flecha([(900, 712), (460, 712)], color=ROJO, grosor=3, punta=13, ancho_punta=11)
    p.etiqueta(680, 690, "presencia  (PIR o distancia < 80 cm)", tam=13, color=ROJO,
               negrita=True)

    # ARMED -> ALARM  temperatura
    p.flecha([(900, 792), (460, 792)], color=AMBAR, grosor=3, punta=13, ancho_punta=11)
    p.etiqueta(680, 770, "temperatura > 45 °C", tam=13, color=AMBAR, negrita=True)

    # ALARM -> DISARMED
    p.flecha([(320, 660), (320, 390)], color=AZUL, grosor=3, punta=13, ancho_punta=11)
    p.etiqueta(334, 525, "disarm", tam=13, color=AZUL, negrita=True, anclaje="izq")

    # ARMED -> DISARMED
    p.flecha([(920, 660), (460, 372)], color=AZUL, grosor=3, punta=13, ancho_punta=11)
    p.etiqueta(742, 516, "disarm", tam=13, color=AZUL, negrita=True)

    # ALARM -> ALARM  mute
    p.curva((180, 700), (62, 726), (180, 752), color=GRIS, grosor=2.6, punta=12,
            ancho_punta=10)
    p.etiqueta(120, 664, "mute", tam=12, color=GRIS, negrita=True)
    p.etiqueta(120, 786, "sirena silenciada,\nel estado sigue en ALARM", tam=10.5,
               color=GRIS_MED, relleno=BLANCO, ancho_max=110)

    # notas laterales
    x, y, w, h = 1240, 240, 312, 660
    p.caja(x, y, w, h, relleno=FONDO_NOTA, borde=BORDE, radio=16, grosor=2)
    p.texto(x + 20, y + 16, "Notas de implementación", tam=15, color=GRIS, negrita=True)
    p.linea([(x + 20, y + 42), (x + w - 20, y + 42), ], color=BORDE, grosor=1)
    notas = [
        ("Antirrebote de 5 s por alerta", "una misma intrusión no cuenta dos veces "
         "(cooldown_alerta_s = 5.0)."),
        ("unlock solo en DISARMED y con PIN", "PIN 2468; 3 intentos fallidos bloquean "
         "30 s."),
        ("La sirena se calla sola", "a los 120 s (sirena_max_s) y el estado sigue en "
         "ALARM."),
        ("mute no cambia de estado", "silencia la sirena pero el estado sigue en ALARM."),
        ("La cerradura se auto-cierra", "8 s después de abrir (auto_relock_s)."),
        ("Toda transición se publica", "evento en centinela/dev01/events + fila en "
         "state_changes."),
        ("El estado viaja en la telemetría", "el campo state se guarda en readings y "
         "se sube a ThingSpeak."),
    ]
    yy = y + 54
    for (tit, det) in notas:
        p.d.ellipse((x + 20, yy + 5, x + 27, yy + 12), fill=AZUL)
        p.texto(x + 34, yy, tit, tam=12.5, color=GRIS, negrita=True)
        alto = p.parrafo(x + 34, yy + 19, w - 58, 60, det, tam=11.5, color=GRIS_MED,
                         alinear="left", valign="top", interlinea=1.24)
        yy += 19 + alto + 12
    p.linea([(x + 20, yy + 2), (x + w - 20, yy + 2)], color=BORDE, grosor=1)
    p.texto(x + 20, yy + 14, "Estados posibles", tam=12, color=GRIS, negrita=True)
    for i, (nom, col) in enumerate((("DISARMED", AZUL), ("ARMING", AMBAR),
                                    ("ARMED", VERDE), ("ALARM", ROJO))):
        yy2 = yy + 36 + i * 20
        p.d.rounded_rectangle((x + 22, yy2 + 4, x + 36, yy2 + 14), radius=3, fill=col)
        p.texto(x + 44, yy2, nom, tam=11.5, color=col, negrita=True)
    return p


# ---------------------------------------------------------------------------
# 5) Modelo de datos
# ---------------------------------------------------------------------------
def dibujar_modelo(nombre="modelo_datos.png"):
    p = Panel(1600, 1190, "Modelo de datos (SQLite) — 5 tablas",
              "ts_epoch (REAL) para cálculos e índices · ts_utc (TEXT ISO-8601) para lectura humana")
    p.pie()

    def tabla(x, y, w, titulo, col, bg, filas, h_fila=24, h_cab=38):
        h = h_cab + len(filas) * h_fila + 8
        p.caja(x, y, w, h, relleno=BLANCO, borde=col, radio=12, grosor=2)
        p.d.rounded_rectangle((x + 1, y + 1, x + w - 1, y + h_cab), radius=11, fill=col)
        p.d.rectangle((x + 1, y + h_cab - 14, x + w - 1, y + h_cab), fill=col)
        p.texto(x + 14, y + 9, titulo, tam=16, color=BLANCO, negrita=True)
        for i, (nom, tipo, clave) in enumerate(filas):
            yy = y + h_cab + 4 + i * h_fila
            if i % 2 == 1:
                p.d.rectangle((x + 2, yy, x + w - 2, yy + h_fila), fill=FONDO_NOTA)
            if clave:
                relleno = col if clave == "PK" else bg
                p.d.rounded_rectangle((x + 10, yy + 5, x + 40, yy + 19), radius=4,
                                      fill=relleno, outline=col, width=1)
                p.texto(x + 25, yy + 6, clave, tam=9, color=BLANCO if clave == "PK" else col,
                        negrita=True, anchor="ma")
            p.texto(x + 48, yy + 4, nom, tam=12.5, color=GRIS,
                    negrita=(clave == "PK"))
            p.texto(x + w - 12, yy + 5, tipo, tam=10.5, color=GRIS_SUAVE, anchor="ra")
        return h

    filas_dev = [
        ("device_id", "TEXT", "PK"), ("nombre", "TEXT", ""), ("ubicacion", "TEXT", ""),
        ("firmware", "TEXT", ""), ("creado_utc", "TEXT", ""), ("visto_utc", "TEXT", ""),
        ("visto_epoch", "REAL", ""),
    ]
    filas_read = [
        ("id", "INTEGER", "PK"), ("device_id", "TEXT", "FK"), ("ts_epoch", "REAL", ""),
        ("ts_utc", "TEXT", ""), ("temp_c", "REAL", ""), ("hum_pct", "REAL", ""),
        ("lux", "REAL", ""), ("dist_cm", "REAL", ""), ("motion", "INTEGER", ""),
        ("state", "TEXT", ""), ("alarm", "INTEGER", ""), ("siren", "INTEGER", ""),
        ("locked", "INTEGER", ""), ("alerts", "INTEGER", ""), ("rssi", "INTEGER", ""),
        ("seq", "INTEGER", ""), ("sensor_errors", "INTEGER", ""), ("payload", "TEXT", ""),
    ]
    filas_ev = [
        ("id", "INTEGER", "PK"), ("device_id", "TEXT", "FK"), ("ts_epoch", "REAL", ""),
        ("ts_utc", "TEXT", ""), ("kind", "TEXT", ""), ("severity", "TEXT", ""),
        ("message", "TEXT", ""), ("state", "TEXT", ""), ("data_json", "TEXT", ""),
    ]
    filas_cmd = [
        ("id", "TEXT", "PK"), ("device_id", "TEXT", "FK"), ("cmd", "TEXT", ""),
        ("args_json", "TEXT", ""), ("source", "TEXT", ""), ("estado", "TEXT", ""),
        ("emitido_epoch", "REAL", ""), ("emitido_utc", "TEXT", ""),
        ("confirmado_epoch", "REAL", ""), ("latencia_ms", "INTEGER", ""),
        ("resultado_json", "TEXT", ""), ("motivo", "TEXT", ""),
    ]
    filas_st = [
        ("id", "INTEGER", "PK"), ("device_id", "TEXT", "FK"), ("ts_epoch", "REAL", ""),
        ("ts_utc", "TEXT", ""), ("desde", "TEXT", ""), ("hacia", "TEXT", ""),
        ("motivo", "TEXT", ""),
    ]

    DX, DY, DW = 560, 150, 440
    h_dev = tabla(DX, DY, DW, "devices", AZUL, AZUL_BG, filas_dev, h_fila=27, h_cab=40)

    CYW = 360
    pos = {
        "readings": (44, 520, CYW, VIOLETA, VIOLETA_BG, filas_read),
        "events": (428, 520, CYW, AMBAR, AMBAR_BG, filas_ev),
        "commands": (812, 520, CYW, VERDE, VERDE_BG, filas_cmd),
        "state_changes": (1196, 520, CYW, (71, 85, 105), (241, 245, 249), filas_st),
    }
    medidas = {}
    for nombre_t, (x, y, w, col, bg, filas) in pos.items():
        medidas[nombre_t] = tabla(x, y, w, nombre_t, col, bg, filas)

    # relaciones 1 --- N
    def relacion(puntos, col):
        p.linea(puntos, color=col, grosor=2.2)
        x0, y0 = puntos[0]
        x1, y1 = puntos[-1]
        p.etiqueta(x0 + 12, y0 + 9, "1", tam=12.5, color=col, negrita=True, relleno=BLANCO)
        # pata de gallo en el extremo hijo (el "muchos" mira a la tabla)
        p.d.line((x1 - 10, y1 - 1, x1, y1 - 13), fill=col, width=2)
        p.d.line((x1, y1 - 1, x1, y1 - 13), fill=col, width=2)
        p.d.line((x1 + 10, y1 - 1, x1, y1 - 13), fill=col, width=2)
        p.etiqueta(x1 + 19, y1 - 15, "N", tam=12.5, color=col, negrita=True, relleno=BLANCO)

    relacion([(600, DY + h_dev), (600, 420), (224, 420), (224, 520)], VIOLETA)
    relacion([(720, DY + h_dev), (720, 445), (608, 445), (608, 520)], AMBAR)
    relacion([(860, DY + h_dev), (860, 470), (992, 470), (992, 520)], VERDE)
    relacion([(1000, DY + h_dev), (1000, 495), (1376, 495), (1376, 520)], (71, 85, 105))

    # convenciones (hueco superior izquierdo)
    x, y, w, h = 44, 186, 440, 212
    p.caja(x, y, w, h, relleno=FONDO_NOTA, borde=BORDE, radio=14, grosor=2)
    p.texto(x + 18, y + 14, "Convenciones", tam=14, color=GRIS, negrita=True)
    p.linea([(x + 18, y + 38), (x + w - 18, y + 38)], color=BORDE, grosor=1)
    conv = [
        ("PK", "clave primaria (INTEGER AUTOINCREMENT o TEXT)"),
        ("FK", "clave foránea → devices(device_id)"),
        ("1 — N", "un dispositivo, muchas filas hijas"),
    ]
    for i, (chip, texto) in enumerate(conv):
        yy = y + 52 + i * 40
        p.d.rounded_rectangle((x + 18, yy + 2, x + 62, yy + 18), radius=4,
                              fill=AZUL_BG, outline=AZUL, width=1)
        p.texto(x + 40, yy + 3, chip, tam=10, color=AZUL, negrita=True, anchor="ma")
        p.parrafo(x + 72, yy, w - 92, 34, texto, tam=11.5, color=GRIS_MED,
                  alinear="left", valign="top", interlinea=1.2)
    p.linea([(x + 18, y + 172), (x + w - 18, y + 172)], color=BORDE, grosor=1)
    p.texto(x + 18, y + 182, "DELETE CASCADE: al borrar el device se borran sus filas.",
            tam=11, color=GRIS_SUAVE)

    # vistas (hueco inferior derecho)
    x, y, w, h = 1196, 790, 360, 226
    p.caja(x, y, w, h, relleno=FONDO_NOTA, borde=BORDE, radio=14, grosor=2)
    p.texto(x + 18, y + 14, "Vistas SQL del informe", tam=13.5, color=GRIS, negrita=True)
    p.linea([(x + 18, y + 38), (x + w - 18, y + 38)], color=BORDE, grosor=1)
    vistas = [
        ("v_ultima_lectura", "última lectura de cada device"),
        ("v_resumen_horario", "promedios y alarmas por hora"),
        ("v_salud_comandos", "OK / rechazos / timeouts por día"),
        ("v_eventos_criticos", "eventos warning y critical"),
        ("v_estado_actual", "último estado de la FSM"),
    ]
    for i, (nom, det) in enumerate(vistas):
        yy = y + 52 + i * 34
        p.texto(x + 18, yy, nom, tam=11.5, color=VIOLETA, negrita=True)
        p.texto(x + 18, yy + 15, det, tam=10.5, color=GRIS_MED)

    # nota de indices
    x, y, w, h = 44, 1035, 1512, 100
    p.caja(x, y, w, h, relleno=FONDO_NOTA, borde=BORDE, radio=12, grosor=2)
    p.texto(x + 18, y + 12, "Índices principales (sql/schema.sql)", tam=13.5, color=GRIS,
            negrita=True)
    p.texto(x + 18, y + 34,
            "readings(device_id, ts_epoch DESC) · readings(alarm, ts_epoch DESC) · "
            "events(device_id, ts_epoch DESC) · events(severity, ts_epoch DESC)",
            tam=11.5, color=GRIS_MED)
    p.texto(x + 18, y + 54,
            "commands(emitido_epoch DESC) · commands(estado) · "
            "state_changes(device_id, ts_epoch DESC)",
            tam=11.5, color=GRIS_MED)
    p.texto(x + 18, y + 74,
            "FK ON DELETE CASCADE · PRAGMA foreign_keys = ON · una fila de readings por "
            "cada mensaje de telemetría",
            tam=11.5, color=GRIS_MED)
    return p


# ---------------------------------------------------------------------------
GENERADORES = {
    "arquitectura": (dibujar_arquitectura, "arquitectura.png", 1),
    "flujo": (dibujar_flujo, "flujo_datos.png", 2),
    "circuito": (dibujar_circuito, "circuito.png", 3),
    "fsm": (dibujar_fsm, "fsm.png", 4),
    "modelo": (dibujar_modelo, "modelo_datos.png", 5),
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    pedidos = [a for a in argv if not a.startswith("-")]
    claves = [k for k in GENERADORES if not pedidos or k in pedidos]
    if not claves:
        print("no hay diagramas que coincidan con: %s" % ", ".join(pedidos))
        return 2

    problemas = 0
    print("Destino: %s" % SALIDA)
    for clave in claves:
        funcion, nombre, numero = GENERADORES[clave]
        panel = funcion()
        ruta = panel.guardar(nombre)
        kb = os.path.getsize(ruta) / 1024.0
        print("%d) %-18s %5.1f KB  %dx%d" % (numero, nombre, kb, panel.ancho, panel.alto))
        for aviso in panel.avisos:
            print("   AVISO: %s" % aviso)
        problemas += len(panel.avisos)
        if kb <= 20:
            print("   AVISO: %s pesa menos de 20 KB" % nombre)
            problemas += 1
    if problemas:
        print("%d aviso(s) de maquetacion" % problemas)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
