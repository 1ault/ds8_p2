"""Pruebas de la maquina de estados de seguridad (logica pura)."""

from __future__ import annotations

import fsm
import pytest

T0 = 100.0


def crear(**cambios) -> fsm.SecurityFSM:
    opciones = dict(salida_s=10, auto_cierre_s=8, sirena_max_s=120,
                    dist_alarma_cm=80.0, temp_alarma_c=45.0, pin="2468",
                    intentos_pin=3, bloqueo_pin_s=30)
    opciones.update(cambios)
    return fsm.SecurityFSM(**opciones)


def efectos(lista):
    return [efecto["e"] for efecto in lista]


def armar(maquina, ahora=T0):
    return maquina.handle(ahora, {"type": "command", "cmd": "arm"})


def armar_del_todo(maquina, ahora=T0):
    armar(maquina, ahora)
    maquina.tick(ahora + maquina.salida_s)
    assert maquina.estado == fsm.ARMADO
    return ahora + maquina.salida_s


class TestEstadoInicial:
    def test_arranca_desarmado_y_cerrado(self):
        maquina = crear()
        assert maquina.estado == fsm.DESARMADO
        assert maquina.cerrada is True
        assert maquina.sonando is False
        assert maquina.alertas == 0

    def test_armado_es_falso_al_inicio(self):
        assert crear().armado() is False

    def test_resumen_tiene_las_claves_del_contrato(self):
        resumen = crear().resumen()
        assert set(resumen) == {"state", "locked", "alarming", "siren",
                               "muted", "alerts", "last_reason"}
        assert resumen["state"] == fsm.DESARMADO


class TestArmado:
    def test_armar_inicia_cuenta_regresiva(self):
        maquina = crear()
        salida = armar(maquina)
        assert maquina.estado == fsm.ARMANDO
        assert fsm.FX_AVISO in efectos(salida)
        assert maquina.armado() is True

    def test_restante_de_salida_decrece(self):
        maquina = crear(salida_s=10)
        armar(maquina, T0)
        assert maquina.restante_salida(T0) == pytest.approx(10.0)
        assert maquina.restante_salida(T0 + 4) == pytest.approx(6.0)

    def test_no_arma_antes_del_plazo(self):
        maquina = crear(salida_s=10)
        armar(maquina, T0)
        maquina.tick(T0 + 9.9)
        assert maquina.estado == fsm.ARMANDO

    def test_arma_al_cumplir_el_plazo(self):
        maquina = crear(salida_s=10)
        armar(maquina, T0)
        salida = maquina.tick(T0 + 10)
        assert maquina.estado == fsm.ARMADO
        assert efectos(salida) == [fsm.FX_AVISO]

    def test_armar_dos_veces_no_reinicia_la_cuenta(self):
        maquina = crear(salida_s=10)
        armar(maquina, T0)
        armar(maquina, T0 + 5)
        assert maquina.restante_salida(T0 + 5) == pytest.approx(5.0)

    def test_armar_cierra_la_cerradura_si_estaba_abierta(self):
        maquina = crear()
        maquina.handle(T0, {"type": "command", "cmd": "unlock", "pin": "2468"})
        assert maquina.cerrada is False
        salida = armar(maquina, T0 + 1)
        assert fsm.FX_CERRAR in efectos(salida)
        assert maquina.cerrada is True


class TestDesarmado:
    def test_desarmar_desde_armando_cancela_la_cuenta(self):
        maquina = crear()
        armar(maquina, T0)
        maquina.handle(T0 + 2, {"type": "command", "cmd": "disarm"})
        assert maquina.estado == fsm.DESARMADO
        maquina.tick(T0 + 50)
        assert maquina.estado == fsm.DESARMADO

    def test_desarmar_desde_armado(self):
        maquina = crear()
        instante = armar_del_todo(maquina)
        maquina.handle(instante, {"type": "command", "cmd": "disarm"})
        assert maquina.estado == fsm.DESARMADO

    def test_desarmar_cuando_ya_esta_desarmado_es_idempotente(self):
        maquina = crear()
        salida = maquina.handle(T0, {"type": "command", "cmd": "disarm"})
        assert maquina.estado == fsm.DESARMADO
        assert fsm.FX_AVISO in efectos(salida)

    def test_desarmar_no_desbloquea_la_cerradura(self):
        maquina = crear()
        maquina.handle(T0, {"type": "command", "cmd": "unlock", "pin": "2468"})
        maquina.handle(T0 + 1, {"type": "command", "cmd": "disarm"})
        assert maquina.cerrada is True


