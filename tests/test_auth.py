"""Pruebas de las sesiones firmadas del panel."""

from __future__ import annotations

import time

from backend import config as config_mod
from backend.web import auth


def test_token_valido():
    token = auth.crear_token("admin", "secreto")
    payload = auth.verificar_token(token, "secreto")
    assert payload is not None
    assert payload["u"] == "admin"


def test_token_con_otro_secreto_no_vale():
    token = auth.crear_token("admin", "secreto")
    assert auth.verificar_token(token, "otro") is None


def test_token_manipulado_no_vale():
    token = auth.crear_token("admin", "secreto")
    cuerpo, _, firma = token.partition(".")
    falso = auth._b64(b'{"u":"root","exp":9999999999}') + "." + firma
    assert auth.verificar_token(falso, "secreto") is None


def test_token_caducado():
    token = auth.crear_token("admin", "secreto", duracion_s=-5)
    assert auth.verificar_token(token, "secreto") is None


def test_token_basura():
    assert auth.verificar_token("sin-punto", "x") is None
    assert auth.verificar_token("", "x") is None
    assert auth.verificar_token(None, "x") is None


def test_token_con_cuerpo_invalido():
    cuerpo = "no-es-base64"
    firma = auth._firma(cuerpo, "secreto")
    assert auth.verificar_token("%s.%s" % (cuerpo, firma), "secreto") is None


def test_credenciales_correctas():
    cfg = config_mod.Config(usuario="admin", clave="clave123")
    assert auth.credenciales_validas("admin", "clave123", cfg) is True


def test_credenciales_incorrectas():
    cfg = config_mod.Config(usuario="admin", clave="clave123")
    assert auth.credenciales_validas("admin", "otra", cfg) is False
    assert auth.credenciales_validas("root", "clave123", cfg) is False
    assert auth.credenciales_validas("", "", cfg) is False


def test_duracion_por_defecto_es_de_ocho_horas():
    token = auth.crear_token("admin", "secreto")
    payload = auth.verificar_token(token, "secreto")
    assert payload["exp"] - int(time.time()) > 7 * 3600
