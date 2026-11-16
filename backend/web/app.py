"""Aplicacion web (aiohttp): API REST, panel en tiempo real y login.

El panel consume:
  * REST  -> estado, historico, eventos, comandos, estadisticas
  * SSE   -> /api/stream para las actualizaciones en vivo

Todas las rutas de datos exigen sesion valida salvo en modo demostracion.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from aiohttp import web

from . import auth

ESTATICOS = Path(__file__).resolve().parent / "static"

# Claves tipadas de la aplicacion (evita los avisos de aiohttp)
CFG = web.AppKey("cfg", object)
LOG = web.AppKey("log", object)
SERVICIOS = web.AppKey("servicios", object)

SEGURIDAD_PUBLICA = (
    "/login",
    "/healthz",
)


def _json(datos, estado: int = 200) -> web.Response:
    return web.json_response(datos, status=estado,
                             dumps=lambda o: json.dumps(o, ensure_ascii=False))


def _html(nombre: str) -> web.Response:
    ruta = ESTATICOS / nombre
    if not ruta.exists():
        return web.Response(text="No encontrado", status=404)
    return web.Response(text=ruta.read_text(encoding="utf-8"),
                        content_type="text/html", charset="utf-8")


def _servicios(request: web.Request) -> dict:
    return request.app[SERVICIOS]


# ---------------------------------------------------------------------------
# Middleware de sesion
# ---------------------------------------------------------------------------
@web.middleware
async def middleware_sesion(request: web.Request, handler):
    cfg = request.app[CFG]
    ruta = request.path

    if ruta.startswith("/static") or ruta in SEGURIDAD_PUBLICA:
        return await handler(request)

    if cfg.sin_login:
        return await handler(request)

    token = request.cookies.get(auth.NOMBRE_COOKIE)
    payload = auth.verificar_token(token, cfg.secreto)
    if payload is None:
        if ruta.startswith("/api/"):
            return _json({"error": "no_autorizado"}, 401)
        raise web.HTTPFound("/login")

    return await handler(request)


@web.middleware
async def middleware_errores(request: web.Request, handler):
    try:
        return await handler(request)
    except web.HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        request.app[LOG]("error no controlado en %s: %s" % (request.path, exc))
        return _json({"error": "error_interno", "detalle": str(exc)}, 500)


# ---------------------------------------------------------------------------
# Paginas
# ---------------------------------------------------------------------------
async def pagina_panel(request: web.Request) -> web.Response:
    return _html("index.html")


async def pagina_login(request: web.Request) -> web.Response:
    if request.app[CFG].sin_login:
        raise web.HTTPFound("/")
    return _html("login.html")


async def entrar(request: web.Request) -> web.Response:
    cfg = request.app[CFG]
    datos = await request.post()
    usuario = str(datos.get("usuario", ""))
    clave = str(datos.get("clave", ""))

    if not auth.credenciales_validas(usuario, clave, cfg):
        request.app[LOG]("login fallido para '%s'" % usuario)
        raise web.HTTPFound("/login?error=1")

    respuesta = web.HTTPFound("/")
    respuesta.set_cookie(
        auth.NOMBRE_COOKIE,
        auth.crear_token(usuario, cfg.secreto),
        max_age=auth.DURACION_S,
        httponly=True,
        samesite="Lax",
        path="/",
    )
    request.app[LOG]("login correcto de '%s'" % usuario)
    raise respuesta


async def salir(request: web.Request) -> web.Response:
    respuesta = web.HTTPFound("/login")
    respuesta.del_cookie(auth.NOMBRE_COOKIE, path="/")
    raise respuesta


async def salud(request: web.Request) -> web.Response:
    servicios = _servicios(request)
    return _json({
        "ok": True,
        "hora_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mqtt": bool(servicios["puente"].conectado),
        "clientes_sse": servicios["hub"].clientes(),
    })


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
async def api_estado(request: web.Request) -> web.Response:
    servicios = _servicios(request)
    cfg = request.app[CFG]
    almacen = servicios["almacen"]

    lectura = await almacen.ultima_lectura(cfg.device_id)
    dispositivos = await almacen.dispositivos()
    comandos = await almacen.estado_comandos()

    estado_seguridad = "DESCONOCIDO"
    if lectura and lectura.get("state"):
        estado_seguridad = lectura["state"]

    return _json({
        "dispositivo": dispositivos[0] if dispositivos else None,
        "lectura": lectura,
        "estado_seguridad": estado_seguridad,
        "alertas": (lectura or {}).get("alerts", 0),
        "mqtt": servicios["puente"].estado(),
        "nube": servicios["nube"].estado(),
        "comandos": comandos,
        "comandos_pendientes": servicios["comandos"].pendientes(),
        "clientes_sse": servicios["hub"].clientes(),
        "sin_login": cfg.sin_login,
        "version": servicios.get("version", ""),
        "hora_servidor_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })


async def api_lecturas(request: web.Request) -> web.Response:
    servicios = _servicios(request)
    cfg = request.app[CFG]
    horas = _flotante(request.query.get("horas"), 6.0, 0.1, 720.0)
    limite = _entero(request.query.get("limite"), 400, 10, 5000)
    series = await servicios["almacen"].historico(cfg.device_id, horas, limite)
    agregados = await servicios["almacen"].agregado_horario(cfg.device_id,
                                                            min(horas, 72.0))
    return _json({"series": series, "agregados": agregados,
                  "horas": horas, "total": len(series)})


async def api_eventos(request: web.Request) -> web.Response:
    servicios = _servicios(request)
    cfg = request.app[CFG]
    limite = _entero(request.query.get("limite"), 40, 1, 500)
    severidad = request.query.get("severidad") or None
    eventos = await servicios["almacen"].eventos(cfg.device_id, limite, severidad)
    return _json({"eventos": eventos, "total": len(eventos)})


async def api_comandos(request: web.Request) -> web.Response:
    servicios = _servicios(request)
    limite = _entero(request.query.get("limite"), 25, 1, 200)
    comandos = await servicios["almacen"].comandos(limite)
    return _json({"comandos": comandos, "total": len(comandos)})


async def api_estadisticas(request: web.Request) -> web.Response:
    servicios = _servicios(request)
    cfg = request.app[CFG]
    datos = await servicios["almacen"].estadisticas(cfg.device_id)
    return _json(datos)


async def api_comando(request: web.Request) -> web.Response:
    servicios = _servicios(request)
    try:
        cuerpo = await request.json()
    except (json.JSONDecodeError, ValueError):
        return _json({"ok": False, "motivo": "json_invalido"}, 400)

    if not isinstance(cuerpo, dict):
        return _json({"ok": False, "motivo": "json_invalido"}, 400)

    cmd = str(cuerpo.get("cmd", ""))
    args = cuerpo.get("args") or {}
    origen = "panel"

    resultado = await servicios["comandos"].ejecutar(cmd, args, source=origen)
    estado = 200 if resultado.get("ok") else 200
    return _json(resultado, estado)


async def api_estado_seguridad(request: web.Request) -> web.Response:
    servicios = _servicios(request)
    cfg = request.app[CFG]
    cambios = await servicios["almacen"].cambios_estado(cfg.device_id, 30)
    return _json({"cambios": cambios})


async def api_stream(request: web.Request) -> web.StreamResponse:
    """Server-Sent Events: un canal de un solo sentido, sin dependencias."""
    servicios = _servicios(request)
    hub = servicios["hub"]

    respuesta = web.StreamResponse(
        status=200,
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
    await respuesta.prepare(request)

    suscriptor = hub.suscribir()
    try:
        await respuesta.write(b": conectado\n\n")
        while True:
            evento = await suscriptor.siguiente(timeout=15.0)
            if evento is None:
                await respuesta.write(b": ping\n\n")
                continue
            carga = json.dumps(evento["datos"], ensure_ascii=False)
            bloque = "event: %s\ndata: %s\n\n" % (evento["tipo"], carga)
            await respuesta.write(bloque.encode("utf-8"))
    except (asyncio.CancelledError, ConnectionResetError, ConnectionError):
        pass
    finally:
        hub.baja(suscriptor)
    return respuesta


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _entero(valor, defecto: int, minimo: int, maximo: int) -> int:
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return defecto
    return max(minimo, min(maximo, numero))


def _flotante(valor, defecto: float, minimo: float, maximo: float) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return defecto
    return max(minimo, min(maximo, numero))


def crear_app(cfg, almacen, hub, comandos, nube, puente, log=None,
              version: str = "") -> web.Application:
    """Construye la aplicacion con sus dependencias."""
    app = web.Application(middlewares=[middleware_errores, middleware_sesion],
                          client_max_size=64 * 1024)
    app[CFG] = cfg
    app[LOG] = log or (lambda mensaje: print(mensaje))
    app[SERVICIOS] = {
        "almacen": almacen,
        "hub": hub,
        "comandos": comandos,
        "nube": nube,
        "puente": puente,
        "version": version,
    }

    app.router.add_get("/", pagina_panel)
    app.router.add_get("/login", pagina_login)
    app.router.add_post("/login", entrar)
    app.router.add_post("/logout", salir)
    app.router.add_get("/healthz", salud)

    app.router.add_get("/api/estado", api_estado)
    app.router.add_get("/api/lecturas", api_lecturas)
    app.router.add_get("/api/eventos", api_eventos)
    app.router.add_get("/api/comandos", api_comandos)
    app.router.add_get("/api/estadisticas", api_estadisticas)
    app.router.add_get("/api/estado-seguridad", api_estado_seguridad)
    app.router.add_post("/api/comando", api_comando)
    app.router.add_get("/api/stream", api_stream)

    if ESTATICOS.exists():
        app.router.add_static("/static/", ESTATICOS, name="static")

    return app
