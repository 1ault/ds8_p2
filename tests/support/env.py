"""Preparacion del entorno de pruebas.

`preparar()` se ejecuta una sola vez al importar `conftest` y deja en
`sys.modules` los dobles de MicroPython. Es imprescindible hacerlo antes de
importar `ssd1306` (que hace `import framebuf` en la cabecera).
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
FIRMWARE = RAIZ / "firmware"

_preparado = False


def preparar() -> None:
    global _preparado
    if _preparado:
        return
    for ruta in (str(RAIZ), str(FIRMWARE)):
        if ruta not in sys.path:
            sys.path.insert(0, ruta)

    from tests.support import fakes

    fakes.instalar_tiempo()
    fakes.instalar_maquina()
    fakes.instalar_framebuf()
    fakes.instalar_dht()
    fakes.instalar_network()
    _preparado = True


def maquina():
    return sys.modules["machine"]