"""Diagnostico aislado: PIR -> FSM -> OLED/buzzer con los modulos REALES.

No usa Wokwi: levanta el firmware en CPython con los dobles de `tests/support`
y simula el pulso del sensor de movimiento (Wokwi deja OUT en ALTO 5 s).

Cubre los seis escenarios que se ven en el simulador y dice, en cada uno, si
llega a ALARMA con sirena. Sirve para separar "el codigo no reacciona" de "el
sensor o el cableado no llegan".

Uso:
    python scripts/diagnostico_pir.py            # casos 1..6
    python scripts/diagnostico_pir.py --solo 3   # un caso suelto
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from tests.support import env, fakes  # noqa: E402

env.preparar()

import actuators  # noqa: E402
import app as app_mod  # noqa: E402
import config as cfg  # noqa: E402
import display  # noqa: E402
import fsm  # noqa: E402
import sensors  # noqa: E402


class ClienteFalso:
    conectado = True

    async def publicar(self, topico, payload, qos=0, retain=False):
        return True

    async def cerrar(self):
        self.conectado = False


class WifiFalsa:
    def rssi(self):
        return -55


def pin(numero):
    encontrados = [p for p in fakes.DoblePin.instancias if p.numero == numero]
    return encontrados[-1] if encontrados else None


def pwm(numero):
    for p in fakes.DoblePWM.instancias:
        if getattr(p.pin, "numero", None) == numero:
            return p
    return None


def construir(reloj):
    fakes.limpiar_registros()
    panel = actuators.construir_desde_config(cfg=cfg)
    suite = sensors.construir_desde_config(cfg=cfg)
    pantalla = display.construir_desde_config(cfg=cfg)
    controlador = app_mod.Controlador(
        cfg=cfg,
        wifi=WifiFalsa(),
        cliente=ClienteFalso(),
        sensores=suite,
        panel=panel,
        pantalla=pantalla,
        maquina=fsm.crear_desde_config(cfg=cfg),
        boton=False,
        reloj=reloj,
    )
    return controlador, pantalla


def renglones_oled(controlador, pantalla):
    """Pinta la pantalla real y devuelve sus renglones visibles."""
    pantalla.mostrar(controlador.datos_pantalla())
    oled = getattr(pantalla, "_oled", None)
    fb = getattr(oled, "_fb", None) or getattr(oled, "fb", None)
    textos = {}
    for texto, _x, y in getattr(fb, "textos", []):
        textos[y] = texto
    return textos


def resumen(controlador, pantalla, etiqueta):
    datos = controlador.datos_pantalla()
    oled = renglones_oled(controlador, pantalla)
    p = pwm(cfg.PIN_BUZZER)
    print("\n  --- %s ---" % etiqueta)
    print("  estado=%s alertas=%d sonando=%s buzzer.activo=%s PWM_u16=%s"
          % (controlador.maquina.estado, controlador.maquina.alertas,
             controlador.maquina.sonando, controlador.panel.buzzer.activo,
             getattr(p, "_duty_u16", "n/a")))
    print("  OLED: %s" % " | ".join(str(oled.get(y, ""))
                                    for y in sorted(oled)))
    return datos


async def caso(reloj, salida_s, inicio_pulso, pulso_s, armar=True):
    """Arma, deja el PIR en ALTO el tiempo indicado y mira el resultado."""
    controlador, pantalla = construir(reloj)
    controlador.maquina.salida_s = salida_s
    p_pir = pin(cfg.PIN_PIR)

    tareas = [
        asyncio.create_task(controlador._bucle_sensores()),
        asyncio.create_task(controlador._bucle_leds()),
        asyncio.create_task(controlador._bucle_pantalla()),
    ]
    try:
        if armar:
            await controlador.procesar_comando({"cmd": "arm"})
        else:
            resumen(controlador, pantalla, "desarmado, PIR en reposo")

        await asyncio.sleep(inicio_pulso)
        p_pir.simular(1)
        print("  PIR -> ALTO (%.1f s)" % pulso_s)
        await asyncio.sleep(pulso_s)
        p_pir.simular(0)
        # Margen para que termine la cuenta regresiva y se resuelva el ciclo.
        margen = max(0.0, salida_s - (inicio_pulso + pulso_s)) + 0.8
        await asyncio.sleep(margen)
        return resumen(controlador, pantalla, "resultado")
    finally:
        for tarea in tareas:
            tarea.cancel()
        await asyncio.sleep(0)


CASOS = [
    # numero, titulo, reloj, salida_s, inicio_pulso, pulso_s, armar, espera_alarma
    (1, "pulso despues de ARMADO (reloj float)", "float", 2.0, 3.0, 5.0, True, True),
    (2, "pulso despues de ARMADO (reloj entero ESP32)", "int", 2.0, 3.0, 5.0, True, True),
    (3, "pulso empieza durante la cuenta y sigue al armar", "int", 3.0, 0.5, 5.0, True, True),
    (4, "pulso empieza durante la cuenta y sigue al armar", "float", 3.0, 0.5, 5.0, True, True),
    (5, "pulso entero dentro de la cuenta regresiva", "float", 10.0, 0.5, 2.0, True, True),
    (6, "pulso con el sistema desarmado", "float", 2.0, 0.5, 2.0, False, False),
]


async def main(solo=None):
    relojes = {"float": time.time, "int": lambda: int(time.monotonic())}
    fallas = 0
    for (numero, titulo, tipo_reloj, salida_s, inicio_pulso, pulso_s,
         armar, espera_alarma) in CASOS:
        if solo and numero not in solo:
            continue
        print("\n" + "=" * 72)
        print("CASO %d: %s" % (numero, titulo))
        print("  reloj=%s salida=%.1fs pulso=%.1fs desde t=%.1fs, armado=%s"
              % (tipo_reloj, salida_s, pulso_s, inicio_pulso, armar))
        print("=" * 72)
        datos = await caso(relojes[tipo_reloj], salida_s, inicio_pulso,
                           pulso_s, armar=armar)
        hubo = datos["state"] == fsm.ALARMA and datos["siren"]
        ok = hubo == espera_alarma
        if not ok:
            fallas += 1
        print("\n  >>> esperado: %s | obtenido: %s | %s"
              % ("ALARMA + sirena" if espera_alarma else "sin alarma",
                 "ALARMA + sirena" if hubo else "sin alarma",
                 "OK" if ok else "FALLA"))
    print("\n%d caso(s) con falla" % fallas)
    return fallas


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solo", type=int, nargs="*", default=None)
    argumentos = parser.parse_args()
    sys.exit(1 if asyncio.run(main(argumentos.solo)) else 0)
