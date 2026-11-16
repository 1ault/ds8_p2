"""Evidencias de ejecucion: capturas del panel, del login y de la consola.

El panel se captura con Chrome/Edge en modo headless (captura real del
navegador con datos reales de la API). Las consolas se renderizan a PNG a
partir de la salida de verdad de la CLI.

Uso:
    python scripts/capturar_dashboard.py                # todo
    python scripts/capturar_dashboard.py --solo-panel
    python scripts/capturar_dashboard.py --puerto 8020
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import io
import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
for ruta in (str(RAIZ), str(RAIZ / "firmware")):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

DESTINO = RAIZ / "docs" / "capturas"

NAVEGADORES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)

FUENTES_MONO = ("consola.ttf", "cour.ttf", "DejaVuSansMono.ttf", "arial.ttf")


def log(mensaje):
    print("[capturas] %s" % mensaje, flush=True)


# ---------------------------------------------------------------------------
# Navegador headless
# ---------------------------------------------------------------------------
def encontrar_navegador():
    for ruta in NAVEGADORES:
        if Path(ruta).exists():
            return ruta
    for nombre in ("chrome", "msedge", "chromium"):
        encontrado = shutil.which(nombre)
        if encontrado:
            return encontrado
    return None


async def capturar_pagina(navegador, url, salida: Path, ancho=1680, alto=1050,
                          espera_s=4.0, puerto_cdp=9333) -> bool:
    """Captura una pagina con Chrome/Edge via DevTools Protocol.

    Se usa CDP en lugar de `--screenshot` porque el modo captura del navegador
    se queda esperando cuando la pagina mantiene una conexion HTTP abierta.
    Con CDP se navega, se espera un tiempo fijo y se pide la imagen: siempre
    termina.
    """
    import base64

    import aiohttp

    salida.parent.mkdir(parents=True, exist_ok=True)
    perfil = RAIZ / ".tmp" / ("chrome-perfil-%d" % puerto_cdp)
    shutil.rmtree(perfil, ignore_errors=True)
    perfil.mkdir(parents=True, exist_ok=True)

    comando = [
        navegador,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-breakpad",
        "--disable-crash-reporter",
        "--disable-extensions",
        "--disable-features=Translate,BackForwardCache",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        "--user-data-dir=%s" % str(perfil),
        "--window-size=%d,%d" % (ancho, alto),
        "--remote-debugging-port=%d" % puerto_cdp,
        "about:blank",
    ]

    proceso = subprocess.Popen(comando, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    try:
        async with aiohttp.ClientSession() as sesion:
            destino = None
            for _ in range(60):
                try:
                    async with sesion.get(
                            "http://127.0.0.1:%d/json/list" % puerto_cdp) as resp:
                        destinos = await resp.json(content_type=None)
                    paginas = [d for d in destinos if d.get("type") == "page"]
                    if paginas:
                        destino = paginas[0]
                        break
                except (aiohttp.ClientError, ValueError, OSError):
                    pass
                await asyncio.sleep(0.25)

            if destino is None:
                log("el navegador no expuso DevTools para %s" % url)
                return False

            async with sesion.ws_connect(destino["webSocketDebuggerUrl"],
                                         max_msg_size=0) as ws:
                contador = {"id": 0}

                async def enviar(metodo, parametros=None):
                    contador["id"] += 1
                    ident = contador["id"]
                    await ws.send_json({"id": ident, "method": metodo,
                                        "params": parametros or {}})
                    while True:
                        mensaje = await asyncio.wait_for(ws.receive_json(), 30)
                        if mensaje.get("id") == ident:
                            return mensaje

                await enviar("Page.enable")
                await enviar("Emulation.setDeviceMetricsOverride", {
                    "width": ancho, "height": alto,
                    "deviceScaleFactor": 1, "mobile": False,
                })
                await enviar("Page.navigate", {"url": url})
                await asyncio.sleep(espera_s)
                respuesta = await enviar("Page.captureScreenshot",
                                         {"format": "png"})
                datos = respuesta.get("result", {}).get("data")
                if not datos:
                    log("el navegador no devolvio imagen de %s" % url)
                    return False
                salida.write_bytes(base64.b64decode(datos))
    except (OSError, aiohttp.ClientError, asyncio.TimeoutError) as exc:
        log("fallo la captura de %s: %s" % (url, exc))
        return False
    finally:
        proceso.terminate()
        try:
            proceso.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proceso.kill()

    if not salida.exists() or salida.stat().st_size < 5000:
        log("captura vacia de %s" % url)
        return False
    log("%s  (%.0f KB)" % (salida.name, salida.stat().st_size / 1024))
    return True


# ---------------------------------------------------------------------------
# Consola renderizada
# ---------------------------------------------------------------------------
def _fuente_mono(tamano, negrita=False):
    from PIL import ImageFont

    candidatas = list(FUENTES_MONO)
    if negrita:
        candidatas = ["consolab.ttf", "courbd.ttf"] + candidatas
    for nombre in candidatas:
        try:
            return ImageFont.truetype(nombre, tamano)
        except OSError:
            continue
    return ImageFont.load_default(size=tamano)


def renderizar_consola(texto: str, salida: Path, titulo: str = "",
                       ancho_caracteres: int = 118) -> bool:
    """Convierte la salida real de un comando en una imagen tipo terminal."""
    from PIL import Image, ImageDraw

    salida.parent.mkdir(parents=True, exist_ok=True)
    tamano = 17
    fuente = _fuente_mono(tamano)
    fuente_negrita = _fuente_mono(tamano + 2, negrita=True)

    lineas = []
    for linea in texto.replace("\t", "    ").rstrip("\n").split("\n"):
        while len(linea) > ancho_caracteres:
            lineas.append(linea[:ancho_caracteres])
            linea = linea[ancho_caracteres:]
        lineas.append(linea)

    alto_linea = tamano + 7
    margen = 26
    alto = margen * 2 + alto_linea * (len(lineas) + (2 if titulo else 0)) + 10
    lienzo = Image.new("RGB", (1180, max(260, alto)), "#0b0f16")
    dibujo = ImageDraw.Draw(lienzo)

    # barra de titulo de la ventana
    dibujo.rectangle([0, 0, 1180, 34], fill="#161f31")
    for indice, color in enumerate(("#ef4444", "#f59e0b", "#22c55e")):
        cx = 20 + indice * 20
        dibujo.ellipse([cx - 6, 11, cx + 6, 23], fill=color)
    if titulo:
        dibujo.text((100, 9), titulo, font=_fuente_mono(14), fill="#93a4c0")

    y = 46
    dibujo.text((margen, y), "$ " + (titulo or "centinela"), font=fuente_negrita,
                fill="#38bdf8")
    y += alto_linea * 1.4

    for linea in lineas:
        color = "#e8eef8"
        if linea.startswith("[") or linea.startswith("---"):
            color = "#7dd3fc"
        elif "OK" in linea or "aprobadas" in linea.lower():
            color = "#86efac"
        elif "FALLA" in linea or "ERROR" in linea or "CRITICO" in linea.upper():
            color = "#fca5a5"
        dibujo.text((margen, y), linea, font=fuente, fill=color)
        y += alto_linea

    dibujo.rectangle([0, lienzo.height - 4, 1180, lienzo.height], fill="#38bdf8")
    lienzo.save(salida)
    log("%s  (%.0f KB)" % (salida.name, salida.stat().st_size / 1024))
    return True


def salida_cli(argumentos) -> str:
    """Ejecuta la CLI en proceso y devuelve lo que imprime de verdad."""
    from backend import cli as cli_mod

    parser = cli_mod.construir_parser()
    args = parser.parse_args(argumentos)
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        asyncio.run(cli_mod.ejecutar(args))
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Orquestacion
# ---------------------------------------------------------------------------
async def tomar_capturas(args):
    from backend import config as config_mod
    from backend.main import Backend, cargar_seed
    from backend.web.app import SERVICIOS
    from scripts.demo import PuenteLoopback, limpiar_base, esperar_nodo_conectado
    from scripts.emular_nodo import ClienteLoopback, NodoEmulado

    navegador = encontrar_navegador()
    if navegador is None:
        log("no se encontro Chrome ni Edge; se omiten las capturas del panel")
        return False

    cfg = config_mod.cargar().con(puerto=args.puerto, sin_login=True)
    limpiar_base(cfg.ruta_bd)
    cargar_seed(cfg)

    backend = Backend(cfg, sin_mqtt=True, logger=log)
    puente = PuenteLoopback()
    canal = ClienteLoopback()
    backend.puente = puente
    backend.comandos.puente = puente
    backend.app[SERVICIOS]["puente"] = puente
    await backend.arrancar()
    canal.hacia_backend = backend._procesar
    puente.canal = canal

    nodo = NodoEmulado(cliente=canal, escenario="intruso", salida_s=4,
                       log=lambda mensaje: None)
    tarea = asyncio.create_task(nodo.ejecutar())
    url = "http://%s:%d" % (cfg.host, cfg.puerto)

    try:
        await asyncio.sleep(4)
        await capturar_pagina(navegador, url + "/?estatico=1",
                              DESTINO / "01_panel_estado.png")

        await esperar_nodo_conectado(backend, nodo, 10)
        resultado = await backend.comandos.ejecutar("arm", {}, source="capturas")
        log("armado: ok=%s" % resultado.get("ok"))

        # esperar la alarma (el escenario intruso la provoca solo)
        fin = time.time() + 60
        while time.time() < fin and nodo.maquina.estado != "ALARM":
            await asyncio.sleep(0.3)
        if nodo.maquina.estado == "ALARM":
            log("alarma detectada; capturando el panel en alarma")
            await asyncio.sleep(1.5)
            await capturar_pagina(navegador, url + "/?estatico=1",
                                  DESTINO / "02_panel_alarma.png")
        else:
            log("no se alcanzo el estado de alarma en el tiempo previsto")
    finally:
        tarea.cancel()
        with contextlib.suppress(Exception):
            await nodo.controlador.detener()
        await backend.detener()

    # pagina de login: se levanta un servidor con autenticacion en otro puerto
    await _capturar_login(args, navegador)
    return True


async def _capturar_login(args, navegador):
    from aiohttp import web

    from backend import config as config_mod
    from backend.bus import Hub
    from backend.storage import Almacen
    from backend.web.app import crear_app

    cfg = config_mod.cargar().con(puerto=args.puerto + 1, sin_login=False)
    almacen = Almacen(cfg.ruta_bd)
    await almacen.abrir()

    class PuenteNulo:
        conectado = False

        def publicar(self, *a, **k):
            return False

        def estado(self):
            return {"conectado": False, "host": "-", "puerto": 0, "tls": False,
                    "recibidos": 0, "enviados": 0, "error": None}

    class ComandosNulos:
        def pendientes(self):
            return 0

        async def ejecutar(self, *a, **k):
            return {"ok": False, "motivo": "sin_nodo"}

    class NubeNula:
        def estado(self):
            return {"activa": False, "talkback": False, "canal": None,
                    "enviados": 0, "errores": 0, "omitidos": 0,
                    "ultimo_entry": None, "comandos_recibidos": 0, "error": None}

    app = crear_app(cfg, almacen, Hub(), ComandosNulos(), NubeNula(),
                    PuenteNulo(), log=lambda m: None, version="2.0.0")
    runner = web.AppRunner(app)
    await runner.setup()
    sitio = web.TCPSite(runner, cfg.host, cfg.puerto)
    await sitio.start()
    try:
        await asyncio.sleep(0.5)
        await capturar_pagina(navegador,
                              "http://%s:%d/login" % (cfg.host, cfg.puerto),
                              DESTINO / "03_login.png", ancho=1200, alto=900)
    finally:
        await runner.cleanup()
        await almacen.cerrar()


def tomar_capturas_consola():
    destinos = [
        (["historico", "--horas", "6", "--limite", "18"],
         "04_cli_historico.png", "python -m backend.cli historico --horas 6"),
        (["eventos", "--limite", "12"],
         "05_cli_eventos.png", "python -m backend.cli eventos"),
        (["estadisticas"],
         "06_cli_estadisticas.png", "python -m backend.cli estadisticas"),
        (["comandos", "--limite", "10"],
         "07_cli_comandos.png", "python -m backend.cli comandos"),
    ]
    for argumentos, archivo, titulo in destinos:
        try:
            texto = salida_cli(argumentos)
        except Exception as exc:  # noqa: BLE001
            log("no se pudo generar %s: %s" % (archivo, exc))
            continue
        renderizar_consola(texto, DESTINO / archivo, titulo=titulo)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Capturas de evidencia")
    parser.add_argument("--puerto", type=int, default=8020)
    parser.add_argument("--solo-panel", action="store_true")
    parser.add_argument("--solo-consola", action="store_true")
    args = parser.parse_args(argv)

    DESTINO.mkdir(parents=True, exist_ok=True)
    if not args.solo_consola:
        asyncio.run(tomar_capturas(args))
    if not args.solo_panel:
        tomar_capturas_consola()
    return 0


if __name__ == "__main__":
    sys.exit(main())
