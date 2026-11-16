"""Pruebas de la interfaz local (OLED SSD1306)."""

from __future__ import annotations

import display
from tests.support.fakes import DobleFrameBuffer, DobleI2C

DATOS = {
    "state": "ARMED",
    "temp_c": 24.6,
    "hum_pct": 58.2,
    "lux": 120.0,
    "dist_cm": 145.0,
    "motion": False,
    "alerts": 2,
    "siren": False,
    "locked": True,
    "rssi": -55,
    "mqtt": True,
    "arm_in_s": 0,
    "exit_delay": 10,
}


def crear_pantalla(cfg_firmware):
    pantalla = display.construir_desde_config(cfg_firmware)
    return pantalla


def textos(pantalla):
    framebuffer = DobleFrameBuffer.instancias[-1]
    return [texto for texto, _, _ in framebuffer.textos]


class TestPantalla:
    def test_detecta_la_pantalla(self, cfg_firmware):
        pantalla = crear_pantalla(cfg_firmware)
        assert pantalla.disponible is True

    def test_escribe_las_escrituras_i2c(self, cfg_firmware):
        crear_pantalla(cfg_firmware)
        assert DobleI2C.instancias
        escrituras = DobleI2C.instancias[-1].escrituras
        assert escrituras
        assert escrituras[0][0] == cfg_firmware.OLED_ADDR

    def test_muestra_el_estado(self, cfg_firmware):
        pantalla = crear_pantalla(cfg_firmware)
        assert pantalla.mostrar(DATOS) is True
        contenido = textos(pantalla)
        assert "ARMADO" in contenido

    def test_muestra_las_lecturas(self, cfg_firmware):
        pantalla = crear_pantalla(cfg_firmware)
        pantalla.mostrar(DATOS)
        contenido = " ".join(textos(pantalla))
        assert "24.6" in contenido
        assert "58.2" in contenido

    def test_valores_ausentes_se_muestran_con_guiones(self, cfg_firmware):
        pantalla = crear_pantalla(cfg_firmware)
        pantalla.mostrar({"state": "DISARMED"})
        contenido = " ".join(textos(pantalla))
        assert "--" in contenido

    def test_recorta_los_textos_largos(self, cfg_firmware):
        pantalla = crear_pantalla(cfg_firmware)
        pantalla.mostrar(DATOS)
        for texto, _, _ in DobleFrameBuffer.instancias[-1].textos:
            assert len(texto) <= 16

    def test_muestra_la_cuenta_regresiva(self, cfg_firmware):
        pantalla = crear_pantalla(cfg_firmware)
        datos = dict(DATOS)
        datos.update({"state": "ARMING", "arm_in_s": 7})
        pantalla.mostrar(datos)
        contenido = " ".join(textos(pantalla))
        assert "Salida" in contenido and "7" in contenido

    def test_aviso_puntual(self, cfg_firmware):
        pantalla = crear_pantalla(cfg_firmware)
        assert pantalla.aviso("Conectando WiFi") is True
        assert any("Conectando" in texto for texto in textos(pantalla))

    def test_sin_pantalla_no_falla(self, cfg_firmware):
        DobleI2C.fallo = True
        pantalla = crear_pantalla(cfg_firmware)
        assert pantalla.disponible is False
        assert pantalla.mostrar(DATOS) is False
        assert pantalla.aviso("hola") is False
        assert pantalla.limpiar() is False

    def test_limpiar(self, cfg_firmware):
        pantalla = crear_pantalla(cfg_firmware)
        assert pantalla.limpiar() is True


class TestNumero:
    def test_entero(self):
        assert display._num(24.6, 0) == "25"

    def test_decimal(self):
        assert display._num(24.64, 1) == "24.6"

    def test_none(self):
        assert display._num(None) == "--"

    def test_texto_invalido(self):
        assert display._num("abc") == "--"


class TestRecorte:
    def test_no_corta_si_entra(self):
        assert display._recortar("abc", 16) == "abc"

    def test_corta_si_no_entra(self):
        assert display._recortar("x" * 20, 16) == "x" * 16
