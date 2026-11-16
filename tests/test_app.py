"""Pruebas del controlador del nodo (integracion de firmware sin hardware)."""

from __future__ import annotations

import asyncio
import json

import actuators
import app as app_mod
import fsm


class ClienteFalso:
    """Cliente MQTT en memoria que registra lo publicado."""

    def __init__(self):
        self.conectado = True
        self.publicados: list[tuple] = []
        self.on_message = None
        self.cerrado = False

    async def publicar(self, topico, payload, qos=0, retain=False):
        self.publicados.append((topico, payload, qos, retain))
        return True

    async def cerrar(self):
        self.cerrado = True
        self.conectado = False

    def por_topico(self, topico):
        return [p for p in self.publicados if p[0] == topico]

    def ultimo(self, topico):
        encontrados = self.por_topico(topico)
        return encontrados[-1][1] if encontrados else None


class WifiFalsa:
    def rssi(self):
        return -55

    def estado(self):
        return {"conectado": True, "ssid": "Wokai-GUEST", "ip": "10.0.0.5",
                "rssi": -55, "intentos": 1}


class PantallaFalsa:
    def __init__(self):
        self.ultimo = None
        self.avisos = []

    def mostrar(self, datos):
        self.ultimo = datos
        return True

    def aviso(self, texto):
        self.avisos.append(texto)
        return True

    def limpiar(self):
        return True


class SuiteFalsa:
    """Sensores controlables desde la prueba."""

    def __init__(self, datos=None):
        self.datos = dict(datos or {})
        self.actuales = dict(self.datos)

    def actualizar(self, ahora=None):
        self.actuales.update(self.datos)
        return dict(self.datos)

    def instantanea(self):
        return dict(self.actuales)

    def total_errores(self):
        return 0


def crear_controlador(cfg_firmware, reloj, suite=None, cliente=None):
    panel = actuators.PanelActuadores(
        actuators.Led(cfg_firmware.PIN_LED_RED, "rojo"),
        actuators.Led(cfg_firmware.PIN_LED_GREEN, "verde"),
        actuators.Buzzer(cfg_firmware.PIN_BUZZER),
        actuators.ServoLock(cfg_firmware.PIN_SERVO),
    )
    return app_mod.Controlador(
        cfg_firmware,
        WifiFalsa(),
        cliente or ClienteFalso(),
        suite or SuiteFalsa(),
        panel,
        PantallaFalsa(),
        fsm.crear_desde_config(cfg_firmware),
        boton=False,
        reloj=reloj,
    )


def leer_json(payload):
    return json.loads(payload) if isinstance(payload, (str, bytes)) else payload


class TestTelemetria:
    def test_incluye_los_campos_del_contrato(self, cfg_firmware, reloj):
        suite = SuiteFalsa({"clima": {"temp_c": 24.6, "hum_pct": 58.0},
                            "luz": 120.0, "distancia": 145.0,
                            "movimiento": False})
        controlador = crear_controlador(cfg_firmware, reloj, suite)
        datos = controlador._telemetria()
        for clave in ("v", "device", "seq", "uptime_s", "temp_c", "hum_pct",
                      "lux", "dist_cm", "motion", "state", "alarm", "siren",
                      "locked", "alerts", "rssi"):
            assert clave in datos
        assert datos["temp_c"] == 24.6
        assert datos["state"] == fsm.DESARMADO

    def test_incrementa_el_secuencial(self, cfg_firmware, reloj):
        controlador = crear_controlador(cfg_firmware, reloj)
        controlador._telemetria()
        assert controlador._telemetria()["seq"] == 2

    async def test_se_publica_en_el_topico_correcto(self, cfg_firmware, reloj):
        cliente = ClienteFalso()
        controlador = crear_controlador(cfg_firmware, reloj, cliente=cliente)
        assert await controlador._publicar_telemetria() is True
        publicado = cliente.por_topico(cfg_firmware.TOPIC_TELEMETRY)
        assert len(publicado) == 1
        assert leer_json(publicado[0][1])["device"] == cfg_firmware.DEVICE_ID

    async def test_sin_conexion_no_publica(self, cfg_firmware, reloj):
        cliente = ClienteFalso()
        cliente.conectado = False
        controlador = crear_controlador(cfg_firmware, reloj, cliente=cliente)
        assert await controlador._publicar_telemetria() is False
        assert cliente.publicados == []


