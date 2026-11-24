# Cliente MQTT 3.1.1 minimo sobre asyncio streams.
#
# QUE ES MQTT (en corto)
# ----------------------
# MQTT es un protocolo de mensajeria **publicar / suscribir** con un
# intermediario llamado *broker* (aca `broker.hivemq.com:1883`):
#
#     nodo ESP32  --publica en "centinela/dev01/telemetry"-->  BROKER
#     backend     <--recibe ese topico (esta suscripto)------  BROKER
#
# El que publica **no sabe** quien escucha: escribe en un *topico* (una
# direccion con barras) y el broker reparte copias entre los suscriptos. Es
# distinto de HTTP, donde el cliente pregunta y el servidor responde en esa
# misma conexion.
#
# Vocabulario que aparece abajo:
#
# * **QoS 0**: "a lo sumo una vez". Se manda y no se espera acuse (telemetria).
# * **QoS 1**: "al menos una vez". Se espera un PUBACK; si no llega, se avisa
#   (eventos y comandos).
# * **retain**: el broker guarda el ultimo mensaje del topico y se lo entrega a
#   quien se suscriba despues (lo usa `status` con online/offline).
# * **Last Will (LWT)**: mensaje que el broker publica por el nodo si la
#   conexion se corta sin despedirse (aca deja `offline`).
# * **keepalive**: cada cuantos segundos el nodo manda un PINGREQ para que el
#   broker no lo considere muerto.
#
# COMO ES UN PAQUETE MQTT
# -----------------------
# Encabezado fijo de 2 partes:
#
#     byte 1:            [ tipo (4 bits) | flags (4 bits) ]
#     bytes siguientes:  longitud del resto (formato variable de 1 a 4 bytes)
#     resto:             encabezado variable + payload
#
# Ejemplo: PUBLISH QoS 0 del topico "a" con el texto "b"
#
#     0x30            tipo 3 (PUBLISH) << 4, sin flags
#     0x03            quedan 3 bytes
#     0x00 0x01 'a'   cadena "a": largo en 2 bytes + la letra
#     'b'             payload
#
# Por eso la primera mitad del modulo son funciones **puras** que devuelven
# `bytes` (se prueban byte a byte sin red) y la segunda es el cliente que los
# manda por el socket.
#
# NUMEROS DE DOS BYTES (big-endian)
# ---------------------------------
# MQTT manda los enteros de 16 bits con el byte mas significativo primero. Para
# partir un numero se usan dos operaciones de bits:
#
#     alto = valor >> 8     # correr 8 bits a la derecha = quedarse con el byte de arriba
#     bajo = valor & 0xFF   # mascara de 8 bits        = quedarse con el byte de abajo
#
# y `bytes([alto, bajo])` arma la pareja. Ejemplo con keepalive = 300:
#
#     300             = 0000 0001 0010 1100
#     300 >> 8        = 0000 0000 0000 0001  -> 0x01
#     300 & 0xFF      = 0000 0000 0010 1100  -> 0x2C
#     bytes([0x01, 0x2C])
#
# Al reves, para leer un id que llega del socket:
#
#     packet_id = (cuerpo[0] << 8) | cuerpo[1]
#
# OPERADORES USADOS EN ESTE ARCHIVO
# ---------------------------------
# * `>>`  desplazar a la derecha (dividir por potencias de 2, sin decimales)
# * `<<`  desplazar a la izquierda (multiplicar por potencias de 2)
# * `&`   AND bit a bit: sirve para "quedarse" con ciertos bits (mascara)
# * `|`   OR bit a bit: sirve para "encender" ciertos bits o combinarlos
# * `//`  division entera (tira los decimales: 300 // 128 = 2)
# * `%`   resto de la division (modulo)
# * `0xNN` numero hexadecimal: 0x0F = 15, 0x80 = 128, 0xFF = 255

import asyncio

# Tipos de paquete: van en los 4 bits altos del primer byte.
# El estandar MQTT 3.1.1 (nivel de protocolo 4) fija estos numeros.
CONNECT = 1
CONNACK = 2
PUBLISH = 3
PUBACK = 4
SUBSCRIBE = 8
SUBACK = 9
PINGREQ = 12
PINGRESP = 13
DISCONNECT = 14

# MicroPython no expone `asyncio.CancelledError` en todas las versiones: si no
# existe queda `()` y el `except` simplemente no atrapa nada (no rompe).
_CANCELADO = getattr(asyncio, "CancelledError", ())


