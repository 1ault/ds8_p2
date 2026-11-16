"""Pruebas del cliente MQTT: codificador de paquetes y transporte real.

El transporte se prueba contra un broker falso levantado con
`asyncio.start_server`, que interpreta los bytes de verdad. Asi se validan los
paquetes que salen por el cable y no solo las funciones del codificador.
"""

from __future__ import annotations

import asyncio

import pytest

import mqtt_client as mqtt


# ---------------------------------------------------------------------------
# Codificador (funciones puras)
# ---------------------------------------------------------------------------
class TestLongitudRestante:
    def test_cero(self):
        assert mqtt.longitud_restante(0) == b"\x00"

    def test_un_byte(self):
        assert mqtt.longitud_restante(127) == b"\x7f"

    def test_dos_bytes(self):
        assert mqtt.longitud_restante(128) == b"\x80\x01"

    def test_dos_bytes_al_limite(self):
        assert mqtt.longitud_restante(16383) == b"\xff\x7f"

    def test_tres_bytes(self):
        assert mqtt.longitud_restante(16384) == b"\x80\x80\x01"

    def test_negativo_invalido(self):
        with pytest.raises(ValueError):
            mqtt.longitud_restante(-1)

    def test_demasiado_grande(self):
        with pytest.raises(ValueError):
            mqtt.longitud_restante(268435456)


class TestCadenas:
    def test_cadena_corta(self):
        assert mqtt.cadena("MQTT") == b"\x00\x04MQTT"

    def test_cadena_vacia(self):
        assert mqtt.cadena("") == b"\x00\x00"

    def test_acentos_en_utf8(self):
        datos = mqtt.cadena("sirena")
        assert datos[:2] == b"\x00\x06"
        assert datos[2:] == b"sirena"


class TestConnect:
    def _cuerpo(self, paquete):
        # salta el byte de tipo y la longitud variable
        posicion = 1
        while paquete[posicion] & 0x80:
            posicion += 1
        return paquete[posicion + 1:]

    def test_tipo_connect(self):
        paquete = mqtt.encode_connect("cli1")
        assert paquete[0] >> 4 == mqtt.CONNECT

    def test_incluye_protocolo_y_nivel(self):
        cuerpo = self._cuerpo(mqtt.encode_connect("cli1"))
        assert cuerpo.startswith(b"\x00\x04MQTT\x04")

    def test_sesion_limpia(self):
        cuerpo = self._cuerpo(mqtt.encode_connect("cli1", clean=True))
        banderas = cuerpo[7]
        assert banderas & 0x02

    def test_will_con_retain(self):
        cuerpo = self._cuerpo(mqtt.encode_connect(
            "cli1", will_topic="centinela/dev01/status", will_msg="offline",
            will_qos=1, will_retain=True))
        banderas = cuerpo[7]
        assert banderas & 0x04          # will flag
        assert banderas & 0x20          # retain
        assert (banderas >> 3) & 0x03 == 1
        assert b"offline" in cuerpo

    def test_credenciales_opcionales(self):
        sin = self._cuerpo(mqtt.encode_connect("cli1"))
        con = self._cuerpo(mqtt.encode_connect("cli1", usuario="u", clave="k"))
        assert not (sin[7] & 0x80)
        assert con[7] & 0x80 and con[7] & 0x40
        assert b"u" in con and b"k" in con

    def test_keepalive(self):
        cuerpo = self._cuerpo(mqtt.encode_connect("cli1", keepalive=30))
        assert cuerpo[8:10] == b"\x00\x1e"


class TestPublish:
    def test_qos0(self):
        paquete = mqtt.encode_publish("a/b", "hola")
        assert paquete[0] >> 4 == mqtt.PUBLISH
        assert not (paquete[0] & 0x06)
        assert b"a/b" in paquete and b"hola" in paquete

    def test_qos1_incluye_identificador(self):
        paquete = mqtt.encode_publish("a/b", "x", qos=1, packet_id=0x1234)
        assert (paquete[0] >> 1) & 0x03 == 1
        assert b"\x12\x34" in paquete

    def test_qos1_sin_id_falla(self):
        with pytest.raises(ValueError):
            mqtt.encode_publish("a/b", "x", qos=1)

    def test_retain(self):
        paquete = mqtt.encode_publish("a/b", "x", retain=True)
        assert paquete[0] & 0x01

    def test_payload_bytes(self):
        paquete = mqtt.encode_publish("a/b", b"\x01\x02")
        assert paquete.endswith(b"\x01\x02")


class TestOtrosPaquetes:
    def test_subscribe(self):
        paquete = mqtt.encode_subscribe(7, [("a/b", 1), ("c/d", 0)])
        assert paquete[0] >> 4 == mqtt.SUBSCRIBE
        assert b"\x00\x07" in paquete
        assert b"a/b" in paquete and b"c/d" in paquete

    def test_puback(self):
        assert mqtt.encode_puback(300) == b"\x40\x02\x01\x2c"

    def test_pingreq(self):
        assert mqtt.encode_pingreq() == b"\xc0\x00"

    def test_disconnect(self):
        assert mqtt.encode_disconnect() == b"\xe0\x00"


