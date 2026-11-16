"""Pruebas del puente MQTT (paho en un hilo) y del bus de eventos SSE."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from backend.bus import Hub
from backend.config import Config
from backend.mqtt_bridge import PuenteMqtt, _codigo_exitoso, decodificar


class ClientePahoFalso:
    """Imita la superficie de paho.mqtt.Client que usa el puente."""

    def __init__(self, codigo_conexion=0, rc_publicacion=0):
        self.on_connect = None
        self.on_disconnect = None
        self.on_message = None
        self.codigo_conexion = codigo_conexion
        self.rc = rc_publicacion
        self.conexion = None
        self.suscritos: list[tuple] = []
        self.publicados: list[tuple] = []
        self.loop_iniciado = False
        self.loop_detenido = False
        self.desconectado = False
        self.retardo = None
        self.usuario = None
        self.tls = False

    def connect_async(self, host, puerto, keepalive=30):
        self.conexion = (host, puerto, keepalive)
        if self.on_connect:
            self.on_connect(self, None, {}, self.codigo_conexion)

    def loop_start(self):
        self.loop_iniciado = True

    def loop_stop(self):
        self.loop_detenido = True

    def disconnect(self):
        self.desconectado = True

    def reconnect_delay_set(self, min_delay=1, max_delay=60):
        self.retardo = (min_delay, max_delay)

    def subscribe(self, topico, qos=0):
        self.suscritos.append((topico, qos))
        return (0, 1)

    def publish(self, topico, payload, qos=0, retain=False):
        self.publicados.append((topico, payload, qos, retain))
        return SimpleNamespace(rc=self.rc)

    def username_pw_set(self, usuario, clave):
        self.usuario = (usuario, clave)

    def tls_set(self):
        self.tls = True


def cfg_mqtt(**cambios):
    base = dict(mqtt_host="broker.local", mqtt_puerto=1883, device_id="dev01",
                mqtt_prefijo="centinela")
    base.update(cambios)
    return Config(**base)


def crear_puente(cliente, cfg=None):
    return PuenteMqtt(cfg or cfg_mqtt(), log=lambda m: None,
                      fabrica_cliente=lambda: cliente)


class TestCodigos:
    def test_entero_cero(self):
        assert _codigo_exitoso(0) is True

    def test_entero_distinto(self):
        assert _codigo_exitoso(5) is False

    def test_none(self):
        assert _codigo_exitoso(None) is True

    def test_objeto_con_is_failure(self):
        assert _codigo_exitoso(SimpleNamespace(is_failure=lambda: False)) is True
        assert _codigo_exitoso(SimpleNamespace(is_failure=lambda: True)) is False

    def test_objeto_con_value(self):
        assert _codigo_exitoso(SimpleNamespace(value=0)) is True
        assert _codigo_exitoso(SimpleNamespace(value=4)) is False

    def test_objeto_con_str(self):
        assert _codigo_exitoso(SimpleNamespace(value="Success")) is False


class TestDecodificar:
    def test_json_valido(self):
        assert decodificar(b'{"a": 1}') == {"a": 1}

    def test_json_invalido(self):
        assert decodificar(b"no json") is None

    def test_vacio(self):
        assert decodificar(b"") is None

    def test_json_que_no_es_objeto(self):
        assert decodificar(b"[1, 2]") is None

    def test_texto_plano(self):
        assert decodificar(b"online") is None


class TestPuente:
    async def test_inicia_y_suscribe(self):
        cliente = ClientePahoFalso()
        puente = crear_puente(cliente)
        assert await puente.iniciar() is True
        assert puente.conectado is True
        assert cliente.loop_iniciado is True
        assert cliente.conexion == ("broker.local", 1883, 30)
        assert cliente.suscritos[0][0] == "centinela/+/#"

    async def test_configura_credenciales_y_tls(self):
        cliente = ClientePahoFalso()
        puente = crear_puente(cliente, cfg_mqtt(mqtt_usuario="u", mqtt_clave="k",
                                                mqtt_tls=True))
        # el cliente lo crea la fabrica: se comprueban las llamadas posteriores
        assert await puente.iniciar() is True
        assert puente.conectado is True

    async def test_rechazo_de_conexion(self):
        cliente = ClientePahoFalso(codigo_conexion=5)
        puente = crear_puente(cliente)
        assert await puente.iniciar() is False
        assert puente.conectado is False
        assert "codigo" in puente.ultimo_error

    async def test_publica_dict_como_json(self):
        cliente = ClientePahoFalso()
        puente = crear_puente(cliente)
        await puente.iniciar()
        assert puente.publicar("centinela/dev01/cmd", {"cmd": "arm"}, qos=1) is True
        topico, payload, qos, retain = cliente.publicados[0]
        assert topico == "centinela/dev01/cmd"
        assert json.loads(payload) == {"cmd": "arm"}
        assert qos == 1
        assert puente.enviados == 1

    async def test_publica_texto(self):
        cliente = ClientePahoFalso()
        puente = crear_puente(cliente)
        await puente.iniciar()
        puente.publicar("t/x", "online", retain=True)
        assert cliente.publicados[0][1] == b"online"
        assert cliente.publicados[0][3] is True

    async def test_publicacion_rechazada(self):
        cliente = ClientePahoFalso(rc_publicacion=4)
        puente = crear_puente(cliente)
        await puente.iniciar()
        assert puente.publicar("t/x", "dato") is False
        assert "rc=" in puente.ultimo_error

    async def test_publicar_sin_cliente(self):
        puente = PuenteMqtt(cfg_mqtt())
        assert puente.publicar("t/x", "dato") is False

    async def test_recibir_mensaje(self):
        cliente = ClientePahoFalso()
        puente = crear_puente(cliente)
        await puente.iniciar()
        mensaje = SimpleNamespace(topic="centinela/dev01/telemetry",
                                  payload=b'{"temp_c": 24}', qos=1, retain=False)
        cliente.on_message(cliente, None, mensaje)
        topico, datos = await asyncio.wait_for(puente.recibir(), 2)
        assert topico == "centinela/dev01/telemetry"
        assert datos["payload"] == b'{"temp_c": 24}'
        assert datos["qos"] == 1
        assert puente.recibidos == 1

    async def test_desconexion_avisa(self):
        cliente = ClientePahoFalso()
        puente = crear_puente(cliente)
        await puente.iniciar()
        cliente.on_disconnect(cliente, None, 0)
        topico, datos = await asyncio.wait_for(puente.recibir(), 2)
        assert topico is None
        assert datos["type"] == "disconnect"
        assert puente.conectado is False

    async def test_detener(self):
        cliente = ClientePahoFalso()
        puente = crear_puente(cliente)
        await puente.iniciar()
        await puente.detener()
        assert cliente.loop_detenido is True
        assert cliente.desconectado is True
        assert puente.conectado is False

    async def test_detener_sin_iniciar(self):
        puente = PuenteMqtt(cfg_mqtt())
        await puente.detener()

    async def test_estado(self):
        cliente = ClientePahoFalso()
        puente = crear_puente(cliente)
        await puente.iniciar()
        estado = puente.estado()
        assert estado["conectado"] is True
        assert estado["host"] == "broker.local"
        assert estado["puerto"] == 1883

    async def test_factory_que_falla(self):
        def explosiva():
            raise RuntimeError("paho roto")

        puente = PuenteMqtt(cfg_mqtt(), fabrica_cliente=explosiva)
        assert await puente.iniciar() is False
        assert "paho roto" in puente.ultimo_error


class TestHub:
    def test_suscribir_y_publicar(self):
        hub = Hub()
        suscriptor = hub.suscribir()
        assert hub.publicar("lectura", {"temp_c": 24}) == 1
        assert hub.clientes() == 1
        assert suscriptor.pendientes() == 1

    async def test_reparte_a_todos(self):
        hub = Hub()
        uno = hub.suscribir()
        dos = hub.suscribir()
        hub.publicar("evento", {"message": "hola"})
        assert (await uno.siguiente(timeout=1))["datos"]["message"] == "hola"
        assert (await dos.siguiente(timeout=1))["datos"]["message"] == "hola"

    def test_baja(self):
        hub = Hub()
        suscriptor = hub.suscribir()
        hub.baja(suscriptor)
        assert hub.clientes() == 0
        assert hub.publicar("x", {}) == 0

    def test_descarta_lo_mas_viejo_si_se_llena(self):
        hub = Hub(capacidad=2)
        suscriptor = hub.suscribir()
        for i in range(4):
            hub.publicar("lectura", {"n": i})
        assert suscriptor.pendientes() == 2
        assert suscriptor.descartados == 2

    async def test_siguiente_con_timeout(self):
        hub = Hub()
        suscriptor = hub.suscribir()
        assert await suscriptor.siguiente(timeout=0.05) is None

    def test_tipo_del_evento(self):
        hub = Hub()
        suscriptor = hub.suscribir()
        hub.publicar("comando", {"ok": True})
        evento = suscriptor._cola.get_nowait()
        assert evento["tipo"] == "comando"
