"""Pruebas de la integracion con ThingSpeak (canal y TalkBack)."""

from __future__ import annotations

import json

from backend import cloud as cloud_mod
from backend.config import Config


class RespuestaFalsa:
    def __init__(self, status=200, texto=""):
        self.status = status
        self._texto = texto

    async def text(self):
        return self._texto

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class SesionFalsa:
    """Sustituto de aiohttp.ClientSession."""

    def __init__(self, respuesta_post=None, respuesta_get=None, excepcion=None):
        self.respuesta_post = respuesta_post or RespuestaFalsa(200, "42")
        self.respuesta_get = respuesta_get or RespuestaFalsa(200, "")
        self.excepcion = excepcion
        self.posts: list[dict] = []
        self.gets: list[dict] = []

    def post(self, url, data=None):
        if self.excepcion:
            raise self.excepcion
        self.posts.append({"url": url, "data": data})
        return self.respuesta_post

    def get(self, url, params=None):
        if self.excepcion:
            raise self.excepcion
        self.gets.append({"url": url, "params": params})
        return self.respuesta_get


LECTURA = {
    "temp_c": 24.5, "hum_pct": 58.0, "lux": 120.0, "dist_cm": 150.0,
    "motion": False, "alarm": True, "state": "ALARM", "alerts": 2,
}


def cfg_nube(**cambios):
    base = dict(ts_canal="12345", ts_write_key="CLAVE",
                ts_talkback_id="99", ts_talkback_key="TB",
                ts_intervalo_s=0.0)
    base.update(cambios)
    return Config(**base)


class TestParseoComandos:
    def test_comando_simple(self):
        assert cloud_mod.parsear_comando("arm") == {"cmd": "arm", "args": {}}

    def test_normaliza_mayusculas(self):
        assert cloud_mod.parsear_comando("DISARM") == {"cmd": "disarm", "args": {}}

    def test_unlock_con_pin(self):
        assert cloud_mod.parsear_comando("unlock:2468") == {
            "cmd": "unlock", "args": {"pin": "2468"}}

    def test_set_config(self):
        comando = cloud_mod.parsear_comando("set_config:dist_alarm_cm=120")
        assert comando == {"cmd": "set_config", "args": {"dist_alarm_cm": 120.0}}

    def test_set_config_invalido(self):
        assert cloud_mod.parsear_comando("set_config:sin_igual") is None

    def test_vacio(self):
        assert cloud_mod.parsear_comando("") is None
        assert cloud_mod.parsear_comando("   ") is None
        assert cloud_mod.parsear_comando(None) is None


