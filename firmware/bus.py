"""Bus de eventos asincrono (pub/sub) para MicroPython.

Desacopla a productores (sensores, comandos) de consumidores (actuadores,
publicador MQTT, pantalla). Cada suscriptor tiene su propio buzon con
capacidad limitada: si se llena, se descarta el evento mas viejo para que un
consumidor lento nunca bloquee al resto del sistema.
"""

import asyncio


class Mailbox:
    """Buzon acotado de un suscriptor."""

    def __init__(self, capacidad=32):
        self._items = []
        self._capacidad = capacidad
        self._hay = asyncio.Event()

    def offer(self, item):
        if len(self._items) >= self._capacidad:
            self._items.pop(0)
        self._items.append(item)
        self._hay.set()

    def size(self):
        return len(self._items)

    async def get(self):
        while not self._items:
            self._hay.clear()
            await self._hay.wait()
        item = self._items.pop(0)
        if not self._items:
            self._hay.clear()
        return item


class Bus:
    """Bus de eventos por topico con soporte de comodin final.

    Suscripciones:
        bus.suscribir("sensor/motion")  -> solo ese topico
        bus.suscribir("sensor/*")       -> cualquier topico bajo "sensor"
        bus.suscribir("*")              -> todos
    """

    def __init__(self, capacidad=32):
        self._capacidad = capacidad
        self._subs = []

    def suscribir(self, patron):
        buzon = Mailbox(self._capacidad)
        self._subs.append((patron, buzon))
        return buzon

    def _coincide(self, patron, topico):
        if patron == "*" or patron == topico:
            return True
        if patron.endswith("/*"):
            return topico.startswith(patron[:-1])
        return False

    def publicar(self, topico, datos=None):
        """Entrega el evento a todos los suscriptores que correspondan."""
        evento = {"topico": topico, "datos": datos}
        entregados = 0
        for patron, buzon in self._subs:
            if self._coincide(patron, topico):
                buzon.offer(evento)
                entregados += 1
        return entregados
