"""Cliente MQTT 3.1.1 minimo sobre asyncio streams.

Implementa lo que el proyecto necesita: CONNECT con Last Will, SUBSCRIBE,
PUBLISH en QoS 0 y QoS 1 con confirmacion (PUBACK), PINGREQ para el keepalive
y reconexion con backoff exponencial. No depende de librerias externas, que en
MicroPython no existen para MQTT.

La primera mitad del modulo es el *codificador de paquetes* (funciones puras),
lo que permite probarlo byte a byte sin red.
"""

import asyncio

# Tipos de paquete (nibble alto del primer byte)
CONNECT = 1
CONNACK = 2
PUBLISH = 3
PUBACK = 4
SUBSCRIBE = 8
SUBACK = 9
PINGREQ = 12
PINGRESP = 13
DISCONNECT = 14

_CANCELADO = getattr(asyncio, "CancelledError", ())


# ---------------------------------------------------------------------------
# Codificacion (funciones puras)
# ---------------------------------------------------------------------------
def longitud_restante(n):
    """Codifica la longitud restante en formato variable (1-4 bytes)."""
    if n < 0 or n > 268435455:
        raise ValueError("longitud fuera de rango MQTT")
    salida = bytearray()
    while True:
        byte = n % 128
        n //= 128
        if n > 0:
            byte = byte | 0x80
        salida.append(byte)
        if n == 0:
            return bytes(salida)


def cadena(texto):
    """Cadena MQTT: 2 bytes de longitud + UTF-8."""
    if isinstance(texto, str):
        datos = texto.encode("utf-8")
    else:
        datos = texto
    if len(datos) > 65535:
        raise ValueError("cadena MQTT demasiado larga")
    return bytes([len(datos) >> 8, len(datos) & 0xFF]) + datos


def _paquete(tipo, cuerpo):
    return bytes([tipo]) + longitud_restante(len(cuerpo)) + cuerpo


def encode_connect(client_id, keepalive=30, will_topic=None, will_msg=None,
                   will_qos=1, will_retain=True, usuario=None, clave=None,
                   clean=True):
    """Paquete CONNECT completo (protocolo MQTT 3.1.1, nivel 4)."""
    flags = 0
    if clean:
        flags |= 0x02
    if will_topic is not None:
        flags |= 0x04 | ((will_qos & 0x03) << 3)
        if will_retain:
            flags |= 0x20
    if usuario:
        flags |= 0x80
    if clave:
        flags |= 0x40

    variable = cadena("MQTT") + bytes([4, flags]) + bytes(
        [keepalive >> 8, keepalive & 0xFF]
    )
    payload = cadena(client_id)
    if will_topic is not None:
        payload += cadena(will_topic)
        if isinstance(will_msg, str):
            will_msg = will_msg.encode("utf-8")
        payload += bytes([len(will_msg) >> 8, len(will_msg) & 0xFF]) + will_msg
    if usuario:
        payload += cadena(usuario)
    if clave:
        payload += cadena(clave)
    return _paquete(CONNECT << 4, variable + payload)


def encode_publish(topic, payload, qos=0, retain=False, packet_id=None,
                   dup=False):
    """Paquete PUBLISH. Para QoS > 0 exige identificador de paquete."""
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    tipo = (PUBLISH << 4) | ((qos & 0x03) << 1)
    if retain:
        tipo |= 0x01
    if dup:
        tipo |= 0x08
    cuerpo = cadena(topic)
    if qos > 0:
        if packet_id is None:
            raise ValueError("QoS>0 requiere packet_id")
        cuerpo += bytes([packet_id >> 8, packet_id & 0xFF])
    return _paquete(tipo, cuerpo + payload)


def encode_subscribe(packet_id, topicos):
    """SUSCRIBE con lista de (topico, qos)."""
    cuerpo = bytes([packet_id >> 8, packet_id & 0xFF])
    for topico, qos in topicos:
        cuerpo += cadena(topico) + bytes([qos & 0x03])
    return _paquete((SUBSCRIBE << 4) | 0x02, cuerpo)


def encode_puback(packet_id):
    return _paquete(PUBACK << 4, bytes([packet_id >> 8, packet_id & 0xFF]))


def encode_pingreq():
    return _paquete(PINGREQ << 4, b"")


def encode_disconnect():
    return _paquete(DISCONNECT << 4, b"")


# ---------------------------------------------------------------------------
# Decodificacion
# ---------------------------------------------------------------------------
async def _leer_longitud(lector):
    multiplicador = 1
    valor = 0
    for _ in range(4):
        byte = await lector.read(1)
        if not byte:
            raise ConnectionError("conexion cerrada al leer longitud")
        b = byte[0]
        valor += (b & 0x7F) * multiplicador
        if not (b & 0x80):
            return valor
        multiplicador *= 128
    raise ValueError("longitud restante invalida")


