"""Pruebas de la API REST y del panel web (aiohttp)."""

from __future__ import annotations

import json

import pytest
from aiohttp.test_utils import TestClient, TestServer

from backend.bus import Hub
from backend.web.app import crear_app


class PuenteFalso:
    conectado = True

    def __init__(self):
        self.enviados: list[tuple] = []

    def publicar(self, topico, payload, qos=1, retain=False):
        self.enviados.append((topico, payload, qos, retain))
        return True

    def estado(self):
        return {"conectado": True, "host": "broker.local", "puerto": 1883,
                "tls": False, "recibidos": 3, "enviados": 2, "error": None}


class NubeFalsa:
    def estado(self):
        return {"activa": False, "talkback": False, "canal": None,
                "enviados": 0, "errores": 0, "omitidos": 0,
                "ultimo_entry": None, "comandos_recibidos": 0, "error": None}


class ComandosFalsos:
    def __init__(self, resultado=None):
        self.llamadas: list[tuple] = []
        self.resultado = resultado or {"ok": True, "id": "abc",
                                       "ack": {"ok": True, "state": "ARMING"}}

    def pendientes(self):
        return 0

    async def ejecutar(self, cmd, args=None, source="panel"):
        self.llamadas.append((cmd, args, source))
        return dict(self.resultado)


@pytest.fixture
async def cliente_web(cfg, almacen, lectura_ejemplo):
    cfg = cfg.con(sin_login=False)
    hub = Hub()
    comandos = ComandosFalsos()
    puente = PuenteFalso()
    app = crear_app(cfg, almacen, hub, comandos, NubeFalsa(), puente,
                    log=lambda m: None, version="prueba")
    servidor = TestServer(app)
    cliente = TestClient(servidor)
    await cliente.start_server()
    try:
        yield cliente, {"cfg": cfg, "almacen": almacen, "hub": hub,
                        "comandos": comandos, "puente": puente}
    finally:
        await cliente.close()


@pytest.fixture
async def cliente_abierto(cfg, almacen):
    cfg = cfg.con(sin_login=True)
    app = crear_app(cfg, almacen, Hub(), ComandosFalsos(), NubeFalsa(),
                    PuenteFalso(), log=lambda m: None, version="prueba")
    servidor = TestServer(app)
    cliente = TestClient(servidor)
    await cliente.start_server()
    try:
        yield cliente
    finally:
        await cliente.close()


async def iniciar_sesion(cliente, cfg):
    return await cliente.post("/login",
                              data={"usuario": cfg.usuario, "clave": cfg.clave},
                              allow_redirects=False)


class TestAutenticacion:
    async def test_pagina_de_login(self, cliente_web):
        cliente, _ = cliente_web
        respuesta = await cliente.get("/login")
        assert respuesta.status == 200
        assert "CENTINELA" in (await respuesta.text()).upper()

    async def test_panel_sin_sesion_redirige(self, cliente_web):
        cliente, _ = cliente_web
        respuesta = await cliente.get("/", allow_redirects=False)
        assert respuesta.status == 302
        assert respuesta.headers["Location"] == "/login"

    async def test_api_sin_sesion_devuelve_401(self, cliente_web):
        cliente, _ = cliente_web
        respuesta = await cliente.get("/api/estado", allow_redirects=False)
        assert respuesta.status == 401

    async def test_login_incorrecto(self, cliente_web):
        cliente, datos = cliente_web
        respuesta = await cliente.post(
            "/login", data={"usuario": "admin", "clave": "mal"},
            allow_redirects=False)
        assert respuesta.status == 302
        assert "error=1" in respuesta.headers["Location"]

    async def test_login_correcto_abre_el_panel(self, cliente_web):
        cliente, datos = cliente_web
        respuesta = await iniciar_sesion(cliente, datos["cfg"])
        assert respuesta.status == 302
        assert respuesta.headers["Location"] == "/"
        assert cliente.session.cookie_jar

        panel = await cliente.get("/")
        assert panel.status == 200
        assert "CENTINELA" in await panel.text()

        api = await cliente.get("/api/estado")
        assert api.status == 200

    async def test_logout(self, cliente_web):
        cliente, datos = cliente_web
        await iniciar_sesion(cliente, datos["cfg"])
        respuesta = await cliente.post("/logout", allow_redirects=False)
        assert respuesta.status == 302
        assert respuesta.headers["Location"] == "/login"

    async def test_modo_sin_login(self, cliente_abierto):
        respuesta = await cliente_abierto.get("/")
        assert respuesta.status == 200
        estado = await cliente_abierto.get("/api/estado")
        assert estado.status == 200


