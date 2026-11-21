"""Pruebas de la capa de hardware (HAL).

Regresion del bug mas caro del proyecto: `hal.Pin.IN = 0`, y en el ESP32 el
modo 0 es ``GPIO_MODE_DISABLE``. Con eso el PIR (GPIO26), el eco del HC-SR04
(GPIO18) y el pulsador (GPIO4) **leian siempre 0**: la alarma no disparaba con
movimiento, el OLED mostraba `Dst --` y el boton no hacia nada (o armaba solo,
porque el primer 0 parecia una pulsacion).
"""

from __future__ import annotations

import hal
import sensors


class TestModosDePin:
    def test_entrada_usa_el_modo_in_del_puerto(self, maquina):
        pin = hal.entrada(26)
        assert pin._obj.modo == maquina.Pin.IN

    def test_salida_usa_el_modo_out_del_puerto(self, maquina):
        pin = hal.salida(25)
        assert pin._obj.modo == maquina.Pin.OUT

    def test_la_entrada_del_pulsador_lleva_pull_up(self, maquina):
        pin = hal.entrada(4, pull=hal.pull_up())
        assert pin._obj.pull == maquina.Pin.PULL_UP

    def test_el_doble_refleja_los_valores_del_esp32(self, maquina):
        # 0 = GPIO_MODE_DISABLE y 1 = GPIO_MODE_INPUT en el ESP32.
        assert maquina.Pin.IN != 0
        assert maquina.Pin.OUT != 1

    def test_la_entrada_devuelve_el_nivel_del_pin(self, maquina):
        pin = hal.entrada(4, pull=hal.pull_up())
        pin._obj.simular(1)
        assert pin.value() == 1
        pin._obj.simular(0)
        assert pin.value() == 0

    def test_el_pir_queda_como_entrada_digital(self, maquina):
        pir = sensors.PirSensor(26)
        assert pir._pin._obj.modo == maquina.Pin.IN

    def test_el_eco_del_hc_sr04_queda_como_entrada(self, maquina):
        sensor = sensors.UltrasonicSensor(5, 18)
        assert sensor._echo._obj.modo == maquina.Pin.IN
        assert sensor._trig._obj.modo == maquina.Pin.OUT
