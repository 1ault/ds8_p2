"""Pruebas de la capa de datos (SQLite)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.storage import Almacen, iso


class RelojManual:
    """Reloj UTC controlable para que las marcas de tiempo sean deterministas."""

    def __init__(self, base: datetime | None = None):
        self.actual = base or datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.actual

    def avanzar(self, **cambios):
        self.actual = self.actual + timedelta(**cambios)
        return self.actual


@pytest.fixture
async def almacen_reloj(ruta_bd):
    reloj = RelojManual()
    almacen = Almacen(ruta_bd, reloj=reloj)
    await almacen.abrir()
    await almacen.registrar_dispositivo("dev01", "Puerta", "Casa", "2.0.0")
    try:
        yield almacen, reloj
    finally:
        await almacen.cerrar()


def lectura(temp=24.5, hum=58.0, estado="ARMED", **extra):
    datos = {
        "temp_c": temp, "hum_pct": hum, "lux": 120.0, "dist_cm": 150.0,
        "motion": False, "state": estado, "alarm": False, "siren": False,
        "locked": True, "alerts": 0, "rssi": -55, "seq": 1, "sensor_errors": 0,
    }
    datos.update(extra)
    return datos


class TestLecturas:
    async def test_guarda_y_recupera_la_ultima(self, almacen, lectura_ejemplo):
        await almacen.registrar_dispositivo("dev01")
        await almacen.guardar_lectura("dev01", lectura_ejemplo)
        ultima = await almacen.ultima_lectura("dev01")
        assert ultima["temp_c"] == pytest.approx(24.6)
        assert ultima["state"] == "ARMED"
        assert ultima["alarm"] == 0

    async def test_sin_lecturas_devuelve_none(self, almacen):
        assert await almacen.ultima_lectura("dev01") is None

    async def test_guarda_la_marca_de_tiempo_del_servidor(self, almacen_reloj):
        almacen, reloj = almacen_reloj
        await almacen.guardar_lectura("dev01", lectura())
        ultima = await almacen.ultima_lectura("dev01")
        assert ultima["ts_utc"] == "2026-01-15T12:00:00.000Z"
        assert ultima["ts_epoch"] == pytest.approx(reloj().timestamp())

    async def test_convierte_booleanos_a_enteros(self, almacen):
        await almacen.registrar_dispositivo("dev01")
        await almacen.guardar_lectura("dev01", lectura(motion=True, alarm=True))
        ultima = await almacen.ultima_lectura("dev01")
        assert ultima["motion"] == 1
        assert ultima["alarm"] == 1

    async def test_acepta_valores_nulos(self, almacen):
        await almacen.registrar_dispositivo("dev01")
        await almacen.guardar_lectura("dev01", {"state": "DISARMED", "temp_c": None})
        ultima = await almacen.ultima_lectura("dev01")
        assert ultima["temp_c"] is None
        assert ultima["hum_pct"] is None

    async def test_historico_respeta_las_horas(self, almacen_reloj):
        almacen, reloj = almacen_reloj
        await almacen.guardar_lectura("dev01", lectura())
        reloj.avanzar(hours=3)
        await almacen.guardar_lectura("dev01", lectura(temp=30.0))
        recientes = await almacen.historico("dev01", horas=1)
        assert len(recientes) == 1
        todas = await almacen.historico("dev01", horas=10)
        assert len(todas) == 2

    async def test_historico_viene_en_orden_cronologico(self, almacen_reloj):
        almacen, reloj = almacen_reloj
        for temperatura in (20.0, 21.0, 22.0):
            await almacen.guardar_lectura("dev01", lectura(temp=temperatura))
            reloj.avanzar(minutes=5)
        filas = await almacen.historico("dev01", horas=24)
        assert [f["temp_c"] for f in filas] == [20.0, 21.0, 22.0]

    async def test_agregado_horario_agrupa(self, almacen_reloj):
        almacen, reloj = almacen_reloj
        await almacen.guardar_lectura("dev01", lectura(temp=20.0))
        reloj.avanzar(minutes=10)
        await almacen.guardar_lectura("dev01", lectura(temp=24.0))
        reloj.avanzar(hours=1)
        await almacen.guardar_lectura("dev01", lectura(temp=30.0))
        buckets = await almacen.agregado_horario("dev01", horas=5)
        assert len(buckets) == 2
        assert buckets[0]["muestras"] == 2
        assert buckets[0]["temp_media"] == pytest.approx(22.0)
        assert buckets[1]["muestras"] == 1

    async def test_parametros_sql_evitan_inyeccion(self, almacen):
        raro = "dev01'; DROP TABLE readings; --"
        await almacen.registrar_dispositivo(raro)
        await almacen.guardar_lectura(raro, lectura())
        assert await almacen.ultima_lectura(raro) is not None
        # la tabla sigue existiendo
        assert await almacen.ultima_lectura("otro") is None


class TestEventos:
    async def test_registra_y_lista(self, almacen):
        await almacen.registrar_dispositivo("dev01")
        await almacen.registrar_evento("dev01", "intrusion", "Presencia",
                                       "critical", "ALARM", {"cm": 30})
        eventos = await almacen.eventos("dev01")
        assert len(eventos) == 1
        assert eventos[0]["severity"] == "critical"
        assert eventos[0]["data"]["cm"] == 30

    async def test_filtra_por_severidad(self, almacen):
        await almacen.registrar_dispositivo("dev01")
        await almacen.registrar_evento("dev01", "state", "Armado", "info")
        await almacen.registrar_evento("dev01", "intrusion", "Alerta", "critical")
        criticos = await almacen.eventos("dev01", severidad="critical")
        assert len(criticos) == 1
        assert criticos[0]["kind"] == "intrusion"

    async def test_respeta_el_limite(self, almacen):
        await almacen.registrar_dispositivo("dev01")
        for i in range(10):
            await almacen.registrar_evento("dev01", "state", "evento %d" % i)
        assert len(await almacen.eventos("dev01", limite=3)) == 3

    async def test_evento_sin_datos(self, almacen):
        await almacen.registrar_dispositivo("dev01")
        await almacen.registrar_evento("dev01", "network", "MQTT caido")
        eventos = await almacen.eventos("dev01")
        assert eventos[0]["data"] is None


class TestComandos:
    async def test_crear_queda_pendiente(self, almacen):
        await almacen.registrar_dispositivo("dev01")
        await almacen.crear_comando("abc", "dev01", "arm", {}, "panel")
        filas = await almacen.comandos()
        assert filas[0]["estado"] == "PENDIENTE"
        assert filas[0]["args"] == {}

    async def test_confirmar_ok_calcula_latencia(self, almacen_reloj):
        almacen, reloj = almacen_reloj
        await almacen.crear_comando("abc", "dev01", "arm", {}, "panel")
        reloj.avanzar(milliseconds=450)
        assert await almacen.confirmar_comando("abc", "OK", {"state": "ARMING"}) is True
        fila = (await almacen.comandos())[0]
        assert fila["estado"] == "OK"
        assert fila["latencia_ms"] == pytest.approx(450, abs=5)
        assert fila["resultado"]["state"] == "ARMING"

    async def test_confirmar_solo_una_vez(self, almacen):
        await almacen.registrar_dispositivo("dev01")
        await almacen.crear_comando("abc", "dev01", "arm", {}, "panel")
        assert await almacen.confirmar_comando("abc", "OK") is True
        assert await almacen.confirmar_comando("abc", "TIMEOUT") is False

    async def test_confirmar_inexistente(self, almacen):
        assert await almacen.confirmar_comando("no-existe", "OK") is False

    async def test_expirar_marca_timeout(self, almacen_reloj):
        almacen, reloj = almacen_reloj
        await almacen.crear_comando("viejo", "dev01", "arm", {}, "panel")
        reloj.avanzar(seconds=30)
        expirados = await almacen.expirar_comandos(10)
        assert expirados == 1
        fila = (await almacen.comandos())[0]
        assert fila["estado"] == "TIMEOUT"
        assert fila["motivo"] == "sin_ack"

    async def test_expirar_no_toca_los_recientes(self, almacen):
        await almacen.registrar_dispositivo("dev01")
        await almacen.crear_comando("nuevo", "dev01", "arm", {}, "panel")
        assert await almacen.expirar_comandos(60) == 0

    async def test_estado_comandos_agrupa(self, almacen):
        await almacen.registrar_dispositivo("dev01")
        await almacen.crear_comando("a", "dev01", "arm", {}, "panel")
        await almacen.crear_comando("b", "dev01", "disarm", {}, "panel")
        await almacen.confirmar_comando("a", "OK")
        assert await almacen.estado_comandos() == {"PENDIENTE": 1, "OK": 1}


class TestEstadosYEstadisticas:
    async def test_cambios_de_estado(self, almacen):
        await almacen.registrar_dispositivo("dev01")
        await almacen.registrar_cambio_estado("dev01", "DISARMED", "ARMING", "arm")
        cambios = await almacen.cambios_estado("dev01")
        assert cambios[0]["hacia"] == "ARMING"
        assert cambios[0]["desde"] == "DISARMED"

    async def test_estadisticas_agregan_lecturas(self, almacen_reloj):
        almacen, reloj = almacen_reloj
        await almacen.guardar_lectura("dev01", lectura(temp=20.0))
        reloj.avanzar(minutes=5)
        await almacen.guardar_lectura("dev01", lectura(temp=30.0, alarm=True))
        datos = await almacen.estadisticas("dev01")
        assert datos["total"] == 2
        assert datos["temp_media"] == pytest.approx(25.0)
        assert datos["temp_min"] == pytest.approx(20.0)
        assert datos["temp_max"] == pytest.approx(30.0)
        assert datos["alarmas"] == 1

    async def test_estadisticas_de_base_vacia(self, almacen):
        datos = await almacen.estadisticas("dev01")
        assert datos["total"] == 0
        assert datos["latencia_media_ms"] is None

    async def test_purgar_borra_lo_viejo(self, almacen_reloj):
        almacen, reloj = almacen_reloj
        await almacen.guardar_lectura("dev01", lectura())
        reloj.avanzar(days=40)
        await almacen.guardar_lectura("dev01", lectura())
        borrado = await almacen.purgar(30)
        assert borrado["readings"] == 1
        assert len(await almacen.historico("dev01", horas=24 * 365)) == 1


class TestDispositivos:
    async def test_registro_idempotente(self, almacen):
        await almacen.registrar_dispositivo("dev01", "Puerta")
        await almacen.registrar_dispositivo("dev01", "Puerta principal")
        dispositivos = await almacen.dispositivos()
        assert len(dispositivos) == 1
        assert dispositivos[0]["nombre"] == "Puerta principal"

    async def test_actualiza_la_ultima_vez_visto(self, almacen_reloj):
        almacen, reloj = almacen_reloj
        await almacen.registrar_dispositivo("dev01")
        primera = (await almacen.dispositivos())[0]["visto_utc"]
        reloj.avanzar(hours=1)
        await almacen.registrar_dispositivo("dev01")
        segunda = (await almacen.dispositivos())[0]["visto_utc"]
        assert primera != segunda


class TestCicloDeVida:
    async def test_persiste_entre_aperturas(self, ruta_bd):
        primero = Almacen(ruta_bd)
        await primero.abrir()
        await primero.registrar_dispositivo("dev01")
        await primero.guardar_lectura("dev01", lectura())
        await primero.cerrar()

        segundo = Almacen(ruta_bd)
        await segundo.abrir()
        assert await segundo.ultima_lectura("dev01") is not None
        await segundo.cerrar()

    async def test_operar_cerrado_falla(self, ruta_bd):
        almacen = Almacen(ruta_bd)
        await almacen.abrir()
        await almacen.cerrar()
        with pytest.raises(RuntimeError):
            await almacen.ultima_lectura("dev01")

    async def test_abrir_dos_veces_es_seguro(self, ruta_bd):
        almacen = Almacen(ruta_bd)
        await almacen.abrir()
        await almacen.abrir()
        assert almacen._conn is not None
        await almacen.cerrar()
        await almacen.cerrar()

    def test_iso_termina_en_z(self):
        momento = datetime(2026, 5, 1, 8, 30, 15, 123000, tzinfo=timezone.utc)
        assert iso(momento) == "2026-05-01T08:30:15.123Z"