def _leer_cadena(cuerpo, pos):
    if pos + 2 > len(cuerpo):
        raise ValueError("cadena truncada")
    largo = (cuerpo[pos] << 8) | cuerpo[pos + 1]
    inicio = pos + 2
    if inicio + largo > len(cuerpo):
        raise ValueError("cadena truncada")
    return cuerpo[inicio:inicio + largo].decode("utf-8", "replace"), inicio + largo


async def leer_paquete(lector):
    """Lee un paquete completo. Devuelve (tipo, flags, cuerpo)."""
    cabeza = await lector.read(1)
    if not cabeza:
        raise ConnectionError("conexion cerrada")
    primero = cabeza[0]
    tipo = primero >> 4
    flags = primero & 0x0F
    largo = await _leer_longitud(lector)
    cuerpo = b""
    while len(cuerpo) < largo:
        trozo = await lector.read(largo - len(cuerpo))
        if not trozo:
            raise ConnectionError("conexion cerrada durante el paquete")
        cuerpo += trozo
    return tipo, flags, cuerpo


def parse_publish(flags, cuerpo):
    """Interpreta un PUBLISH recibido: (topico, payload, qos, retain, id)."""
    qos = (flags >> 1) & 0x03
    retain = bool(flags & 0x01)
    topico, pos = _leer_cadena(cuerpo, 0)
    packet_id = None
    if qos > 0:
        if pos + 2 > len(cuerpo):
            raise ValueError("PUBLISH sin identificador")
        packet_id = (cuerpo[pos] << 8) | cuerpo[pos + 1]
        pos += 2
    return topico, cuerpo[pos:], qos, retain, packet_id