class TestComandos:
    async def test_armar(self, cfg_firmware, reloj):
        cliente = ClienteFalso()
        controlador = crear_controlador(cfg_firmware, reloj, cliente=cliente)
        assert await controlador.procesar_comando({"id": "c1", "cmd": "arm"}) is True
        assert controlador.maquina.estado == fsm.ARMANDO
        ack = leer_json(cliente.ultimo(cfg_firmware.TOPIC_ACK))
        assert ack["ok"] is True
        assert ack["id"] == "c1"

    async def test_desarmar(self, cfg_firmware, reloj):
        controlador = crear_controlador(cfg_firmware, reloj)
        await controlador.procesar_comando({"cmd": "arm"})
        await controlador.procesar_comando({"cmd": "disarm"})
        assert controlador.maquina.estado == fsm.DESARMADO

    async def test_unlock_con_pin_correcto(self, cfg_firmware, reloj):
        cliente = ClienteFalso()
        controlador = crear_controlador(cfg_firmware, reloj, cliente=cliente)
        resultado = await controlador.procesar_comando(
            {"id": "u1", "cmd": "unlock", "args": {"pin": cfg_firmware.UNLOCK_PIN}})
        assert resultado is True
        assert controlador.panel.cerradura.cerrada is False
        assert leer_json(cliente.ultimo(cfg_firmware.TOPIC_ACK))["ok"] is True

    async def test_unlock_con_pin_incorrecto(self, cfg_firmware, reloj):
        cliente = ClienteFalso()
        controlador = crear_controlador(cfg_firmware, reloj, cliente=cliente)
        resultado = await controlador.procesar_comando(
            {"id": "u2", "cmd": "unlock", "args": {"pin": "1111"}})
        assert resultado is False
        ack = leer_json(cliente.ultimo(cfg_firmware.TOPIC_ACK))
        assert ack["ok"] is False
        assert ack["reason"] == "pin_incorrecto"
        assert controlador.panel.cerradura.cerrada is True

    async def test_comando_no_permitido(self, cfg_firmware, reloj):
        cliente = ClienteFalso()
        controlador = crear_controlador(cfg_firmware, reloj, cliente=cliente)
        assert await controlador.procesar_comando({"cmd": "formatear"}) is False
        ack = leer_json(cliente.ultimo(cfg_firmware.TOPIC_ACK))
        assert ack["reason"] == "comando_no_permitido"

    async def test_json_invalido_no_rompe(self, cfg_firmware, reloj):
        cliente = ClienteFalso()
        controlador = crear_controlador(cfg_firmware, reloj, cliente=cliente)
        assert await controlador.procesar_comando(b"{no es json") is None
        eventos = cliente.por_topico(cfg_firmware.TOPIC_EVENTS)
        assert eventos

    async def test_ping_responde(self, cfg_firmware, reloj):
        cliente = ClienteFalso()
        controlador = crear_controlador(cfg_firmware, reloj, cliente=cliente)
        assert await controlador.procesar_comando({"id": "p1", "cmd": "ping"}) is True
        ack = leer_json(cliente.ultimo(cfg_firmware.TOPIC_ACK))
        assert "pong" in ack["result"]

    async def test_set_config_aplica_cambios(self, cfg_firmware, reloj):
        controlador = crear_controlador(cfg_firmware, reloj)
        resultado = await controlador.procesar_comando(
            {"cmd": "set_config",
             "args": {"dist_alarm_cm": 120, "exit_delay_s": 5}})
        assert resultado is True
        assert controlador.maquina.dist_alarma_cm == 120.0
        assert controlador.maquina.salida_s == 5.0

    async def test_set_config_rechaza_fuera_de_rango(self, cfg_firmware, reloj):
        controlador = crear_controlador(cfg_firmware, reloj)
        await controlador.procesar_comando(
            {"cmd": "set_config", "args": {"dist_alarm_cm": 5000}})
        assert controlador.maquina.dist_alarma_cm == cfg_firmware.DIST_ALARM_CM

    async def test_alternar_armado(self, cfg_firmware, reloj):
        controlador = crear_controlador(cfg_firmware, reloj)
        await controlador.alternar_armado("boton")
        assert controlador.maquina.estado == fsm.ARMANDO
        await controlador.alternar_armado("boton")
        assert controlador.maquina.estado == fsm.DESARMADO