class TestCanal:
    def test_sin_claves_esta_inactiva(self):
        nube = cloud_mod.NubeThingSpeak(Config())
        assert nube.activa() is False
        assert nube.estado()["activa"] is False

    def test_mapeo_de_campos(self):
        nube = cloud_mod.NubeThingSpeak(cfg_nube())
        campos = nube.construir_campos(LECTURA)
        assert campos["field1"] == 24.5
        assert campos["field2"] == 58.0
        assert campos["field3"] == 120.0
        assert campos["field4"] == 150.0
        assert campos["field5"] == 0
        assert campos["field6"] == 1
        assert campos["field7"] == cloud_mod.STATE_CODES["ALARM"]
        assert campos["field8"] == 2

    def test_codigos_de_estado(self):
        assert cloud_mod.STATE_CODES == {"DISARMED": 0, "ARMING": 1,
                                         "ARMED": 2, "ALARM": 3}

    def test_estado_desconocido_usa_menos_uno(self):
        nube = cloud_mod.NubeThingSpeak(cfg_nube())
        campos = nube.construir_campos({"state": "RARO"})
        assert campos["field7"] == -1

    async def test_subida_exitosa(self):
        sesion = SesionFalsa(RespuestaFalsa(200, "777"))
        nube = cloud_mod.NubeThingSpeak(cfg_nube(), sesion=sesion)
        assert await nube.subir(LECTURA) is True
        assert nube.enviados == 1
        assert nube.ultimo_entry == "777"
        enviado = sesion.posts[0]["data"]
        assert enviado["api_key"] == "CLAVE"
        assert enviado["field5"] == 0

    async def test_no_envia_sin_claves(self):
        nube = cloud_mod.NubeThingSpeak(Config())
        assert await nube.subir(LECTURA) is False

    async def test_respeta_el_intervalo(self):
        sesion = SesionFalsa()
        nube = cloud_mod.NubeThingSpeak(cfg_nube(ts_intervalo_s=60), sesion=sesion)
        assert await nube.subir(LECTURA) is True
        assert await nube.subir(LECTURA) is False
        assert len(sesion.posts) == 1
        assert nube.omitidos == 1

    async def test_thingspeak_rechaza(self):
        sesion = SesionFalsa(RespuestaFalsa(200, "0"))
        nube = cloud_mod.NubeThingSpeak(cfg_nube(), sesion=sesion)
        assert await nube.subir(LECTURA) is False
        assert nube.errores == 1

    async def test_error_http(self):
        sesion = SesionFalsa(RespuestaFalsa(500, "boom"))
        nube = cloud_mod.NubeThingSpeak(cfg_nube(), sesion=sesion)
        assert await nube.subir(LECTURA) is False
        assert nube.errores == 1

    async def test_error_de_red(self):
        sesion = SesionFalsa(excepcion=RuntimeError("sin red"))
        nube = cloud_mod.NubeThingSpeak(cfg_nube(), sesion=sesion)
        assert await nube.subir(LECTURA) is False
        assert "sin red" in nube.ultimo_error

    async def test_omite_campos_nulos(self):
        sesion = SesionFalsa()
        nube = cloud_mod.NubeThingSpeak(cfg_nube(), sesion=sesion)
        await nube.subir({"state": "ARMED"})
        enviado = sesion.posts[0]["data"]
        assert "field1" not in enviado
        assert enviado["field7"] == 2


class TestTalkBack:
    async def test_lee_el_siguiente_comando(self):
        cuerpo = json.dumps({"id": 5, "command_string": "arm"})
        sesion = SesionFalsa(respuesta_get=RespuestaFalsa(200, cuerpo))
        nube = cloud_mod.NubeThingSpeak(cfg_nube(), sesion=sesion)
        comando = await nube.siguiente_comando()
        assert comando["cmd"] == "arm"
        assert comando["talkback_id"] == 5
        assert nube.comandos_recibidos == 1

    async def test_cola_vacia(self):
        sesion = SesionFalsa(respuesta_get=RespuestaFalsa(200, "-1"))
        nube = cloud_mod.NubeThingSpeak(cfg_nube(), sesion=sesion)
        assert await nube.siguiente_comando() is None

    async def test_sin_talkback_configurado(self):
        sesion = SesionFalsa()
        nube = cloud_mod.NubeThingSpeak(
            cfg_nube(ts_talkback_id="", ts_talkback_key=""), sesion=sesion)
        assert await nube.siguiente_comando() is None
        assert sesion.gets == []

    async def test_respuesta_invalida(self):
        sesion = SesionFalsa(respuesta_get=RespuestaFalsa(200, "{no json"))
        nube = cloud_mod.NubeThingSpeak(cfg_nube(), sesion=sesion)
        assert await nube.siguiente_comando() is None
        assert nube.ultimo_error

    async def test_error_http(self):
        sesion = SesionFalsa(respuesta_get=RespuestaFalsa(404, ""))
        nube = cloud_mod.NubeThingSpeak(cfg_nube(), sesion=sesion)
        assert await nube.siguiente_comando() is None


class TestNubeNula:
    def test_siempre_inactiva(self):
        nube = cloud_mod.NubeNula()
        assert nube.activa() is False
        assert nube.talkback() is False
        assert nube.estado()["activa"] is False

    async def test_no_hace_nada(self):
        nube = cloud_mod.NubeNula()
        assert await nube.subir(LECTURA) is False
        assert await nube.siguiente_comando() is None
        assert await nube.cerrar() is None
