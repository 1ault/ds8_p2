"""Captura un proyecto publico de Wokwi con un navegador headless.

No usa credenciales: solo abre la pagina del proyecto, pulsa Play, interactua
con los componentes (boton y PIR) y toma capturas del circuito, del monitor
serie y del OLED en los estados ARMADO y ALARMA.

Requisitos:
  * Chrome o Edge instalado.
  * El proyecto debe ser publico (boton Share -> enlace).
  * El navegador necesita acceso pleno al sistema (abre pipes IPC), por eso el
    script debe ejecutarse fuera del sandbox de archivos restrictivo.

Uso:
    python scripts/capturar_wokwi.py --url https://wokwi.com/projects/XXXX
    python scripts/capturar_wokwi.py --url ... --salida docs/capturas
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

NAVEGADORES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)

# Marcador que aparece en el monitor serie del firmware
MARCADOR_SERIE = "[centinela]"


def log(mensaje):
    print("[wokwi] %s" % mensaje, flush=True)


def encontrar_navegador() -> str | None:
    for ruta in NAVEGADORES:
        if Path(ruta).exists():
            return ruta
    for nombre in ("chrome", "msedge", "chromium"):
        encontrado = shutil.which(nombre)
        if encontrado:
            return encontrado
    return None


class Navegador:
    """Sesion minima de DevTools Protocol sobre Chrome headless."""

    def __init__(self, ejecutable: str, puerto: int = 9450, ancho: int = 1680,
                 alto: int = 1050):
        self.ejecutable = ejecutable
        self.puerto = puerto
        self.ancho = ancho
        self.alto = alto
        self.proceso = None
        self._ws = None
        self._sesion = None
        self._contador = 0

    async def __aenter__(self):
        import aiohttp

        perfil = Path(os.path.abspath(str(RAIZ / ".tmp" / ("wokwi-%d" % self.puerto))))
        shutil.rmtree(perfil, ignore_errors=True)
        perfil.mkdir(parents=True, exist_ok=True)

        self.proceso = subprocess.Popen(
            [
                self.ejecutable,
                "--headless=new",
                "--no-sandbox",
                "--use-gl=swiftshader",
                "--enable-unsafe-swiftshader",
                "--disable-breakpad",
                "--disable-crash-reporter",
                "--disable-extensions",
                # Sin esto el navegador congela la simulacion: la pagina no es
                # visible y se estrangulan temporizadores y animaciones.
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-ipc-flooding-protection",
                "--disable-hang-monitor",
                "--disable-features=CalculateNativeWinOcclusion,Translate,BackForwardCache",
                "--autoplay-policy=no-user-gesture-required",
                "--hide-scrollbars",
                "--no-first-run",
                "--no-default-browser-check",
                "--force-device-scale-factor=1",
                "--user-data-dir=%s" % perfil,
                "--window-size=%d,%d" % (self.ancho, self.alto),
                "--remote-debugging-port=%d" % self.puerto,
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        self._sesion = aiohttp.ClientSession()
        destino = None
        for _ in range(80):
            try:
                async with self._sesion.get(
                        "http://127.0.0.1:%d/json/list" % self.puerto) as resp:
                    destinos = await resp.json(content_type=None)
                paginas = [d for d in destinos if d.get("type") == "page"]
                if paginas:
                    destino = paginas[0]
                    break
            except (aiohttp.ClientError, ValueError, OSError):
                pass
            await asyncio.sleep(0.25)

        if destino is None:
            raise RuntimeError("el navegador no expuso DevTools")

        self._ws = await self._sesion.ws_connect(destino["webSocketDebuggerUrl"],
                                                 max_msg_size=0)
        await self.enviar("Page.enable")
        await self.enviar("Runtime.enable")
        await self.enviar("Emulation.setFocusEmulationEnabled", {"enabled": True})
        await self.enviar("Emulation.setDeviceMetricsOverride", {
            "width": self.ancho, "height": self.alto,
            "deviceScaleFactor": 1, "mobile": False,
        })
        try:
            await self.enviar("Page.setWebLifecycleState", {"state": "active"})
        except RuntimeError:
            pass
        return self

    async def __aexit__(self, *exc):
        try:
            if self._ws is not None:
                await self._ws.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            if self._sesion is not None:
                await self._sesion.close()
        except Exception:  # noqa: BLE001
            pass
        if self.proceso is not None:
            self.proceso.terminate()
            try:
                self.proceso.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proceso.kill()

    async def enviar(self, metodo: str, parametros: dict | None = None) -> dict:
        self._contador += 1
        ident = self._contador
        await self._ws.send_json({"id": ident, "method": metodo,
                                  "params": parametros or {}})
        while True:
            mensaje = await asyncio.wait_for(self._ws.receive_json(), 60)
            if mensaje.get("id") == ident:
                if "error" in mensaje:
                    raise RuntimeError("%s: %s" % (metodo, mensaje["error"]))
                return mensaje

    async def evaluar(self, expresion: str):
        respuesta = await self.enviar("Runtime.evaluate", {
            "expression": expresion, "returnByValue": True, "awaitPromise": True,
        })
        return respuesta.get("result", {}).get("result", {}).get("value")

    async def navegar(self, url: str) -> None:
        await self.enviar("Page.navigate", {"url": url})

    async def capturar(self, salida: Path, recorte: dict | None = None,
                       escala: float = 1.0) -> bool:
        salida.parent.mkdir(parents=True, exist_ok=True)
        parametros = {"format": "png", "captureBeyondViewport": False}
        if recorte:
            parametros["clip"] = {
                "x": max(0.0, recorte["x"]),
                "y": max(0.0, recorte["y"]),
                "width": max(10.0, recorte["w"]),
                "height": max(10.0, recorte["h"]),
                "scale": escala,
            }
        respuesta = await self.enviar("Page.captureScreenshot", parametros)
        datos = respuesta.get("result", {}).get("data")
        if not datos:
            return False
        salida.write_bytes(base64.b64decode(datos))
        log("%s  (%.0f KB)" % (salida.name, salida.stat().st_size / 1024))
        return True

    # -- interaccion -------------------------------------------------------
    async def clic(self, x: float, y: float) -> None:
        for tipo in ("mousePressed", "mouseReleased"):
            await self.enviar("Input.dispatchMouseEvent", {
                "type": tipo, "x": x, "y": y, "button": "left", "clickCount": 1,
            })
            await asyncio.sleep(0.05)

    async def mantener(self, x: float, y: float, ms: int = 500) -> None:
        await self.enviar("Input.dispatchMouseEvent", {
            "type": "mousePressed", "x": x, "y": y, "button": "left",
            "clickCount": 1,
        })
        await asyncio.sleep(ms / 1000.0)
        await self.enviar("Input.dispatchMouseEvent", {
            "type": "mouseReleased", "x": x, "y": y, "button": "left",
            "clickCount": 1,
        })

    async def rect(self, expresion_selector: str) -> dict | None:
        return await self.evaluar(
            """(() => {
                const e = document.querySelector(%s);
                if (!e) return null;
                const r = e.getBoundingClientRect();
                if (r.width < 2 || r.height < 2) return null;
                return {x: r.x, y: r.y, w: r.width, h: r.height};
            })()""" % expresion_selector)


# ---------------------------------------------------------------------------
# Utilidades de la pagina
# ---------------------------------------------------------------------------
JS_PARTES = """
(() => {
  const tags = [...document.querySelectorAll('*')]
    .map(e => e.tagName.toLowerCase())
    .filter(t => /^(wokwi-|board-)/.test(t));
  return [...new Set(tags)];
})()
"""

JS_RECT_UNION = """
(() => {
  const partes = [...document.querySelectorAll('*')].filter(e =>
    /^(wokwi-|board-)/.test(e.tagName.toLowerCase()));
  if (!partes.length) return null;
  let x1 = 1e9, y1 = 1e9, x2 = 0, y2 = 0;
  for (const p of partes) {
    const r = p.getBoundingClientRect();
    if (r.width < 5 || r.height < 5) continue;
    x1 = Math.min(x1, r.x); y1 = Math.min(y1, r.y);
    x2 = Math.max(x2, r.right); y2 = Math.max(y2, r.bottom);
  }
  if (x1 > x2) return null;
  const m = 30;
  return {x: x1 - m, y: y1 - m, w: (x2 - x1) + 2 * m, h: (y2 - y1) + 2 * m};
})()
"""


def js_rect_texto(marcador: str) -> str:
    """Rectangulo del elemento mas pequeno que contiene el texto dado."""
    return """