# ---------------------------------------------------------------------------
# Codificacion (funciones puras)
# ---------------------------------------------------------------------------
def longitud_restante(n):
    # Codifica la longitud restante en formato variable (1-4 bytes).
    #
    #     Cada byte aporta 7 bits de datos y su bit mas alto (0x80) significa
    #     "sigo": asi un mensaje corto ocupa 1 byte y uno largo crece de a poco.
    #
    #         n = 0    -> 0x00
    #         n = 127  -> 0x7F
    #         n = 128  -> 0x80 0x01
    #
    #     `% 128` se queda con los 7 bits bajos y `// 128` corre el resto. El tope
    #     (268435455 = 0x0FFFFFFF) son 4 bytes de 7 bits; MQTT no permite mas.
    if n < 0 or n > 268435455:
        raise ValueError("longitud fuera de rango MQTT")
    salida = bytearray()
    while True:
        byte = n % 128
        n //= 128
        if n > 0:
            # Queda informacion: se prende el bit de continuacion.
            byte = byte | 0x80
        salida.append(byte)
        if n == 0:
            return bytes(salida)


def cadena(texto):
    # Cadena MQTT: 2 bytes de largo (big-endian) + UTF-8.
    #
    #     Asi viajan el id de cliente, los topicos, el usuario y la clave. Como el
    #     largo va en 2 bytes, el maximo es 65535 caracteres.
    if isinstance(texto, str):
        datos = texto.encode("utf-8")
    else:
        datos = texto
    if len(datos) > 65535:
        raise ValueError("cadena MQTT demasiado larga")
    return bytes([len(datos) >> 8, len(datos) & 0xFF]) + datos


def _paquete(tipo, cuerpo):
    # Encabezado fijo + cuerpo: `[tipo][largo variable][cuerpo]`.
    #
    #     `bytes([tipo])` arma un objeto `bytes` de un solo byte (no una lista de
    #     ints), que es lo que el socket sabe escribir.
    return bytes([tipo]) + longitud_restante(len(cuerpo)) + cuerpo


def encode_connect(client_id, keepalive=30, will_topic=None, will_msg=None,
                   will_qos=1, will_retain=True, usuario=None, clave=None,
                   clean=True):
    # Paquete CONNECT completo (protocolo MQTT 3.1.1, nivel 4).
    #
    #     `CONNECT << 4` pone el tipo (1) en los 4 bits altos y los flags del
    #     paquete (0, CONNECT no usa) en los bajos: el primer byte es 0x10.
    #
    #     Los flags del encabezado variable son un byte de bits:
    #
    #         bit 1 (0x02)  sesion limpia
    #         bit 2 (0x04)  hay Last Will
    #         bits 3-4      QoS del Will  ->  `(will_qos & 0x03) << 3`
    #         bit 5 (0x20)  el Will es retenido
    #         bit 6 (0x40)  hay contrasena
    #         bit 7 (0x80)  hay usuario
    #
    #     El payload lleva, en orden y solo los que existan: client_id, topico del
    #     Will, mensaje del Will, usuario y contrasena.
    flags = 0
    if clean:
        flags |= 0x02
    if will_topic is not None:
        # 0x04 = hay Will; el QoS va en los bits 3-4.
        flags |= 0x04 | ((will_qos & 0x03) << 3)
        if will_retain:
            flags |= 0x20
    if usuario:
        flags |= 0x80
    if clave:
        flags |= 0x40

    # Encabezado variable: "MQTT" + nivel 4 + flags + keepalive (2 bytes).
    variable = cadena("MQTT") + bytes([4, flags]) + bytes(
        [keepalive >> 8, keepalive & 0xFF]
    )
    payload = cadena(client_id)
    if will_topic is not None:
        payload += cadena(will_topic)
        if isinstance(will_msg, str):
            will_msg = will_msg.encode("utf-8")
        # El mensaje del Will es "bytes con largo", no una cadena UTF-8
        # validada, por eso se arma a mano.
        payload += bytes([len(will_msg) >> 8, len(will_msg) & 0xFF]) + will_msg
    if usuario:
        payload += cadena(usuario)
    if clave:
        payload += cadena(clave)
    return _paquete(CONNECT << 4, variable + payload)


def encode_publish(topic, payload, qos=0, retain=False, packet_id=None,
                   dup=False):
    # Paquete PUBLISH. Para QoS > 0 exige identificador de paquete.
    #
    #     Flags del PUBLISH (los 4 bits bajos del primer byte):
    #
    #         bit 0 (0x01)  retain: el broker lo guarda como ultimo del topico
    #         bits 1-2      QoS    ->  `(qos & 0x03) << 1`
    #         bit 3 (0x08)  dup: es un reenvio (el anterior pudo perderse)
    #
    #     Con QoS 0 no hay id porque nadie lo va a confirmar; con QoS 1 o 2 el id
    #     viaja en 2 bytes antes del payload, para que el PUBACK lo repita.
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
    # SUSCRIBE con lista de (topico, qos).
    #
    #     El nibble bajo del primer byte es obligatorio 0x02 en este paquete (lo
    #     exige el estandar). Despues del id van pares topico + 1 byte con el QoS
    #     maximo que aceptamos al recibir.
    cuerpo = bytes([packet_id >> 8, packet_id & 0xFF])
    for topico, qos in topicos:
        cuerpo += cadena(topico) + bytes([qos & 0x03])
    return _paquete((SUBSCRIBE << 4) | 0x02, cuerpo)