class TestCiclo:
    async def _armado(self, controlador, reloj):
        await controlador.procesar_comando({"cmd": "arm"})
        reloj.avanzar(controlador.cfg.EXIT_DELAY_S + 1)
        await controlador._ciclo(reloj())
        assert controlador.maquina.estado == fsm.ARMADO

    async def test_movimiento_dispara_alarma(self, cfg_firmware, reloj):
        suite = SuiteFalsa()
        controlador = crear_controlador(cfg_firmware, reloj, suite)
        await self._armado(controlador, reloj)
        suite.datos = {"movimiento": True}
        await controlador._ciclo(reloj())
        assert controlador.maquina.estado == fsm.ALARMA
        assert controlador.panel.buzzer.activo is True

    async def test_movimiento_sostenido_no_genera_ruido(self, cfg_firmware, reloj):
        suite = SuiteFalsa()
        controlador = crear_controlador(cfg_firmware, reloj, suite)
        await self._armado(controlador, reloj)
        suite.datos = {"movimiento": True}
        await controlador._ciclo(reloj())
        reloj.avanzar(0.2)
        await controlador._ciclo(reloj())
        assert controlador.maquina.alertas == 1

    async def test_presencia_cercana_dispara_alarma(self, cfg_firmware, reloj):
        suite = SuiteFalsa()
        controlador = crear_controlador(cfg_firmware, reloj, suite)
        await self._armado(controlador, reloj)
        suite.datos = {"distancia": 30.0}
        await controlador._ciclo(reloj())
        assert controlador.maquina.estado == fsm.ALARMA

    async def test_temperatura_alta_con_sistema_armado(self, cfg_firmware, reloj):
        suite = SuiteFalsa()
        controlador = crear_controlador(cfg_firmware, reloj, suite)
        await self._armado(controlador, reloj)
        suite.datos = {"clima": {"temp_c": 70.0, "hum_pct": 20.0}}
        await controlador._ciclo(reloj())
        assert controlador.maquina.estado == fsm.ALARMA

    async def test_temperatura_alta_desarmado_solo_avisa(self, cfg_firmware, reloj):
        cliente = ClienteFalso()
        suite = SuiteFalsa({"clima": {"temp_c": 70.0, "hum_pct": 20.0}})
        controlador = crear_controlador(cfg_firmware, reloj, suite, cliente)
        await controlador._ciclo(reloj())
        assert controlador.maquina.estado == fsm.DESARMADO
        mensajes = [leer_json(p[1])["message"] for p in
                    cliente.por_topico(cfg_firmware.TOPIC_EVENTS)]
        assert any("temperatura" in m for m in mensajes)

    async def test_publica_cambio_de_estado(self, cfg_firmware, reloj):
        cliente = ClienteFalso()
        controlador = crear_controlador(cfg_firmware, reloj, cliente=cliente)
        await controlador.procesar_comando({"cmd": "arm"})
        await controlador._detectar_cambio_estado()
        eventos = [leer_json(p[1]) for p in cliente.por_topico(cfg_firmware.TOPIC_EVENTS)]
        cambios = [e for e in eventos if e.get("kind") == "state"
                   and e.get("data", {}).get("to")]
        assert cambios
        assert cambios[-1]["data"]["to"] == fsm.ARMANDO

    async def test_cerradura_se_cierra_al_armar(self, cfg_firmware, reloj):
        controlador = crear_controlador(cfg_firmware, reloj)
        await controlador.procesar_comando(
            {"cmd": "unlock", "args": {"pin": cfg_firmware.UNLOCK_PIN}})
        assert controlador.panel.cerradura.cerrada is False
        await controlador.procesar_comando({"cmd": "arm"})
        assert controlador.panel.cerradura.cerrada is True