class TestDeteccion:
    def test_presencia_desarmado_no_dispara(self):
        maquina = crear()
        salida = maquina.handle(T0, {"type": "presence", "motivo": "movimiento"})
        assert salida == []
        assert maquina.estado == fsm.DESARMADO
        assert maquina.alertas == 0

    def test_presencia_durante_armado_no_dispara(self):
        maquina = crear()
        armar(maquina, T0)
        maquina.handle(T0 + 1, {"type": "presence", "motivo": "movimiento"})
        assert maquina.estado == fsm.ARMANDO

    def test_presencia_armado_dispara_alarma(self):
        maquina = crear()
        instante = armar_del_todo(maquina)
        salida = maquina.handle(instante, {"type": "presence", "motivo": "movimiento"})
        assert maquina.estado == fsm.ALARMA
        assert maquina.alertas == 1
        assert maquina.sonando is True
        assert fsm.FX_ALERTA in efectos(salida)
        assert fsm.FX_SIRENA_ON in efectos(salida)

    def test_presencia_cercana_registra_la_distancia(self):
        maquina = crear()
        instante = armar_del_todo(maquina)
        salida = maquina.handle(instante, {"type": "presence", "cm": 42.0})
        alerta = [e for e in salida if e["e"] == fsm.FX_ALERTA][0]
        assert alerta["motivo"] == "presencia_cercana"
        assert alerta["cm"] == 42.0

    def test_presencia_en_alarma_suma_alertas(self):
        maquina = crear(cooldown_alerta_s=5)
        instante = armar_del_todo(maquina)
        maquina.handle(instante, {"type": "presence"})
        maquina.handle(instante + 6, {"type": "presence"})
        assert maquina.alertas == 2

    def test_presencia_repetida_no_infla_las_alertas(self):
        maquina = crear(cooldown_alerta_s=5)
        instante = armar_del_todo(maquina)
        maquina.handle(instante, {"type": "presence"})
        assert maquina.handle(instante + 0.5, {"type": "presence"}) == []
        assert maquina.alertas == 1

    def test_temperatura_alta_armado_dispara_alarma(self):
        maquina = crear()
        instante = armar_del_todo(maquina)
        salida = maquina.handle(instante, {"type": "temperature", "c": 60.0})
        assert maquina.estado == fsm.ALARMA
        assert maquina.ultimo_motivo == "sobrecalentamiento"
        assert fsm.FX_ALERTA in efectos(salida)

    def test_temperatura_alta_desarmado_solo_avisa(self):
        maquina = crear()
        salida = maquina.handle(T0, {"type": "temperature", "c": 60.0})
        assert maquina.estado == fsm.DESARMADO
        aviso = [e for e in salida if e["e"] == fsm.FX_AVISO][0]
        assert aviso["motivo"] == "temperatura_alta"

    def test_temperatura_normal_no_hace_nada(self):
        maquina = crear()
        instante = armar_del_todo(maquina)
        assert maquina.handle(instante, {"type": "temperature", "c": 24.0}) == []

    def test_temperatura_sin_valor_se_ignora(self):
        assert crear().handle(T0, {"type": "temperature", "c": None}) == []


class TestSirena:
    def test_desarmar_en_alarma_apaga_la_sirena(self):
        maquina = crear()
        instante = armar_del_todo(maquina)
        maquina.handle(instante, {"type": "presence"})
        salida = maquina.handle(instante + 1, {"type": "command", "cmd": "disarm"})
        assert maquina.sonando is False
        assert fsm.FX_SIRENA_OFF in efectos(salida)

    def test_silenciar_en_alarma_apaga_sin_desarmar(self):
        maquina = crear()
        instante = armar_del_todo(maquina)
        maquina.handle(instante, {"type": "presence"})
        salida = maquina.handle(instante + 1, {"type": "command", "cmd": "mute"})
        assert maquina.silenciada is True
        assert maquina.sonando is False
        assert maquina.estado == fsm.ALARMA
        assert fsm.FX_SIRENA_OFF in efectos(salida)

    def test_silenciar_desarmado_no_hace_nada(self):
        maquina = crear()
        assert maquina.handle(T0, {"type": "command", "cmd": "mute"}) == []
        assert maquina.silenciada is False

    def test_alarma_silenciada_vuelve_a_sonar_con_nueva_alerta(self):
        maquina = crear(cooldown_alerta_s=5)
        instante = armar_del_todo(maquina)
        maquina.handle(instante, {"type": "presence"})
        maquina.handle(instante + 1, {"type": "command", "cmd": "mute"})
        maquina.handle(instante + 6, {"type": "presence"})
        assert maquina.silenciada is False
        assert maquina.sonando is True
        assert maquina.alertas == 2


