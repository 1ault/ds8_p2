"""Pruebas del servicio de comandos: validacion, envio, ACK y auditoria."""

from __future__ import annotations

import asyncio

import pytest

from backend import commands as cmd_mod
from backend.bus import Hub


class PuenteFalso:
    """Puente MQTT falso: registra publicaciones sin red."""

    def __init__(self, conectado=True, publica=True):
        self.conectado = conectado
        self._publica = publica
        self.publicados: list[tuple] = []

    def publicar(self, topico, payload, qos=1, retain=False):
        if not self._publica:
            return False
        self.publicados.append((topico, payload, qos, retain))
        return True

    def estado(self):
        return {"conectado": self.conectado}


async def esperar(condicion, timeout=10.0):
    """Espera activa con margen amplio: el equipo puede estar bajo carga."""
    bucle = asyncio.get_running_loop()
    fin = bucle.time() + timeout
    while bucle.time() < fin:
        if condicion():
            return True
        await asyncio.sleep(0.005)
    return False


@pytest.fixture
def puente():
    return PuenteFalso()


@pytest.fixture
def servicio(cfg, almacen, puente):
    return cmd_mod.ServicioComandos(cfg, almacen, puente, hub=Hub(), log=lambda m: None)


class TestValidador:
    def setup_method(self):
        self.validador = cmd_mod.Validador()

    def test_comando_simple(self):
        assert self.validador.validar("arm", None) == (True, None, {})
        assert self.validador.validar("disarm", {}) == (True, None, {})

    def test_normaliza_mayusculas(self):
        assert self.validador.validar("ARM", None)[0] is True

    def test_comando_desconocido(self):
        valido, motivo, _ = self.validador.validar("reiniciar", None)
        assert valido is False
        assert motivo == "comando_no_permitido"

    def test_pin_valido(self):
        valido, motivo, limpio = self.validador.validar("unlock", {"pin": "2468"})
        assert valido is True
        assert limpio == {"pin": "2468"}

    def test_pin_no_numerico(self):
        assert self.validador.validar("unlock", {"pin": "abcd"})[1] == "pin_invalido"

    def test_pin_corto(self):
        assert self.validador.validar("unlock", {"pin": "123"})[1] == "pin_invalido"

    def test_pin_largo(self):
        assert self.validador.validar("unlock", {"pin": "123456789"})[1] == "pin_invalido"

    def test_pin_ausente(self):
        assert self.validador.validar("unlock", {})[1] == "pin_invalido"

    def test_argumentos_no_dict(self):
        assert self.validador.validar("arm", ["x"])[1] == "argumentos_invalidos"

    def test_argumentos_gigantes(self):
        grande = {"relleno": "x" * 2000}
        assert self.validador.validar("arm", grande)[1] == "argumentos_demasiado_grandes"

    def test_set_config_valido(self):
        valido, _, limpio = self.validador.validar(
            "set_config", {"dist_alarm_cm": 100, "exit_delay_s": 5})
        assert valido is True
        assert limpio == {"dist_alarm_cm": 100.0, "exit_delay_s": 5.0}

    def test_set_config_ignora_claves_desconocidas(self):
        valido, _, limpio = self.validador.validar(
            "set_config", {"dist_alarm_cm": 100, "inventada": 1})
        assert valido is True
        assert "inventada" not in limpio

    def test_set_config_fuera_de_rango(self):
        assert self.validador.validar("set_config", {"exit_delay_s": 9999})[1] == "config_fuera_de_rango"

    def test_set_config_no_numerica(self):
        assert self.validador.validar("set_config", {"exit_delay_s": "mucho"})[1] == "config_no_numerica"

    def test_set_config_vacia(self):
        assert self.validador.validar("set_config", {})[1] == "config_vacia"

    def test_claves_de_configuracion(self):
        assert "dist_alarm_cm" in self.validador.claves_config()