class TestRecepcionMqtt:
    async def test_el_comando_entra_al_bus(self, cfg_firmware, reloj):
        controlador = crear_controlador(cfg_firmware, reloj)
        controlador._al_recibir(cfg_firmware.TOPIC_COMMAND,
                                b'{"id": "1", "cmd": "arm"}', 1, False)
        assert controlador._buzon.size() == 1
        evento = await asyncio.wait_for(controlador._buzon.get(), 1)
        assert evento["topico"] == "cmd"
        assert evento["datos"] == b'{"id": "1", "cmd": "arm"}'

    async def test_el_bucle_procesa_lo_recibido(self, cfg_firmware, reloj):
        controlador = crear_controlador(cfg_firmware, reloj)
        tarea = asyncio.create_task(controlador._bucle_comandos())
        controlador._al_recibir(cfg_firmware.TOPIC_COMMAND,
                                b'{"id": "1", "cmd": "arm"}', 1, False)
        for _ in range(50):
            if controlador.maquina.estado == fsm.ARMANDO:
                break
            await asyncio.sleep(0.01)
        tarea.cancel()
        assert controlador.maquina.estado == fsm.ARMANDO

    async def test_config_por_mqtt_se_convierte_en_set_config(self, cfg_firmware, reloj):
        controlador = crear_controlador(cfg_firmware, reloj)
        controlador._al_recibir(cfg_firmware.TOPIC_CONFIG, b'{"exit_delay_s": 3}',
                                1, False)
        evento = await asyncio.wait_for(controlador._buzon.get(), 1)
        assert evento["datos"]["cmd"] == "set_config"
        assert evento["datos"]["args"] == {"exit_delay_s": 3}

    async def test_config_invalida_se_ignora(self, cfg_firmware, reloj):
        controlador = crear_controlador(cfg_firmware, reloj)
        controlador._al_recibir(cfg_firmware.TOPIC_CONFIG, b"{roto", 1, False)
        assert controlador._buzon.size() == 0

    async def test_topicos_ajenos_se_ignoran(self, cfg_firmware, reloj):
        controlador = crear_controlador(cfg_firmware, reloj)
        controlador._al_recibir("otro/dispositivo/cmd", b"x", 0, False)
        assert controlador._buzon.size() == 0


class TestPantalla:
    def test_datos_para_la_pantalla(self, cfg_firmware, reloj):
        suite = SuiteFalsa({"clima": {"temp_c": 21.0, "hum_pct": 40.0},
                            "luz": 10.0, "distancia": 200.0, "movimiento": True})
        controlador = crear_controlador(cfg_firmware, reloj, suite)
        datos = controlador.datos_pantalla()
        for clave in ("state", "temp_c", "hum_pct", "lux", "dist_cm", "motion",
                      "alerts", "siren", "locked", "rssi", "mqtt"):
            assert clave in datos
        assert datos["motion"] is True
        assert datos["mqtt"] is True

    def test_uptime_antes_de_arrancar(self, cfg_firmware, reloj):
        controlador = crear_controlador(cfg_firmware, reloj)
        assert controlador.uptime_s() == 0