class TestCerradura:
    def test_unlock_con_pin_correcto_abre(self):
        maquina = crear()
        salida = maquina.handle(T0, {"type": "command", "cmd": "unlock",
                                     "pin": "2468"})
        assert maquina.cerrada is False
        efecto = [e for e in salida if e["e"] == fsm.FX_ABRIR][0]
        assert efecto["auto_cierre_s"] == 8

    def test_unlock_con_pin_incorrecto_rechaza(self):
        maquina = crear()
        salida = maquina.handle(T0, {"type": "command", "cmd": "unlock",
                                     "pin": "0000"})
        assert maquina.cerrada is True
        rechazo = [e for e in salida if e["e"] == fsm.FX_RECHAZO][0]
        assert rechazo["motivo"] == "pin_incorrecto"

    def test_unlock_estando_armado_se_rechaza(self):
        maquina = crear()
        instante = armar_del_todo(maquina)
        salida = maquina.handle(instante, {"type": "command", "cmd": "unlock",
                                           "pin": "2468"})
        rechazo = [e for e in salida if e["e"] == fsm.FX_RECHAZO][0]
        assert rechazo["motivo"] == "sistema_armado"
        assert maquina.cerrada is True

    def test_tres_pines_erroneos_bloquean(self):
        maquina = crear(intentos_pin=3, bloqueo_pin_s=30)
        for _ in range(3):
            salida = maquina.handle(T0, {"type": "command", "cmd": "unlock",
                                         "pin": "1111"})
        rechazo = [e for e in salida if e["e"] == fsm.FX_RECHAZO][0]
        assert rechazo["motivo"] == "pin_bloqueado"

    def test_bloqueado_rechaza_incluso_el_pin_correcto(self):
        maquina = crear(intentos_pin=1, bloqueo_pin_s=30)
        maquina.handle(T0, {"type": "command", "cmd": "unlock", "pin": "1111"})
        salida = maquina.handle(T0 + 1, {"type": "command", "cmd": "unlock",
                                         "pin": "2468"})
        rechazo = [e for e in salida if e["e"] == fsm.FX_RECHAZO][0]
        assert rechazo["motivo"] == "bloqueado"
        assert maquina.cerrada is True

    def test_el_bloqueo_expira(self):
        maquina = crear(intentos_pin=1, bloqueo_pin_s=30)
        maquina.handle(T0, {"type": "command", "cmd": "unlock", "pin": "1111"})
        maquina.tick(T0 + 31)
        salida = maquina.handle(T0 + 31, {"type": "command", "cmd": "unlock",
                                          "pin": "2468"})
        assert fsm.FX_ABRIR in efectos(salida)
        assert maquina.cerrada is False

    def test_cierre_automatico(self):
        maquina = crear(auto_cierre_s=8)
        maquina.handle(T0, {"type": "command", "cmd": "unlock", "pin": "2468"})
        assert maquina.tick(T0 + 7) == []
        salida = maquina.tick(T0 + 8)
        assert fsm.FX_CERRAR in efectos(salida)
        assert maquina.cerrada is True


class TestVarios:
    def test_comando_desconocido_se_rechaza(self):
        maquina = crear()
        salida = maquina.handle(T0, {"type": "command", "cmd": "autodestruir"})
        rechazo = [e for e in salida if e["e"] == fsm.FX_RECHAZO][0]
        assert rechazo["cmd"] == "autodestruir"

    def test_evento_desconocido_se_ignora(self):
        assert crear().handle(T0, {"type": "terremoto"}) == []

    def test_tick_sin_temporizadores_no_genera_efectos(self):
        assert crear().tick(T0) == []

    def test_crear_desde_config(self, cfg_firmware):
        maquina = fsm.crear_desde_config(cfg_firmware)
        assert maquina.salida_s == cfg_firmware.EXIT_DELAY_S
        assert maquina.pin == cfg_firmware.UNLOCK_PIN
        assert maquina.dist_alarma_cm == cfg_firmware.DIST_ALARM_CM
        assert maquina.temp_alarma_c == cfg_firmware.TEMP_ALARM_C

    def test_armado_incluye_estado_alarma(self):
        maquina = crear()
        instante = armar_del_todo(maquina)
        maquina.handle(instante, {"type": "presence"})
        assert maquina.armado() is True
        assert maquina.en_alarma() is True
