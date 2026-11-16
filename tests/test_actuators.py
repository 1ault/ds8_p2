"""Pruebas de los actuadores (LEDs, sirena y cerradura)."""

from __future__ import annotations

import actuators
from tests.support.fakes import DoblePin, DoblePWM


class TestLed:
    def test_arranca_apagado(self):
        led = actuators.Led(23, "rojo")
        assert led.encendido is False
        assert DoblePin.instancias[-1].value() == 0

    def test_encender_y_apagar(self):
        led = actuators.Led(23)
        led.encender()
        assert led.encendido is True
        led.apagar()
        assert led.encendido is False

    def test_no_reescribe_el_pin_si_no_cambia(self):
        led = actuators.Led(23)
        led.encender()
        escrituras = len(DoblePin.instancias[-1].escrituras)
        led.encender()
        assert len(DoblePin.instancias[-1].escrituras) == escrituras

    def test_fijar_con_booleano(self):
        led = actuators.Led(19)
        led.fijar(True)
        assert led.encendido is True
        led.fijar(False)
        assert led.encendido is False

    def test_alternar(self):
        led = actuators.Led(19)
        led.alternar()
        assert led.encendido is True
        led.alternar()
        assert led.encendido is False


class TestBuzzer:
    def test_encender_fija_frecuencia_y_ciclo(self):
        buzzer = actuators.Buzzer(25)
        buzzer.encender(2900)
        assert buzzer.activo is True
        pwm = DoblePWM.instancias[-1]
        assert pwm.historial_freq[-1] == 2900

    def test_apagar_deja_ciclo_en_cero(self):
        buzzer = actuators.Buzzer(25)
        buzzer.encender(2400)
        buzzer.apagar()
        assert buzzer.activo is False
        assert DoblePWM.instancias[-1].duty() == 0

    def test_fijar_con_frecuencia(self):
        buzzer = actuators.Buzzer(25)
        buzzer.fijar(True, 2400)
        assert buzzer.activo is True
        buzzer.fijar(False)
        assert buzzer.activo is False

    def test_deinit_apaga(self):
        buzzer = actuators.Buzzer(25)
        buzzer.encender(2400)
        buzzer.deinit()
        assert buzzer.activo is False


class TestServoCerradura:
    def test_arranca_cerrada_en_cero_grados(self):
        cerradura = actuators.ServoLock(13)
        assert cerradura.angulo == 0
        assert cerradura.cerrada is True

    def test_abrir_pone_noventa_grados(self):
        cerradura = actuators.ServoLock(13)
        cerradura.abrir()
        assert cerradura.angulo == 90
        assert cerradura.cerrada is False

    def test_cerrar_vuelve_a_cero(self):
        cerradura = actuators.ServoLock(13)
        cerradura.abrir()
        cerradura.cerrar()
        assert cerradura.angulo == 0
        assert cerradura.cerrada is True

    def test_ciclo_para_cero_grados(self):
        cerradura = actuators.ServoLock(13, min_us=500, max_us=2500)
        # 500 us sobre un periodo de 20 ms = 2.5 % de 65535
        assert cerradura._duty_para(0) == 1638

    def test_ciclo_para_noventa_grados(self):
        cerradura = actuators.ServoLock(13, min_us=500, max_us=2500)
        # 1500 us = 7.5 % de 65535
        assert cerradura._duty_para(90) == 4915

    def test_angulo_fuera_de_rango_se_recorta(self):
        cerradura = actuators.ServoLock(13)
        assert cerradura.mover_a(200) == 200
        assert DoblePWM.instancias[-1].duty_u16() == cerradura._duty_para(180)


class TestPanel:
    def test_estado_inicial(self):
        panel = actuators.PanelActuadores(
            actuators.Led(23, "rojo"), actuators.Led(19, "verde"),
            actuators.Buzzer(25), actuators.ServoLock(13))
        estado = panel.estado()
        assert estado["led_rojo"] is False
        assert estado["sirena"] is False
        assert estado["cerrada"] is True

    def test_apagar_todo(self):
        panel = actuators.PanelActuadores(
            actuators.Led(23, "rojo"), actuators.Led(19, "verde"),
            actuators.Buzzer(25), actuators.ServoLock(13))
        panel.led_rojo.encender()
        panel.led_verde.encender()
        panel.buzzer.encender(2400)
        panel.apagar_todo()
        estado = panel.estado()
        assert estado["led_rojo"] is False
        assert estado["led_verde"] is False
        assert estado["sirena"] is False

    def test_construir_desde_config(self, cfg_firmware):
        panel = actuators.construir_desde_config(cfg_firmware)
        assert panel.cerradura.cerrada is True
        assert panel.led_rojo.nombre == "rojo"
