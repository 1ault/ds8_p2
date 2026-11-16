"""Bus de eventos en proceso para empujar cambios al panel por SSE.

Cada cliente conectado al panel tiene su propia cola acotada. Si un navegador
se queda atras, se descarta el evento mas viejo en lugar de bloquear al
productor: una pestana congelada no puede tumbar el backend.
"""

from __future__ import annotations

import asyncio
from typing import Any


class Suscriptor:
    """Cola acotada de un cliente SSE."""

    def __init__(self, capacidad: int = 64):
        self._cola: asyncio.Queue = asyncio.Queue(maxsize=capacidad)
        self.descartados = 0

    def ofrecer(self, evento: dict) -> None:
        try:
            self._cola.put_nowait(evento)
        except asyncio.QueueFull:
            self.descartados += 1
            try:
                self._cola.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                self._cola.put_nowait(evento)
            except asyncio.QueueFull:
                pass

    async def siguiente(self, timeout: float | None = None) -> dict | None:
        if timeout is None:
            return await self._cola.get()
        try:
            return await asyncio.wait_for(self._cola.get(), timeout)
        except asyncio.TimeoutError:
            return None

    def pendientes(self) -> int:
        return self._cola.qsize()


class Hub:
    """Registro de suscriptores y publicacion de eventos."""

    def __init__(self, capacidad: int = 64):
        self._capacidad = capacidad
        self._suscriptores: set[Suscriptor] = set()
        self.publicados = 0

    def suscribir(self) -> Suscriptor:
        suscriptor = Suscriptor(self._capacidad)
        self._suscriptores.add(suscriptor)
        return suscriptor

    def baja(self, suscriptor: Suscriptor) -> None:
        self._suscriptores.discard(suscriptor)

    def publicar(self, tipo: str, datos: Any) -> int:
        """Publica un evento de tipo `tipo` con datos serializables."""
        self.publicados += 1
        evento = {"tipo": tipo, "datos": datos}
        for suscriptor in list(self._suscriptores):
            suscriptor.ofrecer(evento)
        return len(self._suscriptores)

    def clientes(self) -> int:
        return len(self._suscriptores)