class TestApi:
    async def test_estado_incluye_servicios(self, cliente_web, lectura_ejemplo):
        cliente, datos = cliente_web
        await iniciar_sesion(cliente, datos["cfg"])
        await datos["almacen"].guardar_lectura("dev01", lectura_ejemplo)
        respuesta = await cliente.get("/api/estado")
        cuerpo = await respuesta.json()
        assert cuerpo["estado_seguridad"] == "ARMED"
        assert cuerpo["mqtt"]["conectado"] is True
        assert cuerpo["nube"]["activa"] is False
        assert cuerpo["lectura"]["temp_c"] == pytest.approx(24.6)
        assert cuerpo["dispositivo"]["device_id"] == "dev01"

    async def test_lecturas_por_rango(self, cliente_web, lectura_ejemplo):
        cliente, datos = cliente_web
        await iniciar_sesion(cliente, datos["cfg"])
        for _ in range(3):
            await datos["almacen"].guardar_lectura("dev01", lectura_ejemplo)
        respuesta = await cliente.get("/api/lecturas?horas=6")
        cuerpo = await respuesta.json()
        assert cuerpo["total"] == 3
        assert len(cuerpo["series"]) == 3
        assert "agregados" in cuerpo

    async def test_eventos(self, cliente_web):
        cliente, datos = cliente_web
        await iniciar_sesion(cliente, datos["cfg"])
        await datos["almacen"].registrar_evento("dev01", "intrusion", "Alerta",
                                                "critical")
        cuerpo = await (await cliente.get("/api/eventos?limite=5")).json()
        assert cuerpo["total"] == 1
        assert cuerpo["eventos"][0]["severity"] == "critical"

    async def test_eventos_por_severidad(self, cliente_web):
        cliente, datos = cliente_web
        await iniciar_sesion(cliente, datos["cfg"])
        await datos["almacen"].registrar_evento("dev01", "state", "info 1", "info")
        await datos["almacen"].registrar_evento("dev01", "intrusion", "crit", "critical")
        cuerpo = await (await cliente.get("/api/eventos?severidad=critical")).json()
        assert cuerpo["total"] == 1

    async def test_comandos(self, cliente_web):
        cliente, datos = cliente_web
        await iniciar_sesion(cliente, datos["cfg"])
        await datos["almacen"].crear_comando("abc", "dev01", "arm", {}, "panel")
        cuerpo = await (await cliente.get("/api/comandos")).json()
        assert cuerpo["comandos"][0]["cmd"] == "arm"

    async def test_estadisticas(self, cliente_web, lectura_ejemplo):
        cliente, datos = cliente_web
        await iniciar_sesion(cliente, datos["cfg"])
        await datos["almacen"].guardar_lectura("dev01", lectura_ejemplo)
        cuerpo = await (await cliente.get("/api/estadisticas")).json()
        assert cuerpo["total"] == 1

    async def test_historial_de_estados(self, cliente_web):
        cliente, datos = cliente_web
        await iniciar_sesion(cliente, datos["cfg"])
        await datos["almacen"].registrar_cambio_estado("dev01", "DISARMED",
                                                       "ARMING", "arm")
        cuerpo = await (await cliente.get("/api/estado-seguridad")).json()
        assert cuerpo["cambios"][0]["hacia"] == "ARMING"

    async def test_enviar_comando(self, cliente_web):
        cliente, datos = cliente_web
        await iniciar_sesion(cliente, datos["cfg"])
        respuesta = await cliente.post("/api/comando",
                                       json={"cmd": "arm", "args": {}})
        cuerpo = await respuesta.json()
        assert cuerpo["ok"] is True
        assert datos["comandos"].llamadas == [("arm", {}, "panel")]

    async def test_comando_json_invalido(self, cliente_web):
        cliente, datos = cliente_web
        await iniciar_sesion(cliente, datos["cfg"])
        respuesta = await cliente.post("/api/comando", data="{no json")
        assert respuesta.status == 400

    async def test_comando_rechazado_por_el_nodo(self, cfg, almacen):
        app = crear_app(cfg.con(sin_login=True), almacen, Hub(),
                        ComandosFalsos({"ok": False, "motivo": "timeout"}),
                        NubeFalsa(), PuenteFalso(), log=lambda m: None)
        cliente = TestClient(TestServer(app))
        await cliente.start_server()
        try:
            cuerpo = await (await cliente.post("/api/comando",
                                               json={"cmd": "arm"})).json()
            assert cuerpo["ok"] is False
            assert cuerpo["motivo"] == "timeout"
        finally:
            await cliente.close()

    async def test_salud(self, cliente_web):
        cliente, _ = cliente_web
        respuesta = await cliente.get("/healthz")
        assert respuesta.status == 200
        cuerpo = await respuesta.json()
        assert cuerpo["ok"] is True

    async def test_estaticos(self, cliente_web):
        cliente, _ = cliente_web
        respuesta = await cliente.get("/static/styles.css")
        assert respuesta.status == 200
        assert "text/css" in respuesta.headers["Content-Type"]

    async def test_sse_abre_el_canal(self, cliente_web):
        import asyncio

        cliente, datos = cliente_web
        await iniciar_sesion(cliente, datos["cfg"])
        respuesta = await cliente.get("/api/stream")
        assert respuesta.status == 200
        assert respuesta.headers["Content-Type"].startswith("text/event-stream")
        linea = await asyncio.wait_for(respuesta.content.readline(), 3)
        assert linea.startswith(b":")
        respuesta.close()