class TestParsePublish:
    def test_qos0(self):
        cuerpo = b"\x00\x03a/b" + b"hola"
        topico, payload, qos, retain, pid = mqtt.parse_publish(0, cuerpo)
        assert (topico, payload, qos, retain, pid) == ("a/b", b"hola", 0, False, None)

    def test_qos1_con_identificador(self):
        cuerpo = b"\x00\x03a/b\x00\x09" + b"dato"
        topico, payload, qos, retain, pid = mqtt.parse_publish(0x02, cuerpo)
        assert qos == 1
        assert pid == 9
        assert payload == b"dato"

    def test_retain(self):
        cuerpo = b"\x00\x01t" + b"x"
        _, _, _, retain, _ = mqtt.parse_publish(0x01, cuerpo)
        assert retain is True

    def test_cadena_truncada(self):
        with pytest.raises(ValueError):
            mqtt.parse_publish(0, b"\x00\x09ab")


class TestConnack:
    def test_aceptado(self):
        assert mqtt.parse_connack(b"\x00\x00") == (False, 0)

    def test_rechazado(self):
        assert mqtt.parse_connack(b"\x00\x05") == (False, 5)

    def test_sesion_presente(self):
        assert mqtt.parse_connack(b"\x01\x00") == (True, 0)

    def test_invalido(self):
        with pytest.raises(ValueError):
            mqtt.parse_connack(b"\x00")


# ---------------------------------------------------------------------------
# Broker falso para probar el transporte
# ---------------------------------------------------------------------------
def _varint(n: int) -> bytes:
    salida = bytearray()
    while True:
        byte = n % 128
        n //= 128
        if n:
            byte |= 0x80
        salida.append(byte)
        if not n:
            return bytes(salida)


class BrokerFalso:
    """Broker MQTT minimo que habla bytes reales por TCP."""

    def __init__(self, responder_puback=True, codigo_connack=0):
        self.responder_puback = responder_puback
        self.codigo_connack = codigo_connack
        self.conectados = 0
        self.publicados: list[tuple[str, bytes, int]] = []
        self.suscritos: list[bytes] = []
        self.pings = 0
        self.ultimo_connect = b""
        self._servidor = None
        self._escritores = set()
        self.puerto = 0

    async def iniciar(self):
        self._servidor = await asyncio.start_server(
            self._cliente, "127.0.0.1", 0)
        self.puerto = self._servidor.sockets[0].getsockname()[1]
        return self.puerto

    async def detener(self):
        for escritor in list(self._escritores):
            try:
                escritor.close()
            except Exception:  # noqa: BLE001
                pass
        self._escritores.clear()
        if self._servidor is not None:
            self._servidor.close()
            await self._servidor.wait_closed()
            self._servidor = None

    async def enviar(self, topico: str, payload: bytes, qos: int = 0):
        cuerpo = mqtt.cadena(topico) + payload
        paquete = bytes([0x30 | (qos << 1)]) + _varint(len(cuerpo)) + cuerpo
        for escritor in list(self._escritores):
            escritor.write(paquete)
            await escritor.drain()

    async def _leer(self, lector):
        primera = (await lector.readexactly(1))[0]
        multiplicador, largo = 1, 0
        while True:
            byte = (await lector.readexactly(1))[0]
            largo += (byte & 0x7F) * multiplicador
            if not byte & 0x80:
                break
            multiplicador *= 128
        cuerpo = await lector.readexactly(largo) if largo else b""
        return primera >> 4, primera & 0x0F, cuerpo

    async def _cliente(self, lector, escritor):
        self._escritores.add(escritor)
        try:
            tipo, _banderas, cuerpo = await self._leer(lector)
            if tipo != mqtt.CONNECT:
                return
            self.conectados += 1
            self.ultimo_connect = cuerpo
            if self.codigo_connack:
                escritor.write(bytes([0x20, 0x02, 0x00, self.codigo_connack]))
                await escritor.drain()
                return
            escritor.write(b"\x20\x02\x00\x00")
            await escritor.drain()

            while True:
                tipo, banderas, cuerpo = await self._leer(lector)
                if tipo == mqtt.SUBSCRIBE:
                    self.suscritos.append(cuerpo)
                    escritor.write(bytes([0x90, 0x03]) + cuerpo[:2] + b"\x01")
                    await escritor.drain()
                elif tipo == mqtt.PUBLISH:
                    qos = (banderas >> 1) & 0x03
                    largo = (cuerpo[0] << 8) | cuerpo[1]
                    topico = cuerpo[2:2 + largo].decode()
                    posicion = 2 + largo
                    if qos:
                        pid = cuerpo[posicion:posicion + 2]
                        posicion += 2
                        if self.responder_puback:
                            escritor.write(b"\x40\x02" + pid)
                            await escritor.drain()
                    self.publicados.append((topico, cuerpo[posicion:], qos))
                elif tipo == mqtt.PINGREQ:
                    self.pings += 1
                    escritor.write(b"\xd0\x00")
                    await escritor.drain()
                elif tipo == mqtt.DISCONNECT:
                    return
        except (asyncio.IncompleteReadError, ConnectionResetError, ConnectionError):
            pass
        finally:
            self._escritores.discard(escritor)
            try:
                escritor.close()
            except Exception:  # noqa: BLE001
                pass