(() => {
  const marcador = %s;
  const todos = [...document.querySelectorAll('*')].filter(e =>
    (e.textContent || '').includes(marcador) && e.children.length <= 6);
  if (!todos.length) return null;
  let mejor = null, area = 1e18;
  for (const e of todos) {
    const r = e.getBoundingClientRect();
    if (r.width < 40 || r.height < 20) continue;
    if (r.width * r.height < area) { area = r.width * r.height; mejor = r; }
  }
  if (!mejor) return null;
  const m = 12;
  return {x: mejor.x - m, y: mejor.y - m, w: mejor.width + 2 * m, h: mejor.height + 2 * m};
})()
""" % repr(marcador)


def js_rect_boton(texto: str) -> str:
    """Localiza un control por aria-label, title, tooltip o texto visible.

    Se queda con el candidato mas pequeno: los contenedores tambien contienen
    el texto (y en el DOM aparecen antes) pero no responden al clic.
    """
    return """
(() => {
  const buscado = %s.toLowerCase();
  const candidatos = [...document.querySelectorAll('button, [role=button], a, div, span')];
  let mejor = null, area = 1e18;
  for (const c of candidatos) {
    const etiqueta = (
      (c.getAttribute('aria-label') || '') + ' ' +
      (c.getAttribute('title') || '') + ' ' +
      (c.getAttribute('data-tooltip') || '') + ' ' +
      (c.textContent || '')
    ).toLowerCase();
    if (!etiqueta.includes(buscado)) continue;
    const r = c.getBoundingClientRect();
    if (r.width < 8 || r.height < 8 || r.width > 600 || r.height > 200) continue;
    const a = r.width * r.height;
    if (a < area) {
      area = a;
      mejor = {x: r.x + r.width / 2, y: r.y + r.height / 2,
               w: r.width, h: r.height};
    }
  }
  return mejor;
})()
""" % repr(texto)


async def esperar(condicion, limite_s: float, intervalo: float = 0.5):
    fin = time.time() + limite_s
    while time.time() < fin:
        valor = await condicion()
        if valor:
            return valor
        await asyncio.sleep(intervalo)
    return None


async def _contiene(nav, texto: str) -> bool:
    """True si el monitor serie (terminal xterm) ya contiene el texto."""
    contenido = await nav.evaluar(JS_TERMINAL) or ""
    return texto in contenido


async def texto_serie(nav) -> str:
    return await nav.evaluar(JS_TERMINAL) or ""


JS_RELOJ = """
(() => {
  const candidatos = [...document.querySelectorAll('div, span')]
    .map(e => (e.textContent || '').trim())
    .filter(t => /^\\d{2}:\\d{2}\\.\\d{3}$/.test(t));
  if (!candidatos.length) return null;
  const partes = candidatos[0].split(/[:.]/);
  return parseInt(partes[0]) * 60 + parseInt(partes[1]) + parseInt(partes[2]) / 1000;
})()
"""


async def reloj_simulacion(nav):
    """Tiempo de simulacion en segundos (el navegador corre a ~0,4x)."""
    return await nav.evaluar(JS_RELOJ)


async def esperar_simulacion(nav, segundos: float, limite_pared: float = 240.0):
    """Espera N segundos de *simulacion*, no de reloj de pared."""
    inicio = await reloj_simulacion(nav)
    if inicio is None:
        await asyncio.sleep(segundos)
        return
    fin = time.time() + limite_pared
    while time.time() < fin:
        await asyncio.sleep(1.0)
        ahora = await reloj_simulacion(nav)
        if ahora is None:
            return
        if ahora - inicio >= segundos:
            return


class ObservadorMqtt:
    """Lee la telemetria real del nodo para confirmar el estado de seguridad."""

    def __init__(self, host: str, prefijo: str, device: str, log_fn=log):
        self.host = host
        self.topico = "%s/%s/telemetry" % (prefijo, device)
        self._log = log_fn
        self._cliente = None
        self.estado = None
        self.ultima = None
        self.mensajes = 0

    def iniciar(self) -> bool:
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            self._log("paho no disponible: no se puede confirmar por MQTT")
            return False

        def al_conectar(cliente, *args):
            cliente.subscribe(self.topico, qos=0)
            self._log("observando %s" % self.topico)

        def al_recibir(cliente, userdata, mensaje):
            import json

            self.mensajes += 1
            try:
                datos = json.loads(mensaje.payload.decode("utf-8", "replace"))
            except ValueError:
                return
            self.ultima = datos
            self.estado = datos.get("state")

        try:
            cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except (AttributeError, TypeError):
            cliente = mqtt.Client()
        cliente.on_connect = al_conectar
        cliente.on_message = al_recibir
        try:
            cliente.connect(self.host, 1883, 30)
            cliente.loop_start()
        except Exception as exc:  # noqa: BLE001
            self._log("no se pudo observar MQTT: %s" % exc)
            return False
        self._cliente = cliente
        return True

    def detener(self):
        if self._cliente is not None:
            try:
                self._cliente.loop_stop()
                self._cliente.disconnect()
            except Exception:  # noqa: BLE001
                pass
            self._cliente = None

    def publicar(self, comandos: dict) -> bool:
        """Envia un comando al nodo por el topico .../cmd (nube -> dispositivo)."""
        import json

        if self._cliente is None:
            return False
        topico = self.topico.rsplit("/", 1)[0] + "/cmd"
        try:
            self._cliente.publish(topico, json.dumps(comandos), qos=1)
        except Exception as exc:  # noqa: BLE001
            self._log("no se pudo publicar el comando: %s" % exc)
            return False
        self._log("comando enviado a %s: %s" % (topico, comandos.get("cmd")))
        return True


async def esperar_estado(observador: ObservadorMqtt, estados, limite_s: float):
    if observador is None or observador._cliente is None:
        return None
    fin = time.time() + limite_s
    while time.time() < fin:
        if observador.estado in estados:
            return observador.estado
        await asyncio.sleep(0.5)
    return None


# ---------------------------------------------------------------------------
# Secuencia de captura
# ---------------------------------------------------------------------------
JS_TERMINAL = """
(() => {
  const t = document.querySelector('.terminal');
  return t ? t.innerText : '';
})()
"""


async def recorte_circuito(nav) -> dict | None:
    """Union de las partes, sin invadir el panel del monitor serie."""
    circuito = await nav.evaluar(JS_RECT_UNION)
    if circuito is None:
        return None
    terminal = await nav.rect("'.terminal'")
    if terminal is not None:
        limite = terminal["y"] - 4
        alto = min(circuito["y"] + circuito["h"], limite) - circuito["y"]
        if alto > 120:
            circuito["h"] = alto
    return circuito


async def parchear_archivo(nav, nombre: str, contenido: str) -> str:
    """Reemplaza el contenido de un archivo usando la interfaz del editor.

    Abre la pestana del archivo, selecciona todo (Ctrl+A) e inserta el texto
    nuevo con `Input.insertText`, que no dispara el auto-indentado de Monaco.
    Solo afecta al editor en memoria: no guarda el proyecto.
    """
    tab = await nav.evaluar(
        """(() => {
            const e = [...document.querySelectorAll('div, span, button, a')]
              .find(x => (x.textContent || '').trim() === %s &&
                         x.getBoundingClientRect().width < 260);
            if (!e) return null;
            e.scrollIntoView({block: 'nearest', inline: 'center'});
            const r = e.getBoundingClientRect();
            return {x: r.x + r.width / 2, y: r.y + r.height / 2};
        })()""" % repr(nombre))
    if tab is None:
        return "sin pestana %s" % nombre

    await nav.clic(tab["x"], tab["y"])
    await asyncio.sleep(1.2)

    vista = await nav.rect("'.monaco-editor'") or await nav.rect(
        "'.monaco-scrollable-element'")
    if vista is None:
        return "sin editor"
    await nav.clic(vista["x"] + 140, vista["y"] + 60)
    await asyncio.sleep(0.6)

    for tipo in ("keyDown", "keyUp"):
        await nav.enviar("Input.dispatchKeyEvent", {
            "type": tipo, "modifiers": 2, "key": "a", "code": "KeyA",
            "windowsVirtualKeyCode": 65, "nativeVirtualKeyCode": 65,
        })
    await asyncio.sleep(0.3)
    await nav.enviar("Input.insertText", {"text": contenido})
    await asyncio.sleep(0.8)

    visible = await nav.evaluar(
        "(document.querySelector('.monaco-editor') || {}).innerText || ''")
    marca = "Y_INICIO"
    return "ok" if marca in (visible or "") else "no confirmado"


async def arrancar_simulacion(nav, intentos: int = 3) -> bool:
    """Pulsa Play hasta que aparezca el terminal del monitor serie."""
    for intento in range(1, intentos + 1):
        if await nav.evaluar("!!document.querySelector('.terminal')"):
            return True
        boton = await esperar(
            lambda: nav.evaluar(js_rect_boton("start the simulation")), 35, 1.0)
        if boton is None:
            log("Play no disponible (intento %d); se reintenta" % intento)
            await asyncio.sleep(3)
            continue
        await nav.clic(boton["x"], boton["y"])
        if await esperar(lambda: nav.evaluar("!!document.querySelector('.terminal')"),
                         25, 0.5):
            log("simulacion iniciada (intento %d)" % intento)
            return True
        log("el terminal no aparecio (intento %d)" % intento)
    return False


async def capturar(url: str, salida: Path, espera_arranque: float,
                   espera_armado: float, sin_contexto: bool,
                   host_mqtt: str = "broker.hivemq.com",
                   prefijo: str = "centinela",
                   device: str = "dev01",
                   parchear: bool = False) -> int:
    ejecutable = encontrar_navegador()
    if ejecutable is None:
        log("no se encontro Chrome ni Edge")
        return 2

    async with Navegador(ejecutable) as nav:
        log("abriendo %s" % url)
        await nav.navegar(url)
        await asyncio.sleep(8)

        titulo = await nav.evaluar("document.title")
        etiquetas = await nav.evaluar(JS_PARTES)
        log("titulo: %s" % titulo)
        log("componentes: %s" % etiquetas)

        if not etiquetas:
            log("la pagina no monto el diagrama (proyecto privado o error)")
            return 3

        # 1.b cargar la version corregida de display.py (solo en el editor)
        if parchear:
            ruta = RAIZ / "firmware" / "display.py"
            if ruta.exists():
                estado = await parchear_archivo(nav, "display.py",
                                               ruta.read_text(encoding="utf-8"))
                log("display.py en el editor: %s" % estado)

        # 1. arrancar la simulacion
        if not await arrancar_simulacion(nav):
            log("no se pudo iniciar la simulacion")
            return 4

        # 2. esperar a que el firmware escriba en el monitor serie
        arrancado = await esperar(
            lambda: _contiene(nav, "[centinela]"), 90, 1.0)
        if arrancado:
            log("el nodo escribe en el monitor serie")
        else:
            log("sin salida del firmware; se continua con la espera fija")
            await asyncio.sleep(espera_arranque)

        observador = ObservadorMqtt(host_mqtt, prefijo, device)
        if not observador.iniciar():
            observador = None

        # 3. dejar que se estabilice y capturar el estado de reposo
        await esperar_simulacion(nav, 4)
        log("estado reportado por el nodo: %s" % (
            observador.estado if observador else "sin MQTT"))

        serie = await nav.rect("'.terminal'")
        if serie:
            await nav.capturar(salida / "wokwi_02_serie.png", serie, 1.6)
        else:
            log("no se encontro el monitor serie")

        if not sin_contexto:
            circuito = await recorte_circuito(nav)
            if circuito:
                await nav.capturar(salida / "wokwi_01_circuito.png", circuito, 1.0)
            else:
                await nav.capturar(salida / "wokwi_01_circuito.png")

        # 4. armar con el pulsador fisico y esperar la cuenta regresiva
        pulsador = await nav.rect("'wokwi-pushbutton'") or await nav.evaluar(
            js_rect_boton("ARMAR / DESARMAR"))
        if pulsador is None:
            log("no se encontro el pulsador")
        else:
            await nav.mantener(pulsador["x"], pulsador["y"], 700)
            log("pulsador accionado")

        confirmado = await esperar_estado(observador, {"ARMING", "ARMED"}, 45)
        log("estado tras pulsar: %s" % confirmado)
        await esperar_simulacion(nav, espera_armado)
        log("estado antes de la captura: %s" % (
            observador.estado if observador else "?"))

        oled = (await nav.rect("'wokwi-ssd1306'")
                or await nav.evaluar(js_rect_texto("ARMADO"))
                or await nav.rect("'board-ssd1306'"))
        if oled:
            await nav.capturar(salida / "wokwi_03_oled_armado.png", oled, 3.0)
        else:
            log("no se pudo localizar el OLED en ARMADO")

        # 5. provocar la alarma con el PIR
        pir = await nav.rect("'wokwi-pir-motion-sensor'")
        if pir is None:
            log("no se encontro el PIR")
        else:
            await nav.clic(pir["x"] + pir["w"] / 2, pir["y"] + pir["h"] / 2)
            await asyncio.sleep(1.5)
            simular = await nav.evaluar(js_rect_boton("simulate motion"))
            if simular is None:
                log("no aparecio el boton 'Simulate Motion'")
            else:
                await nav.clic(simular["x"], simular["y"])
                log("movimiento simulado")

        alarma = await esperar_estado(observador, {"ALARM"}, 40)
        if alarma is None and observador is not None:
            # Plan B: si el popup del PIR no responde, se fuerza una alerta
            # termica bajando el umbral por comando desde la "nube".
            log("el PIR no disparo la alarma; se baja el umbral de temperatura")
            observador.publicar({
                "id": "captura-termica",
                "cmd": "set_config",
                "args": {"temp_alarm_c": 20},
                "source": "capturas",
            })
            alarma = await esperar_estado(observador, {"ALARM"}, 40)
        log("estado de alarma: %s" % alarma)
        await esperar_simulacion(nav, 3)

        oled_alarma = (await nav.rect("'wokwi-ssd1306'")
                       or await nav.evaluar(js_rect_texto("ALARMA")) or oled)
        if oled_alarma:
            await nav.capturar(salida / "wokwi_04_oled_alarma.png", oled_alarma, 3.0)

        circuito_alarma = await recorte_circuito(nav)
        if circuito_alarma:
            await nav.capturar(salida / "wokwi_05_circuito_alarma.png",
                               circuito_alarma, 1.0)


        if observador is not None:
            log("telemetria recibida: %d mensajes; ultimo estado %s" % (
                observador.mensajes, observador.estado))
            if observador.ultima:
                log("ultima lectura: %s" % observador.ultima)
            observador.detener()

        # el monitor serie completo queda en el log para diagnostico
        texto_final = await texto_serie(nav)
        log("--- monitor serie (ultimas lineas) ---")
        for linea in [l for l in texto_final.strip().splitlines() if l.strip()][-22:]:
            log("  " + linea)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Capturas de un proyecto publico de Wokwi")
    parser.add_argument("--url", required=True, help="enlace del proyecto")
    parser.add_argument("--salida", default=str(RAIZ / "docs" / "capturas"))
    parser.add_argument("--espera-arranque", type=float, default=22.0,
                        help="espera de respaldo si no hay salida del nodo")
    parser.add_argument("--espera-armado", type=float, default=12.0,
                        help="segundos de SIMULACION a esperar tras armar")
    parser.add_argument("--sin-contexto", action="store_true",
                        help="no capturar el circuito completo")
    parser.add_argument("--mqtt-host", default="broker.hivemq.com")
    parser.add_argument("--prefijo", default="centinela")
    parser.add_argument("--device", default="dev01")
    parser.add_argument("--parchear", dest="parchear", action="store_true",
                        help="intentar cargar display.py en el editor (experimental)")
    args = parser.parse_args(argv)
    return asyncio.run(capturar(args.url, Path(args.salida),
                                args.espera_arranque, args.espera_armado,
                                args.sin_contexto, args.mqtt_host,
                                args.prefijo, args.device, args.parchear))


if __name__ == "__main__":
    sys.exit(main())
