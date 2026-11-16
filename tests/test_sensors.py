"""Pruebas de los sensores con dobles de hardware."""

from __future__ import annotations

import time

import pytest

import sensors
from tests.support.fakes import DobleADC, DobleDHT, DoblePin


class TestMediana:
    def test_lista_impar(self):
        assert sensors._mediana([3, 1, 2]) == 2

    def test_lista_par(self):
        assert sensors._mediana([4, 1, 3, 2]) == 2.5

    def test_lista_vacia(self):
        assert sensors._mediana([]) is None

    def test_un_solo_valor(self):
        assert sensors._mediana([7]) == 7


class TestDht:
    def test_lee_temperatura_y_humedad(self):
        DobleDHT.reiniciar([(24.5, 60.0)])
        sensor = sensors.DhtSensor(27)
        lectura = sensor.leer()
        assert lectura == {"temp_c": 24.5, "hum_pct": 60.0}

    def test_reintenta_tras_un_fallo(self):
        DobleDHT.reiniciar([OSError("sin respuesta"), (25.0, 55.0)])
        sensor = sensors.DhtSensor(27, retries=3)
        assert sensor.leer()["temp_c"] == 25.0

    def test_falla_si_todos_los_intentos_fallan(self):
        DobleDHT.reiniciar([OSError("sin respuesta")] * 5)
        sensor = sensors.DhtSensor(27, retries=2)
        with pytest.raises(RuntimeError):
            sensor.leer()

    def test_rechaza_temperaturas_absurdas(self):
        DobleDHT.reiniciar([(150.0, 50.0)] * 3)
        sensor = sensors.DhtSensor(27, retries=2)
        with pytest.raises(RuntimeError):
            sensor.leer()

    def test_rechaza_humedad_fuera_de_rango(self):
        DobleDHT.reiniciar([(24.0, 130.0)] * 3)
        sensor = sensors.DhtSensor(27, retries=2)
        with pytest.raises(RuntimeError):
            sensor.leer()

    def test_suaviza_con_la_mediana(self):
        DobleDHT.reiniciar([(20.0, 40.0), (30.0, 50.0), (40.0, 60.0)])
        sensor = sensors.DhtSensor(27, ventana=3)
        sensor.leer()
        sensor.leer()
        tercera = sensor.leer()
        assert tercera["temp_c"] == 30.0
        assert tercera["hum_pct"] == 50.0


class TestPir:
    def test_detecta_movimiento(self, monkeypatch):
        pin = DoblePin(26, DoblePin.IN)
        sensor = sensors.PirSensor(26, mantenimiento_ms=1500)
        # el sensor crea su propio pin: se usa el registrado
        creado = DoblePin.instancias[-1]
        creado.simular(1)
        assert sensor.leer() is True

    def test_mantiene_el_estado_un_tiempo(self, monkeypatch):
        reloj = {"t": 1000}
        monkeypatch.setattr(time, "ticks_ms", lambda: reloj["t"])
        sensor = sensors.PirSensor(26, mantenimiento_ms=1500)
        creado = DoblePin.instancias[-1]
        creado.simular(1)
        assert sensor.leer() is True
        creado.simular(0)
        reloj["t"] = 1800
        assert sensor.leer() is True
        reloj["t"] = 3000
        assert sensor.leer() is False

    def test_sin_movimiento(self):
        sensor = sensors.PirSensor(26)
        assert sensor.leer() is False


class TestUltrasonido:
    def test_convierte_el_pulso_en_centimetros(self, maquina):
        maquina.pulsos[18] = 5800
        sensor = sensors.UltrasonicSensor(5, 18)
        assert sensor.leer() == 100.0

    def test_usa_la_mediana_de_varios_disparos(self, maquina):
        maquina.pulsos_secuencia = [5800, 5800, 2320, 5800]
        sensor = sensors.UltrasonicSensor(5, 18, muestras=3)
        assert sensor.leer() == 100.0

    def test_sin_eco_lanza_error(self, maquina):
        maquina.pulsos[18] = -2
        sensor = sensors.UltrasonicSensor(5, 18)
        with pytest.raises(RuntimeError):
            sensor.leer()

    def test_descarta_distancias_fuera_de_rango(self, maquina):
        maquina.pulsos_secuencia = [5800, 116, 5800, 5800]
        sensor = sensors.UltrasonicSensor(5, 18, min_cm=2.0, muestras=3)
        # el disparo de 116 us equivale a 2 cm: se descarta y sobrevive la mediana
        assert sensor.leer() == 100.0


class TestLuz:
    def test_lectura_media_corresponde_a_cien_lux(self):
        DobleADC.valor = 2047
        sensor = sensors.LightSensor(34, vcc=3.3)
        lux = sensor.leer()
        assert 90.0 < lux < 115.0

    def test_mas_luz_menos_valor_de_adc(self):
        sensor = sensors.LightSensor(34, vcc=3.3)
        DobleADC.valor = 3000
        oscuro = sensor.leer()
        DobleADC.valor = 800
        claro = sensor.leer()
        assert claro > oscuro

    def test_adc_al_maximo_es_oscuridad(self):
        DobleADC.valor = 4095
        assert sensors.LightSensor(34).leer() == 0.0

    def test_adc_en_cero_es_muy_brillante(self):
        DobleADC.valor = 0
        assert sensors.LightSensor(34).leer() > 1000.0


class TestSuite:
    def _suite(self):
        return sensors.SensorSuite([
            ("luz", sensors.LightSensor(34), 1.0),
            ("movimiento", sensors.PirSensor(26), 0.5),
        ])

    def test_respeta_los_periodos(self):
        suite = self._suite()
        primera = suite.actualizar(100.0)
        assert set(primera) == {"luz", "movimiento"}
        segunda = suite.actualizar(100.2)
        assert segunda == {}
        # a los 0.6 s solo vencio el sensor de movimiento (0.5 s)
        tercera = suite.actualizar(100.6)
        assert set(tercera) == {"movimiento"}
        # a los 1.05 s vence la luz (1.0 s) pero no el movimiento (0.45 s)
        cuarta = suite.actualizar(101.05)
        assert set(cuarta) == {"luz"}

    def test_aisla_errores_por_sensor(self, monkeypatch):
        class Explosivo:
            def leer(self):
                raise RuntimeError("roto")

        suite = sensors.SensorSuite([("roto", Explosivo(), 1.0),
                                     ("luz", sensors.LightSensor(34), 1.0)])
        nuevas = suite.actualizar(50.0)
        assert "roto" not in nuevas
        assert "luz" in nuevas
        assert suite.errores["roto"] == 1
        assert suite.total_errores() == 1

    def test_conserva_la_ultima_lectura_valida(self):
        suite = sensors.SensorSuite([("luz", sensors.LightSensor(34), 1.0)])
        suite.actualizar(10.0)
        valor = suite.instantanea()["luz"]
        suite.actualizar(12.0)
        assert suite.instantanea()["luz"] == valor

    def test_nombres(self):
        assert self._suite().nombres() == ["luz", "movimiento"]

    def test_construir_desde_config(self, cfg_firmware):
        suite = sensors.construir_desde_config(cfg_firmware)
        assert suite.nombres() == ["clima", "movimiento", "distancia", "luz"]