async def esperar(condicion, timeout: float = 3.0) -> bool:
    """Espera activa: el broker procesa en otra tarea, no en el mismo paso."""
    bucle = asyncio.get_running_loop()
    fin = bucle.time() + timeout
    while bucle.time() < fin:
        if condicion():
            return True
        await asyncio.sleep(0.01)
    return False


@pytest.fixture
async def broker():
    falso = BrokerFalso()
    await falso.iniciar()
    try:
        yield falso
    finally:
        await falso.detener()


@pytest.fixture
async def cliente(broker):
    creado = mqtt.MqttClient("127.0.0.1", broker.puerto, "cli-prueba",
                             keepalive=5, timeout_ack_s=1.0)
    yield creado
    await creado.cerrar()


class TestTransporte:
    async def test_conecta_y_recibe_connack(self, cliente, broker):
        assert await cliente.conectar() is True
        assert cliente.conectado is True
        assert broker.conectados == 1

    async def test_envia_el_last_will(self, cliente, broker):
        await cliente.conectar("centinela/dev01/status", "offline")
        assert b"offline" in broker.ultimo_connect

    async def test_suscribe(self, cliente, broker):
        await cliente.conectar()
        assert await cliente.suscribir([("centinela/dev01/cmd", 1)]) is True
        assert broker.suscritos
        assert b"centinela/dev01/cmd" in broker.suscritos[0]

    async def test_publica_qos0(self, cliente, broker):
        await cliente.conectar()
        assert await cliente.publicar("centinela/dev01/telemetry", b'{"a":1}') is True
        assert await esperar(lambda: broker.publicados)
        assert broker.publicados[0][0] == "centinela/dev01/telemetry"
        assert broker.publicados[0][1] == b'{"a":1}'

    async def test_publica_qos1_y_espera_puback(self, cliente, broker):
        await cliente.conectar()
        assert await cliente.publicar("t/x", b"dato", qos=1) is True
        assert broker.publicados[0][2] == 1

    async def test_publica_qos1_sin_puback_devuelve_false(self, broker):
        broker.responder_puback = False
        cliente = mqtt.MqttClient("127.0.0.1", broker.puerto, "cli-sin-ack",
                                  keepalive=5, timeout_ack_s=0.2)
        try:
            await cliente.conectar()
            assert await cliente.publicar("t/x", b"dato", qos=1) is False
        finally:
            await cliente.cerrar()

    async def test_recibe_un_mensaje(self, cliente, broker):
        recibidos = []
        listo = asyncio.Event()

        def al_recibir(topico, payload, qos, retain):
            recibidos.append((topico, payload, qos))
            listo.set()

        cliente.on_message = al_recibir
        await cliente.conectar()
        await cliente.suscribir([("centinela/dev01/cmd", 1)])
        await broker.enviar("centinela/dev01/cmd", b'{"cmd":"arm"}')
        await asyncio.wait_for(listo.wait(), 3)
        assert recibidos[0][0] == "centinela/dev01/cmd"
        assert recibidos[0][1] == b'{"cmd":"arm"}'

    async def test_connack_rechazado(self, broker):
        broker.codigo_connack = 5
        cliente = mqtt.MqttClient("127.0.0.1", broker.puerto, "cli-rechazo")
        with pytest.raises(ConnectionError):
            await cliente.conectar()
        assert cliente.conectado is False

    async def test_publicar_sin_conexion_falla(self):
        cliente = mqtt.MqttClient("127.0.0.1", 1, "cli-suelto")
        with pytest.raises(ConnectionError):
            await cliente.publicar("a/b", b"x")

    async def test_keepalive_envia_ping(self, cliente, broker):
        await cliente.conectar()
        await asyncio.sleep(2.8)      # keepalive 5 -> ping cada 2.5 s
        assert broker.pings >= 1

    async def test_cerrar_marca_desconectado(self, cliente, broker):
        await cliente.conectar()
        await cliente.cerrar()
        assert cliente.conectado is False

    async def test_reintentos_se_rinden_al_limite(self):
        cliente = mqtt.MqttClient("127.0.0.1", 1, "cli-sin-broker")
        conectado = await mqtt.conectar_con_reintentos(
            cliente, [], minimo_s=0.01, maximo_s=0.02, intentos=2)
        assert conectado is False