def parse_connack(cuerpo):
    if len(cuerpo) < 2:
        raise ValueError("CONNACK invalido")
    return bool(cuerpo[0] & 0x01), cuerpo[1]


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------
class MqttClient:
    """Cliente MQTT asincrono con Last Will y QoS 1."""

    def __init__(self, host, port=1883, client_id="centinela", keepalive=30,
                 tls=False, usuario="", clave="", log=None,
                 timeout_ack_s=5.0):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.keepalive = keepalive or 30
        self.tls = tls
        self.usuario = usuario
        self.clave = clave
        self.timeout_ack_s = timeout_ack_s
        self._log = log or (lambda mensaje: None)

        self.conectado = False
        self.on_message = None
        self.on_conectado = None

        self._lector = None
        self._escritor = None
        self._lock = asyncio.Lock()
        self._id = 0
        self._acks = {}
        self._tareas = []
        self._caida = asyncio.Event()
        self.ultimo_ping = 0
        self.publicados = 0
        self.recibidos = 0

    # -- utilidades --------------------------------------------------------
    def _siguiente_id(self):
        self._id += 1
        if self._id > 65535:
            self._id = 1
        return self._id

    async def _enviar(self, datos):
        if self._escritor is None:
            raise ConnectionError("sin conexion MQTT")
        async with self._lock:
            self._escritor.write(datos)
            await self._escritor.drain()
        return len(datos)

    # -- ciclo de vida -----------------------------------------------------
    async def conectar(self, will_topic=None, will_msg=None):
        """Abre el socket, envia CONNECT y espera el CONNACK."""
        if self.tls:
            import ssl as _ssl

            contexto = _ssl.SSLContext(_ssl.PROTOCOL_TLS_CLIENT)
            contexto.verify_mode = _ssl.CERT_NONE
            contexto.check_hostname = False
            self._lector, self._escritor = await asyncio.open_connection(
                self.host, self.port, ssl=contexto
            )
        else:
            self._lector, self._escritor = await asyncio.open_connection(
                self.host, self.port
            )

        saludo = encode_connect(
            self.client_id, self.keepalive, will_topic, will_msg,
            will_qos=1, will_retain=True,
            usuario=self.usuario or None, clave=self.clave or None,
        )
        await self._enviar(saludo)

        try:
            tipo, _flags, cuerpo = await asyncio.wait_for(
                leer_paquete(self._lector), 10
            )
        except Exception:
            await self.cerrar()
            raise

        if tipo != CONNACK:
            await self.cerrar()
            raise ConnectionError("se esperaba CONNACK y llego %d" % tipo)
        _sesion, codigo = parse_connack(cuerpo)
        if codigo != 0:
            await self.cerrar()
            raise ConnectionError("CONNACK rechazado (codigo %d)" % codigo)

        self.conectado = True
        self._caida.clear()
        self._tareas = [asyncio.create_task(self._bucle_lectura())]
        if self.keepalive:
            self._tareas.append(asyncio.create_task(self._bucle_keepalive()))
        if self.on_conectado:
            self.on_conectado()
        self._log("MQTT conectado a %s:%d" % (self.host, self.port))
        return True

    async def cerrar(self):
        """Cierra la conexion y detiene las tareas internas."""
        self.conectado = False
        for tarea in self._tareas:
            tarea.cancel()
        self._tareas = []
        escritor = self._escritor
        self._escritor = None
        self._lector = None
        if escritor is not None:
            try:
                escritor.close()
            except Exception:  # noqa: BLE001
                pass
            try:
                await escritor.wait_closed()
            except Exception:  # noqa: BLE001
                pass
        self._caida.set()

    async def esperar_caida(self):
        """Se bloquea hasta que la conexion se pierda."""
        await self._caida.wait()

    # -- operaciones -------------------------------------------------------
    async def suscribir(self, topicos):
        if not self.conectado:
            raise ConnectionError("sin conexion MQTT")
        packet_id = self._siguiente_id()
        evento = asyncio.Event()
        self._acks[("sub", packet_id)] = evento
        await self._enviar(encode_subscribe(packet_id, topicos))
        try:
            await asyncio.wait_for(evento.wait(), self.timeout_ack_s)
        except asyncio.TimeoutError:
            self._log("sin SUBACK para %s" % str(topicos))
            return False
        finally:
            self._acks.pop(("sub", packet_id), None)
        return True

    async def publicar(self, topic, payload, qos=0, retain=False):
        """Publica y, en QoS 1, espera el PUBACK."""
        if not self.conectado:
            raise ConnectionError("sin conexion MQTT")
        packet_id = self._siguiente_id() if qos > 0 else None
        evento = None
        if qos > 0:
            evento = asyncio.Event()
            self._acks[packet_id] = evento
        await self._enviar(encode_publish(topic, payload, qos, retain, packet_id))
        self.publicados += 1
        if qos > 0:
            try:
                await asyncio.wait_for(evento.wait(), self.timeout_ack_s)
            except asyncio.TimeoutError:
                self._log("sin PUBACK para %s" % topic)
                return False
            finally:
                self._acks.pop(packet_id, None)
        return True

    # -- tareas internas ---------------------------------------------------
    async def _bucle_lectura(self):
        try:
            while self.conectado:
                tipo, flags, cuerpo = await leer_paquete(self._lector)
                if tipo == PUBLISH:
                    topico, payload, qos, retain, packet_id = parse_publish(
                        flags, cuerpo
                    )
                    self.recibidos += 1
                    if qos == 1 and packet_id is not None:
                        await self._enviar(encode_puback(packet_id))
                    if self.on_message:
                        self.on_message(topico, payload, qos, retain)
                elif tipo == PUBACK:
                    packet_id = (cuerpo[0] << 8) | cuerpo[1]
                    evento = self._acks.get(packet_id)
                    if evento is not None:
                        evento.set()
                elif tipo == SUBACK:
                    packet_id = (cuerpo[0] << 8) | cuerpo[1]
                    evento = self._acks.get(("sub", packet_id))
                    if evento is not None:
                        evento.set()
                elif tipo == PINGRESP:
                    self.ultimo_ping = 0
        except _CANCELADO:
            raise
        except Exception as exc:  # noqa: BLE001
            self._log("lectura MQTT interrumpida: %s" % exc)
        finally:
            self.conectado = False
            self._caida.set()

    async def _bucle_keepalive(self):
        intervalo = max(1.0, self.keepalive / 2.0)
        try:
            while self.conectado:
                await asyncio.sleep(intervalo)
                if not self.conectado:
                    return
                await self._enviar(encode_pingreq())
                self.ultimo_ping += 1
                if self.ultimo_ping > 3:
                    self._log("keepalive sin respuesta")
                    self.conectado = False
                    self._caida.set()
                    return
        except _CANCELADO:
            raise
        except Exception as exc:  # noqa: BLE001
            self._log("keepalive interrumpido: %s" % exc)
            self._caida.set()


async def conectar_con_reintentos(cliente, topicos, will_topic=None,
                                  will_msg="offline", minimo_s=2, maximo_s=60,
                                  log=None, intentos=None):
    """Conecta y suscribe con backoff exponencial.

    Devuelve True al conectar. Si se alcanza el limite de intentos devuelve
    False; sin limite, reintenta indefinidamente.
    """
    log = log or (lambda mensaje: None)
    espera = minimo_s
    cuenta = 0
    while intentos is None or cuenta < intentos:
        cuenta += 1
        try:
            await cliente.conectar(will_topic, will_msg)
            if topicos:
                await cliente.suscribir(topicos)
            return True
        except _CANCELADO:
            raise
        except Exception as exc:  # noqa: BLE001
            log("conexion MQTT fallida (%s); reintento en %ds" % (exc, espera))
            await asyncio.sleep(espera)
            espera = min(maximo_s, espera * 2)
    return False