class TestServicio:
    async def test_envia_y_espera_el_ack(self, servicio, puente, almacen):
        tarea = asyncio.create_task(servicio.ejecutar("arm"))
        assert await esperar(lambda: puente.publicados)
        topico, mensaje, qos, _ = puente.publicados[0]
        assert topico.endswith("/cmd")
        assert mensaje["cmd"] == "arm"
        assert qos == 1
        assert servicio.pendientes() == 1

        assert await servicio.confirmar({"id": mensaje["id"], "ok": True,
                                         "result": {"state": "ARMING"},
                                         "state": "ARMING"}) is True
        resultado = await tarea
        assert resultado["ok"] is True
        assert resultado["id"] == mensaje["id"]

        fila = (await almacen.comandos())[0]
        assert fila["estado"] == "OK"
        assert fila["resultado"]["state"] == "ARMING"

    async def test_rechazo_del_nodo(self, servicio, puente, almacen):
        tarea = asyncio.create_task(servicio.ejecutar("unlock", {"pin": "1111"}))
        assert await esperar(lambda: puente.publicados)
        cmd_id = puente.publicados[0][1]["id"]
        await servicio.confirmar({"id": cmd_id, "ok": False,
                                  "reason": "pin_incorrecto"})
        resultado = await tarea
        assert resultado["ok"] is False
        assert resultado["motivo"] == "pin_incorrecto"
        assert (await almacen.comandos())[0]["estado"] == "RECHAZADO"

    async def test_timeout_sin_ack(self, cfg, almacen, puente):
        servicio = cmd_mod.ServicioComandos(cfg, almacen, puente, timeout_s=0.05)
        resultado = await servicio.ejecutar("arm")
        assert resultado["ok"] is False
        assert resultado["motivo"] == "timeout"
        assert (await almacen.comandos())[0]["estado"] == "TIMEOUT"
        assert servicio.timeouts == 1

    async def test_sin_conexion_mqtt(self, servicio):
        servicio.puente.conectado = False
        resultado = await servicio.ejecutar("arm")
        assert resultado["motivo"] == "sin_conexion_mqtt"
        assert servicio.puente.publicados == []

    async def test_comando_invalido_no_se_publica(self, servicio, puente, almacen):
        resultado = await servicio.ejecutar("formatear")
        assert resultado["ok"] is False
        assert resultado["motivo"] == "comando_no_permitido"
        assert puente.publicados == []
        assert await almacen.comandos() == []

    async def test_publicacion_fallida(self, cfg, almacen):
        puente = PuenteFalso(publica=False)
        servicio = cmd_mod.ServicioComandos(cfg, almacen, puente)
        resultado = await servicio.ejecutar("arm")
        assert resultado["motivo"] == "publicacion_fallida"
        assert (await almacen.comandos())[0]["estado"] == "ERROR"

    async def test_limite_de_frecuencia(self, cfg, almacen, puente):
        servicio = cmd_mod.ServicioComandos(cfg, almacen, puente,
                                           limite_por_minuto=1)
        tarea = asyncio.create_task(servicio.ejecutar("arm"))
        assert await esperar(lambda: puente.publicados)
        segundo = await servicio.ejecutar("disarm")
        assert segundo["motivo"] == "demasiados_comandos"
        cmd_id = puente.publicados[0][1]["id"]
        await servicio.confirmar({"id": cmd_id, "ok": True})
        await tarea

    async def test_ack_desconocido_se_ignora(self, servicio):
        assert await servicio.confirmar({"id": "no-existe", "ok": True}) is False
        assert await servicio.confirmar("no-es-dict") is False

    async def test_no_se_puede_confirmar_dos_veces(self, servicio, puente):
        tarea = asyncio.create_task(servicio.ejecutar("arm"))
        assert await esperar(lambda: puente.publicados)
        cmd_id = puente.publicados[0][1]["id"]
        assert await servicio.confirmar({"id": cmd_id, "ok": True}) is True
        assert await servicio.confirmar({"id": cmd_id, "ok": True}) is False
        await tarea

    async def test_expirar_delega_en_el_almacen(self, servicio, puente):
        tarea = asyncio.create_task(servicio.ejecutar("arm"))
        assert await esperar(lambda: puente.publicados)
        assert await servicio.expirar() == 0        # aun no vence
        cmd_id = puente.publicados[0][1]["id"]
        await servicio.confirmar({"id": cmd_id, "ok": True})
        await tarea

    async def test_cerrar_cancela_pendientes(self, servicio, puente):
        tarea = asyncio.create_task(servicio.ejecutar("arm"))
        assert await esperar(lambda: puente.publicados)
        servicio.cerrar()
        assert servicio.pendientes() == 0
        with pytest.raises(asyncio.CancelledError):
            await tarea

    async def test_hub_recibe_el_resultado(self, cfg, almacen, puente):
        hub = Hub()
        suscriptor = hub.suscribir()
        servicio = cmd_mod.ServicioComandos(cfg, almacen, puente, hub=hub)
        tarea = asyncio.create_task(servicio.ejecutar("arm", source="dashboard"))
        assert await esperar(lambda: puente.publicados)
        cmd_id = puente.publicados[0][1]["id"]
        await servicio.confirmar({"id": cmd_id, "ok": True, "state": "ARMING"})
        await tarea
        evento = await suscriptor.siguiente(timeout=1)
        assert evento["tipo"] == "comando"
        assert evento["datos"]["ok"] is True

    async def test_contadores(self, servicio, puente):
        tarea = asyncio.create_task(servicio.ejecutar("arm"))
        assert await esperar(lambda: puente.publicados)
        cmd_id = puente.publicados[0][1]["id"]
        await servicio.confirmar({"id": cmd_id, "ok": True})
        await tarea
        await servicio.ejecutar("formatear")
        assert servicio.aceptados == 1
        assert servicio.rechazados == 1
