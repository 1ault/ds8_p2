# Bus de eventos asincrono (pub/sub) para MicroPython.
#
# QUE ES UN BUS DE EVENTOS
# ------------------------
# Imaginalo como el altavoz de una escuela: alguien habla por el altavoz y lo
# escuchan todos los que estan en el patio. El que habla **no sabe** quien
# escucha, y no tiene que esperarlos.
#
# En este proyecto el bus conecta al **callback de MQTT** (que es una funcion
# normal, sincrona, y no puede esperar) con los **bucles asincronos** que
# procesan los comandos. El callback solo deja el mensaje en un buzon y sigue;
# el bucle lo recoge cuando puede. Asi una red lenta nunca bloquea al resto.
#
# DOS PIEZAS
# ----------
# * **Mailbox** (buzon): una cola chica con tope. Si se llena, se descarta el
#   mensaje mas viejo: es preferible perder un comando repetido a quedar
#   colgado sin atender nada.
# * **Bus**: la lista de suscriptores con su patron de topico.
#
# ``asyncio.Event`` es como una bandera con timbre: el que espera se duerme con
# `await` y el que publica la levanta (`set()`) para despertarlo.

import asyncio


class Mailbox:
    # Buzon acotado de un suscriptor.

    def __init__(self, capacidad=32):
        self._items = []
        self._capacidad = capacidad
        # Bandera que se levanta cuando hay algo nuevo para leer.
        self._hay = asyncio.Event()

    def offer(self, item):
        # Deja un elemento. Si el buzon esta lleno, tira el mas viejo.
        #
        #         `pop(0)` saca el primero de la lista (el mas antiguo).
        if len(self._items) >= self._capacidad:
            self._items.pop(0)
        self._items.append(item)
        self._hay.set()

    def size(self):
        # Cuantos elementos hay esperando (util en las pruebas).
        return len(self._items)

    async def get(self):
        # Espera (sin gastar CPU) hasta que haya algo y lo devuelve.
        #
        #         El `while` existe porque entre `clear()` y `wait()` podria entrar algo:
        #         se vuelve a comprobar antes de dormirse.
        while not self._items:
            self._hay.clear()
            await self._hay.wait()
        item = self._items.pop(0)
        if not self._items:
            self._hay.clear()
        return item


class Bus:
    # Bus de eventos por topico con soporte de comodin final.
    #
    #     Suscripciones:
    #         bus.suscribir("sensor/motion")  -> solo ese topico
    #         bus.suscribir("sensor/*")       -> cualquier topico bajo "sensor"
    #         bus.suscribir("*")              -> todos

    def __init__(self, capacidad=32):
        self._capacidad = capacidad
        self._subs = []

    def suscribir(self, patron):
        # Anota un suscriptor y devuelve su buzon (ahi va a recibir).
        buzon = Mailbox(self._capacidad)
        self._subs.append((patron, buzon))
        return buzon

    def _coincide(self, patron, topico):
        # True si el patron del suscriptor acepta ese topico.
        #
        #         `patron.endswith("/*")` mira el final de la cadena y
        #         `topico.startswith(patron[:-1])` recorta el `*` para comparar el
        #         prefijo: "sensor/*" queda como "sensor/".
        if patron == "*" or patron == topico:
            return True
        if patron.endswith("/*"):
            return topico.startswith(patron[:-1])
        return False

    def publicar(self, topico, datos=None):
        # Entrega el evento a todos los suscriptores que correspondan.
        evento = {"topico": topico, "datos": datos}
        entregados = 0
        for patron, buzon in self._subs:
            if self._coincide(patron, topico):
                buzon.offer(evento)
                entregados += 1
        return entregados
