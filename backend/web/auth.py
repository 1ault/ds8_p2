"""Sesiones del panel mediante cookie firmada con HMAC-SHA256.

No se guarda estado en el servidor: la cookie lleva el usuario y la caducidad,
y la firma impide que se manipule. La comparacion usa `compare_digest` para no
filtrar informacion por tiempo de respuesta.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

NOMBRE_COOKIE = "centinela_sesion"
DURACION_S = 8 * 3600


def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).decode("ascii").rstrip("=")


def _de_b64(texto: str) -> bytes:
    relleno = "=" * (-len(texto) % 4)
    return base64.urlsafe_b64decode(texto + relleno)


def _firma(cuerpo: str, secreto: str) -> str:
    return hmac.new(secreto.encode("utf-8"), cuerpo.encode("utf-8"),
                    hashlib.sha256).hexdigest()


def crear_token(usuario: str, secreto: str, duracion_s: int = DURACION_S) -> str:
    """Genera un token 'cuerpo.firma' para el usuario indicado."""
    payload = {"u": usuario, "exp": int(time.time()) + duracion_s}
    cuerpo = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return "%s.%s" % (cuerpo, _firma(cuerpo, secreto))


def verificar_token(token: str | None, secreto: str) -> dict | None:
    """Devuelve el payload si la firma cuadra y no expiro; si no, None."""
    if not token or "." not in token:
        return None
    cuerpo, _, firma = token.partition(".")
    esperada = _firma(cuerpo, secreto)
    if not hmac.compare_digest(firma, esperada):
        return None
    try:
        payload = json.loads(_de_b64(cuerpo).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


def credenciales_validas(usuario: str, clave: str, cfg) -> bool:
    """Compara usuario y clave en tiempo constante."""
    usuario_ok = hmac.compare_digest((usuario or "").encode("utf-8"),
                                     cfg.usuario.encode("utf-8"))
    clave_ok = hmac.compare_digest((clave or "").encode("utf-8"),
                                   cfg.clave.encode("utf-8"))
    return usuario_ok and clave_ok