def encode_puback(packet_id):
    # PUBACK: acuse de un PUBLISH QoS 1. Solo lleva el id, en 2 bytes.
    return _paquete(PUBACK << 4, bytes([packet_id >> 8, packet_id & 0xFF]))


def encode_pingreq():
    # PINGREQ: latido sin cuerpo. El broker contesta PINGRESP.
    return _paquete(PINGREQ << 4, b"")


def encode_disconnect():
    # DISCONNECT: salida ordenada (asi el broker NO publica el Will).
    return _paquete(DISCONNECT << 4, b"")


# ---------------------------------------------------------------------------
# Decodificacion
# ---------------------------------------------------------------------------
async def _leer_longitud(lector):
    # Lee la longitud restante del paquete que empieza.
    #
    #     Es el formato variable al reves: cada byte aporta 7 bits (`b & 0x7F`)
    #     pesados por 1, 128, 128^2 y 128^3. Si el bit 0x80 esta prendido, hay otro
    #     byte. `await lector.read(1)` devuelve `b""` cuando el otro cerro.
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
    # Lee una cadena MQTT de un cuerpo ya recibido: (texto, nueva_pos).
    #
    #     Los 2 primeros bytes son el largo en big-endian: `cuerpo[pos] << 8` es el
    #     byte alto y `| cuerpo[pos + 1]` pega el bajo, igual que al escribir.
    if pos + 2 > len(cuerpo):
        raise ValueError("cadena truncada")
    largo = (cuerpo[pos] << 8) | cuerpo[pos + 1]
    inicio = pos + 2
    if inicio + largo > len(cuerpo):
        raise ValueError("cadena truncada")
    return cuerpo[inicio:inicio + largo].decode("utf-8", "replace"), inicio + largo


