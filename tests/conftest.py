"""Configuracion comun de las pruebas.

Deja el entorno listo (dobles de MicroPython, rutas de importacion) y expone
las fixtures compartidas por las suites de firmware y backend.
"""

from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from tests.support import env, fakes  # noqa: E402

env.preparar()

from backend import config as backend_config  # noqa: E402
from backend.storage import Almacen  # noqa: E402


# ---------------------------------------------------------------------------
# Firmware
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def limpiar_dobles():
    """Cada prueba arranca con los dobles en blanco."""
    fakes.limpiar_registros()
    yield
    fakes.limpiar_registros()


@pytest.fixture
def maquina():
    return env.maquina()


@pytest.fixture
def cfg_firmware():
    import config as firmware_config

    return firmware_config


@pytest.fixture
def reloj():
    """Reloj manual: devuelve (funcion, avanzar)."""
    estado = {"t": 1000.0}

    def ahora():
        return estado["t"]

    def avanzar(segundos):
        estado["t"] += segundos
        return estado["t"]

    ahora.avanzar = avanzar
    return ahora


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------
@pytest.fixture
def cfg_base():
    return backend_config.Config()


@pytest.fixture
def cfg(cfg_base):
    return cfg_base.con(sin_login=True, secreto="secreto-de-prueba")


@pytest.fixture
def carpeta_temporal():
    """Carpeta dentro del proyecto (el sandbox no permite el temporal)."""
    base = RAIZ / "tests" / ".scratch"
    base.mkdir(parents=True, exist_ok=True)
    carpeta = base / ("tmp-" + uuid.uuid4().hex[:10])
    carpeta.mkdir()
    try:
        yield carpeta
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)


@pytest.fixture
def ruta_bd(carpeta_temporal):
    return carpeta_temporal / "centinela.db"


@pytest.fixture
async def almacen(cfg, ruta_bd):
    almacen = Almacen(ruta_bd)
    await almacen.abrir()
    try:
        yield almacen
    finally:
        await almacen.cerrar()


@pytest.fixture
def lectura_ejemplo():
    return {
        "v": 1,
        "device": "dev01",
        "seq": 7,
        "uptime_s": 120,
        "temp_c": 24.6,
        "hum_pct": 58.1,
        "lux": 120.0,
        "dist_cm": 145.0,
        "motion": False,
        "state": "ARMED",
        "alarm": False,
        "siren": False,
        "locked": True,
        "alerts": 0,
        "rssi": -55,
        "sensor_errors": 0,
    }