async def leer_paquete(lector):
    # Lee un paquete completo. Devuelve (tipo, flags, cuerpo).
    #
    #     `primero >> 4` se queda con el nibble alto (el tipo) y `primero & 0x0F`
    #     con el bajo (los flags). El `while` existe porque `read(n)` puede
    #     devolver menos bytes de los pedidos.
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
    # Interpreta un PUBLISH recibido: (topico, payload, qos, retain, id).
    #
    #     El QoS son los bits 1-2 (`(flags >> 1) & 0x03`) y el retain el bit 0. El
    #     payload es "lo que quede" despues del topico (y del id si hay QoS).
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
    # CONNACK: byte 0 = "la sesion ya existia" (bit 0), byte 1 = codigo.
    #
    #     Codigo 0 = aceptado; otro valor es un rechazo (1 version de protocolo,
    #     2 id de cliente, 4 credenciales, 5 no autorizado).
    if len(cuerpo) < 2:
        raise ValueError("CONNACK invalido")
    return bool(cuerpo[0] & 0x01), cuerpo[1]


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------
class MqttClient:
    # Cliente MQTT asincrono con Last Will y QoS 1.
    #
    #     No hay hilos: todo corre en el bucle de asyncio. Cada operacion que espera
    #     respuesta (CONNACK, SUBACK, PUBACK) usa un `asyncio.Event` que la tarea de
    #     lectura "despierta" cuando llega el paquete esperado.

    def __init__(self, host, port=1883, client_id="centinela", keepalive=30,
                 tls=False, usuario="", clave="", log=None,
                 timeout_ack_s=5.0):
        self.host = host
        self.port = port
        # El id de cliente debe ser UNICO en el broker: dos nodos con el mismo
        # id se expulsan entre si y entran en bucle de reconexion (por eso el
        # proyecto le agrega un sufijo propio).
        self.client_id = client_id
        self.keepalive = keepalive or 30
        self.tls = tls
        self.usuario = usuario
        self.clave = clave
        self.timeout_ack_s = timeout_ack_s
        self._log = log or (lambda mensaje: None)

        self.conectado = False
        self.on_message = None      # callback(topico, payload, qos, retain)
        self.on_conectado = None    # callback() cuando llega el CONNACK

        self._lector = None
        self._escritor = None
        # Un solo escritor a la vez: dos tareas no pueden intercalar bytes.
        self._lock = asyncio.Lock()
        self._id = 0
        # Acuses pendientes: packet_id (o la tupla ("sub", id)) -> Event.
        self._acks = {}
        self._tareas = []
        # Se prende cuando la conexion se cae; el llamador puede esperarla.
        self._caida = asyncio.Event()
        self.ultimo_ping = 0
        self.publicados = 0
        self.recibidos = 0

    # -- utilidades --------------------------------------------------------
    def _siguiente_id(self):
        # Id de paquete de 16 bits circular (1..65535; el 0 no se usa).
        self._id += 1
        if self._id > 65535:
            self._id = 1
        return self._id

    async def _enviar(self, datos):
        # Escribe los bytes y espera a que salgan del buffer del socket.
        #
        #         `drain()` evita llenar la cola de envio; el lock garantiza que dos
        #         paquetes no se mezclen a mitad de escritura.
        if self._escritor is None:
            raise ConnectionError("sin conexion MQTT")
        async with self._lock:
            self._escritor.write(datos)
            await self._escritor.drain()
        return len(datos)

    # -- ciclo de vida -----------------------------------------------------
    async def conectar(self, will_topic=None, will_msg=None):
        # Abre el socket, envia CONNECT y espera el CONNACK.
        #
        #         Si el CONNACK no llega en 10 s o trae un codigo distinto de 0, cierra
        #         el socket y levanta el error: el bucle de reconexion del llamador
        #         decide cuando volver a intentar.
        if self.tls:
            # HiveMQ Cloud (8883) pide TLS. El ESP32 no trae el juego de
            # certificados raiz, por eso no se valida el certificado.
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
        # Dos tareas de fondo: leer lo que llega y mandar PINGREQ.
        self._tareas = [asyncio.create_task(self._bucle_lectura())]
        if self.keepalive:
            self._tareas.append(asyncio.create_task(self._bucle_keepalive()))
        if self.on_conectado:
            self.on_conectado()
        self._log("MQTT conectado a %s:%d" % (self.host, self.port))
        return True

    async def cerrar(self):
        # Cierra la conexion y detiene las tareas internas.
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
        # Despierta a quien este esperando `esperar_caida()`.
        self._caida.set()

    async def esperar_caida(self):
        # Se bloquea hasta que la conexion se pierda.
        await self._caida.wait()

    # -- operaciones -------------------------------------------------------
    async def suscribir(self, topicos):
        # SUBSCRIBE y espera el SUBACK (hasta `timeout_ack_s`).
        #
        #         `topicos` es una lista de (topico, qos). El id se guarda con la clave
        #         ("sub", id) para no confundirlo con un PUBACK del mismo numero.
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
            # Se ejecuta tambien si hubo timeout: limpia el registro.
            self._acks.pop(("sub", packet_id), None)
        return True

    async def publicar(self, topic, payload, qos=0, retain=False):
        # Publica y, en QoS 1, espera el PUBACK.
        #
        #         QoS 0: sin id ni espera (el camino de la telemetria cada 5 s).
        #         QoS 1: guarda un Event y espera hasta `timeout_ack_s`; si no llega el
        #         acuse devuelve False y el llamador decide.
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
        # Lee paquetes hasta que la conexion se corte.
        #
        #         Es la unica tarea que lee del socket. Cuando llega un PUBLISH QoS 1
        #         contesta PUBACK ANTES de llamar al callback, para que el broker no lo
        #         reenvie aunque el callback tarde.
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
                        # Despierta al `publicar()` que estaba esperando.
                        evento.set()
                elif tipo == SUBACK:
                    packet_id = (cuerpo[0] << 8) | cuerpo[1]
                    evento = self._acks.get(("sub", packet_id))
                    if evento is not None:
                        evento.set()
                elif tipo == PINGRESP:
                    # Llego la respuesta del latido: se reinicia el contador.
                    self.ultimo_ping = 0
        except _CANCELADO:
            raise
        except Exception as exc:  # noqa: BLE001
            self._log("lectura MQTT interrumpida: %s" % exc)
        finally:
            # Pase lo que pase, la conexion queda marcada como caida.
            self.conectado = False
            self._caida.set()

    async def _bucle_keepalive(self):
        # Manda PINGREQ cada `keepalive / 2` segundos.
        #
        #         `self.keepalive / 2.0` es division con decimales (en Python 3 `/`
        #         siempre devuelve float) y `max(1.0, ...)` evita esperas de 0 s. A los
        #         3 pings sin respuesta se da la conexion por muerta.
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
    # Conecta y suscribe con backoff exponencial.
    #
    #     Backoff exponencial = esperar 2 s, despues 4, 8, 16, 32... hasta el tope
    #     `maximo_s`. Evita martillar al broker sin red y deja que el nodo siga
    #     funcionando en local mientras tanto.
    #
    #     Devuelve True al conectar. Si se alcanza el limite de intentos devuelve
    #     False; sin limite, reintenta indefinidamente.
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
            # Se duplica la espera sin pasarse del maximo.
            espera = min(maximo_s, espera * 2)
    return False
