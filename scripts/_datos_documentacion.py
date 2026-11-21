"""Contenido editorial de la documentacion extendida.

Separa los textos de la maquetacion: proposito de cada modulo, descripcion de
cada elemento cuando el docstring no basta, comentarios linea por linea de las
funciones criticas, anotacion de los archivos SQL y del frontend, y el
contenido del capitulo de analisis funcional.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Proposito y dependencias de cada modulo
# ---------------------------------------------------------------------------
MODULOS = {
    "firmware/config.py": {
        "proposito": "Unica fuente de verdad para pines, umbrales, tiempos, "
                     "topicos y credenciales del nodo. Ningun otro modulo del "
                     "firmware contiene numeros de hardware.",
        "depende": "nada (solo constantes)",
    },
    "firmware/hal.py": {
        "proposito": "Capa de abstraccion de hardware: envuelve `machine` (Pin, "
                     "PWM, ADC, I2C, DHT22 y `time_pulse_us`) y resuelve las "
                     "diferencias entre versiones de MicroPython.",
        "depende": "machine, dht, time (importados de forma diferida)",
    },
    "firmware/bus.py": {
        "proposito": "Bus de eventos asincrono con buzon acotado por suscriptor; "
                     "desacopla productores y consumidores dentro del nodo.",
        "depende": "asyncio",
    },
    "firmware/fsm.py": {
        "proposito": "Maquina de estados de seguridad pura: recibe eventos y el "
                     "instante actual, y devuelve efectos. No toca hardware ni red.",
        "depende": "nada",
    },
    "firmware/sensors.py": {
        "proposito": "Lectura de los cuatro sensores con validacion de rangos, "
                     "mediana de muestras y aislamiento de errores por sensor.",
        "depende": "hal, time",
    },
    "firmware/actuators.py": {
        "proposito": "Control de LEDs, sirena PWM y cerradura con servo, con "
                     "estado recordado para no reescribir el GPIO sin necesidad.",
        "depende": "hal",
    },
    "firmware/ssd1306.py": {
        "proposito": "Driver minimo del OLED SSD1306 sobre `framebuf`: "
                     "inicializacion, volcado del framebuffer y primitivas de dibujo.",
        "depende": "framebuf",
    },
    "firmware/display.py": {
        "proposito": "Interfaz local del nodo: compone las lineas del OLED "
                     "(estado, lecturas, cerradura, sirena y enlace).",
        "depende": "hal, ssd1306",
    },
    "firmware/net.py": {
        "proposito": "Conexion WiFi con reintentos y consulta del estado de la "
                     "senal para la telemetria.",
        "depende": "network (diferido), asyncio, time",
    },
    "firmware/mqtt_client.py": {
        "proposito": "Cliente MQTT 3.1.1 propio sobre `asyncio` streams: "
                     "codificacion de paquetes, CONNECT con Last Will, QoS 0/1, "
                     "keepalive y reconexion.",
        "depende": "asyncio",
    },
    "firmware/app.py": {
        "proposito": "Controlador del nodo: siete tareas cooperativas que unen "
                     "sensores, maquina de estados, actuadores y MQTT.",
        "depende": "config, hal, fsm, bus, asyncio, json, time",
    },
    "firmware/main.py": {
        "proposito": "Punto de entrada: construye pantalla, WiFi, actuadores, "
                     "sensores, maquina y cliente; arranca el controlador.",
        "depende": "config, display, net, actuators, sensors, fsm, mqtt_client, app",
    },
    "backend/config.py": {
        "proposito": "Configuracion del backend por variables de entorno y archivo "
                     "`.env`, con valores por defecto para la demo.",
        "depende": "os, dataclasses, pathlib, dotenv (opcional)",
    },
    "backend/storage.py": {
        "proposito": "DAO sobre SQLite: lecturas, eventos, comandos, transiciones, "
                     "estadisticas y purga, con un unico escritor serializado.",
        "depende": "sqlite3, asyncio, json, datetime",
    },
    "backend/commands.py": {
        "proposito": "Validacion, envio, espera de ACK y auditoria de comandos, con "
                     "limite de frecuencia por origen.",
        "depende": "config, storage, asyncio, uuid, collections",
    },
    "backend/cloud.py": {
        "proposito": "Cliente de ThingSpeak: canal de ocho campos y cola de "
                     "comandos TalkBack, con implementacion nula para modo local.",
        "depende": "aiohttp (diferido), json, time",
    },
    "backend/bus.py": {
        "proposito": "Bus de eventos en proceso que alimenta el canal SSE del panel.",
        "depende": "asyncio",
    },
    "backend/mqtt_bridge.py": {
        "proposito": "Puente entre paho-mqtt (hilos) y asyncio: publica y recibe "
                     "mensajes como eventos asincronos.",
        "depende": "paho.mqtt, asyncio, json",
    },
    "backend/web/auth.py": {
        "proposito": "Sesiones sin estado mediante cookie firmada con HMAC-SHA256 y "
                     "comparacion de credenciales en tiempo constante.",
        "depende": "hmac, hashlib, base64, json, time",
    },
    "backend/web/app.py": {
        "proposito": "Aplicacion aiohttp: middleware de sesion, API REST, canal SSE, "
                     "login y archivos estaticos del panel.",
        "depende": "aiohttp, auth, asyncio, json, time",
    },
    "backend/main.py": {
        "proposito": "Composicion del backend: servicios, tareas de fondo, servidor "
                     "web y parada ordenada.",
        "depende": "todos los modulos del backend, aiohttp",
    },
    "backend/cli.py": {
        "proposito": "Consultas de historicos por consola, con salida en tabla o JSON.",
        "depende": "config, storage, argparse, asyncio",
    },
    "backend/__init__.py": {
        "proposito": "Marca el paquete y declara la version del backend.",
        "depende": "nada",
    },
    "backend/web/__init__.py": {
        "proposito": "Marca el subpaquete web.",
        "depende": "nada",
    },
}

# ---------------------------------------------------------------------------
# Descripcion de elementos cuando el docstring no basta
# ---------------------------------------------------------------------------
ELEMENTOS = {
    # firmware/hal.py
    "Pin.value": "Lee o escribe el pin: sin argumento devuelve 0/1; con argumento lo fija.",
    "Pin.on": "Atajo de `value(1)`.",
    "Pin.off": "Atajo de `value(0)`.",
    "Pin._instancia": "Crea el objeto `machine.Pin` la primera vez; se llamo desde el "
                      "constructor para fallar pronto si el pin no existe.",
    "PWM.freq": "Fija o consulta la frecuencia del PWM.",
    "PWM.duty": "Ciclo de trabajo 0..1023; en ESP32 nuevo se traduce a `duty_u16`.",
    "PWM.duty_u16": "Ciclo de trabajo 0..65535, usado por el servo.",
    "ADC.read": "Devuelve la lectura cruda del ADC (12 bits en el ESP32).",
    "I2C.writevto": "Escribe varios vectores en una transaccion; si no existe, los envía uno a uno.",
    # firmware/sensors.py
    "DhtSensor.leer": "Reintenta hasta tres veces y devuelve la mediana de las ultimas "
                      "muestras validas de temperatura y humedad.",
    "PirSensor.leer": "Devuelve verdadero mientras el PIR siga en alto o dentro del tiempo "
                      "de retencion (1,5 s).",
    "UltrasonicSensor._disparo": "Genera el pulso de disparo y mide el eco; devuelve la "
                                 "distancia en cm o None si no hay eco valido.",
    "UltrasonicSensor.leer": "Toma tres disparos y devuelve la mediana de los validos.",
    "LightSensor.leer": "Convierte la lectura del ADC en lux con el modelo del modulo.",
    "SensorSuite.actualizar": "Lee solo los sensores cuyo periodo vencio y devuelve las "
                              "lecturas nuevas.",
    # firmware/actuators.py
    "Led.encender": "Enciende el LED solo si estaba apagado.",
    "Led.apagar": "Apaga el LED solo si estaba encendido.",
    "Led.alternar": "Invierte el estado; lo usa el parpadeo de alarma.",
    "Buzzer.encender": "Fija la frecuencia y activa el ciclo de trabajo de la sirena.",
    "Buzzer.apagar": "Deja el ciclo de trabajo en cero.",
    "ServoLock.mover_a": "Convierte el angulo a microsegundos y luego a `duty_u16`.",
    "PanelActuadores.apagar_todo": "Apaga LEDs y sirena; se usa al detener el nodo.",
    # firmware/fsm.py
    "SecurityFSM.handle": "Despacha el evento al manejador correspondiente y devuelve efectos.",
    "SecurityFSM.tick": "Resuelve temporizadores vencidos: fin de armado, fin de bloqueo y "
                        "cierre automatico.",
    "SecurityFSM._comando": "Traduce `arm`, `disarm`, `mute` y `unlock` en transiciones.",
    "SecurityFSM._abrir": "Valida PIN, bloqueo e intentos antes de liberar la cerradura.",
    "SecurityFSM._puede_alertar": "Antirrebote de alertas: exige `cooldown_alerta_s` desde "
                                  "la anterior.",
    "SecurityFSM._temperatura": "Convierte una temperatura alta en alarma solo si el sistema "
                               "esta armado.",
    # firmware/app.py
    "Controlador._publicar": "Serializa y publica; si no hay conexion devuelve False sin "
                             "lanzar error.",
    "Controlador._evento": "Construye y publica un evento con tipo, severidad y contexto.",
    "Controlador._telemetria": "Arma el diccionario de telemetria con sensores y estado.",
    "Controlador._aplicar": "Traduce los efectos de la FSM en acciones de hardware y eventos.",
    "Controlador._detectar_cambio_estado": "Publica un evento solo cuando el estado cambio.",
    "Controlador._al_recibir": "Callback sincrono del cliente: publica en el bus, no bloquea.",
    "Controlador._aplicar_config": "Valida y aplica umbrales recibidos en caliente.",
    "Controlador.procesar_comando": "Valida, ejecuta y confirma un comando, con ACK.",
    "Controlador.alternar_armado": "Arma o desarma segun el estado; lo usa el pulsador.",
    "Controlador.datos_pantalla": "Prepara el diccionario que consume el OLED.",
    "Controlador.ejecutar": "Crea las tareas asincronas y espera a que terminen.",
    "Controlador.detener": "Cancela tareas, cierra MQTT y apaga actuadores.",
    # firmware/mqtt_client.py
    "longitud_restante": "Codifica la longitud variable de MQTT (1 a 4 bytes).",
    "cadena": "Codifica una cadena MQTT: dos bytes de longitud y UTF-8.",
    "_leer_longitud": "Lee y decodifica la longitud variable de un paquete entrante.",
    "leer_paquete": "Lee un paquete completo del socket y devuelve tipo, flags y cuerpo.",
    "parse_publish": "Interpreta un PUBLISH entrante y separa topico, payload e identificador.",
    "parse_connack": "Interpreta el CONNACK y devuelve sesion presente y codigo.",
    "MqttClient.conectar": "Abre el socket, envia CONNECT y espera CONNACK.",
    "MqttClient.cerrar": "Cierra el transporte y cancela las tareas internas.",
    "MqttClient.suscribir": "Envia SUBSCRIBE y espera SUBACK.",
    "MqttClient.publicar": "Publica y, en QoS 1, espera PUBACK.",
    "MqttClient._bucle_lectura": "Bucle que interpreta los paquetes entrantes.",
    "MqttClient._bucle_keepalive": "Envia PINGREQ y detecta la perdida de enlace.",
    "conectar_con_reintentos": "Conecta con retroceso exponencial hasta lograrlo o rendirse.",
    # firmware/net.py
    "Wifi.conectar": "Activa la interfaz, se conecta y espera hasta el tiempo limite.",
    "Wifi.rssi": "Consulta la potencia de la senal para la telemetria.",
    # firmware/main.py
    "log": "Imprime un mensaje con el prefijo del nodo.",
    "arrancar": "Secuencia de arranque completa del dispositivo.",
    "main": "Ejecuta el bucle asincrono y captura la interrupcion del usuario.",
    # firmware/display.py
    "_recortar": "Corta el texto al ancho de pantalla (16 caracteres).",
    "_num": "Formatea un numero o devuelve `--` si falta.",
    "Pantalla.mostrar": "Compone y pinta las siete lineas del OLED.",
    "Pantalla.aviso": "Mensaje puntual de arranque.",
    # backend/storage.py
    "ahora_utc": "Instante actual en UTC (inyectable en pruebas).",
    "iso": "Convierte un datetime a texto ISO-8601 con sufijo Z.",
    "Almacen.abrir": "Crea la conexion y aplica el esquema.",
    "Almacen.cerrar": "Confirma y cierra la conexion.",
    "Almacen._asegurar_dispositivo": "Inserta el dispositivo si falta, para respetar la clave foranea.",
    "Almacen.registrar_dispositivo": "Alta o actualizacion del dispositivo y su ultima vez visto.",
    "Almacen.guardar_lectura": "Inserta una lectura con marca de tiempo del servidor.",
    "Almacen.ultima_lectura": "Devuelve la lectura mas reciente del dispositivo.",
    "Almacen.historico": "Lecturas de las ultimas N horas, en orden cronologico.",
    "Almacen.agregado_horario": "Promedios, minimos y maximos por hora.",
    "Almacen.registrar_evento": "Inserta un evento con su severidad y datos.",
    "Almacen.eventos": "Ultimos eventos, con filtro opcional por severidad.",
    "Almacen.crear_comando": "Registra el comando en estado PENDIENTE antes de publicarlo.",
    "Almacen.confirmar_comando": "Cierra el comando y calcula la latencia.",
    "Almacen.expirar_comandos": "Marca TIMEOUT los comandos sin ACK.",
    "Almacen.comandos": "Historial de comandos con argumentos y resultado.",
    "Almacen.estadisticas": "Agregados de lecturas, eventos y comandos.",
    "Almacen.purgar": "Borra datos anteriores a N dias.",
    # backend/commands.py
    "Validador.validar": "Aplica lista blanca, tipos y rangos; devuelve argumentos limpios.",
    "Validador.claves_config": "Lista las claves de configuracion admitidas.",
    "ServicioComandos.ejecutar": "Ciclo completo: validar, auditar, publicar y esperar ACK.",
    "ServicioComandos.confirmar": "Procesa el ACK del nodo y libera la espera.",
    "ServicioComandos.expirar": "Delega en el almacen el marcado de comandos vencidos.",
    "ServicioComandos._permitir": "Limita la frecuencia de comandos por minuto.",
    # backend/cloud.py
    "parsear_comando": "Convierte el texto de TalkBack en un comando del sistema.",
    "NubeThingSpeak.construir_campos": "Mapea la telemetria a los ocho campos del canal.",
    "NubeThingSpeak.subir": "Envia una lectura respetando el intervalo minimo.",
    "NubeThingSpeak.siguiente_comando": "Consulta la cola de TalkBack.",
    # backend/mqtt_bridge.py
    "_codigo_exitoso": "Normaliza el codigo de resultado entre paho 1.x y 2.x.",
    "PuenteMqtt.iniciar": "Crea el cliente, conecta en segundo plano y espera el CONNACK.",
    "PuenteMqtt.publicar": "Publica un mensaje y devuelve si el broker lo acepto.",
    "PuenteMqtt.recibir": "Espera el siguiente mensaje de la cola asincrona.",
    "decodificar": "Convierte el payload en diccionario si es JSON valido.",
    # backend/web/app.py
    "middleware_sesion": "Exige sesion valida salvo en modo demostracion o rutas publicas.",
    "middleware_errores": "Convierte cualquier excepcion en una respuesta JSON controlada.",
    "pagina_panel": "Sirve el HTML del panel.",
    "pagina_login": "Sirve el formulario de acceso.",
    "entrar": "Valida credenciales y crea la cookie de sesion.",
    "salir": "Elimina la cookie y redirige al login.",
    "salud": "Estado del servicio para diagnostico.",
    "api_estado": "Estado actual: lectura, MQTT, nube, comandos y clientes SSE.",
    "api_lecturas": "Serie temporal y agregados por hora.",
    "api_eventos": "Ultimos eventos, con filtro por severidad.",
    "api_comandos": "Historial de comandos con estado y latencia.",
    "api_estadisticas": "Agregados del dispositivo.",
    "api_comando": "Valida el cuerpo y delega en el servicio de comandos.",
    "api_estado_seguridad": "Transiciones de la maquina de estados.",
    "api_stream": "Canal SSE que empuja los eventos del bus al navegador.",
    "_entero": "Convierte y acota un parametro entero de la consulta.",
    "_flotante": "Convierte y acota un parametro decimal de la consulta.",
    "crear_app": "Construye la aplicacion con sus dependencias y rutas.",
    # backend/web/auth.py
    "_firma": "Calcula la firma HMAC-SHA256 del cuerpo.",
    "crear_token": "Genera el token `cuerpo.firma` con usuario y caducidad.",
    "verificar_token": "Valida firma y caducidad; devuelve el payload o None.",
    "credenciales_validas": "Compara usuario y clave en tiempo constante.",
    # backend/main.py
    "log": "Salida con hora del backend.",
    "Backend.arrancar": "Abre la base, conecta MQTT, lanza tareas y sirve el panel.",
    "Backend.detener": "Cancela tareas, cierra servicios y libera recursos.",
    "Backend._procesar": "Reparte cada mensaje MQTT segun su topico.",
    "Backend._detectar_estado": "Registra las transiciones de estado observadas.",
    "Backend._bucle_mensajes": "Consume la cola del puente y procesa mensajes.",
    "Backend._bucle_talkback": "Recoge comandos de ThingSpeak y los ejecuta.",
    "Backend._bucle_mantenimiento": "Expira comandos y purga datos antiguos.",
    "cargar_seed": "Aplica el esquema y los datos de demostracion.",
    "construir_argumentos": "Define las opciones de linea de comandos.",
    "ejecutar": "Monta el backend, instala senales y espera la parada.",
    "main": "Punto de entrada del proceso.",
    # backend/cli.py
    "_tabla": "Dibuja una tabla de texto con anchos calculados.",
    "_texto": "Formatea un valor para la tabla.",
    "construir_parser": "Define subcomandos y opciones.",
    "ejecutar": "Ejecuta el subcomando solicitado sobre la base de datos.",
    "main": "Punto de entrada de la CLI.",
    # backend/bus.py
    "Suscriptor.ofrecer": "Encola un evento; si el buzon esta lleno descarta el mas viejo.",
    "Suscriptor.siguiente": "Espera el siguiente evento con tiempo limite opcional.",
    "Hub.suscribir": "Crea un suscriptor nuevo.",
    "Hub.publicar": "Entrega el evento a todos los suscriptores.",
    # frontend
    "pintarEstado": "Actualiza estado, sensores, pildoras y tarjeta del sistema.",
    "pintarEventos": "Pinta el feed de eventos con su severidad.",
    "pintarComandos": "Rellena la tabla de comandos con insignias de estado.",
    "dibujarGrafica": "Dibuja la grafica de temperatura y humedad en canvas.",
    "dibujarSerie": "Traza una serie con relleno bajo la curva.",
    "conectarSSE": "Abre el canal SSE y programa la reconexion.",
    "enviarComando": "Publica el comando en la API y muestra el resultado.",
    "pedirPin": "Abre el dialogo de PIN y devuelve lo introducido.",
    "refrescarTodo": "Recarga estado, lecturas, eventos, comandos y estadisticas.",
}

# ---------------------------------------------------------------------------
# Listados comentados linea por linea (numero de linea absoluto)
# ---------------------------------------------------------------------------
LISTADOS = {
    "firmware/fsm.py::SecurityFSM._presencia": {
        209: "Firma: recibe el instante y el evento del sensor.",
        210: "Solo se reacciona con la vigilancia activa (armado o ya en alarma).",
        211: "En desarmado o armando no hay efectos: el sistema no vigila.",
        212: "Antirrebote: exige que hayan pasado 5 s desde la alerta anterior.",
        213: "Evento repetido descartado para que un PIR en alto no genere decenas de alertas.",
        215: "Distancia opcional que envia el controlador cuando la deteccion viene del HC-SR04.",
        216: "Motivo por defecto si el evento no lo trae.",
        217: "Si hay distancia, el motivo cambia a presencia cercana.",
        218: "Se sobrescribe el motivo con el especifico.",
        220: "Se guarda el instante para el antirrebote siguiente.",
        221: "Contador acumulado que luego viaja en la telemetria.",
        222: "Transicion a alarma: es el unico punto que la produce por presencia.",
        223: "Se conserva el motivo para eventos y trazabilidad.",
        224: "Primer efecto: registrar la alerta con su detalle.",
        226: "Si el operador silencio la sirena, no se vuelve a encender.",
        227: "Se marca que la sirena debe sonar.",
        228: "Se programa el apagado automatico a los 120 s por defecto.",
        229: "Segundo efecto: encender la sirena.",
        231: "Se devuelven los efectos al controlador, que los aplica.",
    },
    "firmware/mqtt_client.py::encode_connect": {
        61: "Firma del codificador; todos los datos del CONNECT son opcionales salvo el id.",
        62: "Argumentos de will y credenciales en la segunda linea.",
        63: "Cierra la firma con la bandera de sesion limpia.",
        65: "Acumulador de banderas del octeto de conexion.",
        66: "La sesion limpia se activa por defecto.",
        67: "Bit 1: clean session.",
        68: "Solo se procesa el Last Will si hay topico.",
        69: "Bits 2 y 3-4: bandera de will y su QoS.",
        70: "Retencion del will opcional.",
        71: "Bit 5: mensaje retenido.",
        72: "Si hay usuario, se activa su bandera.",
        73: "Bit 7: bandera de usuario.",
        74: "Si hay clave, se activa la contrasena.",
        75: "Bit 6: bandera de contrasena.",
        77: "Cabecera variable: nombre del protocolo y nivel.",
        78: "Nivel 4 (MQTT 3.1.1) y banderas calculadas.",
        79: "Keepalive en dos bytes, big endian.",
        80: "El payload empieza con el identificador de cliente.",
        81: "Si hay will, se anexan su topico y su mensaje.",
        82: "Topico del will como cadena MQTT.",
        83: "El mensaje del will se normaliza a bytes.",
        84: "Conversion a UTF-8 si llego como texto.",
        85: "Longitud de dos bytes y contenido del will.",
        86: "Credenciales opcionales al final del payload.",
        87: "Usuario como cadena MQTT.",
        88: "La clave solo se agrega si existe.",
        89: "Clave como cadena MQTT.",
        90: "Se arma el paquete con el tipo CONNECT y el cuerpo completo.",
    },
    "firmware/app.py::Controlador._ciclo": {
        192: "Firma: recibe el instante; lo llama el bucle de sensores cada 50 ms.",
        193: "Lee solo los sensores cuyo periodo vencio.",
        194: "Avanza los temporizadores de la maquina (fin de armado, cierre automatico).",
        195: "Umbral de distancia leido de la configuracion, con valor de respaldo.",
        197: "Comentario: se evalua el flanco de subida del movimiento.",
        198: "Motivo: el sensor puede quedar en alto varios segundos.",
        199: "Lectura de movimiento de este ciclo, si la hubo.",
        200: "Solo se evalua cuando el sensor entrego una muestra nueva.",
        201: "Flanco de subida y sistema armado: unico caso que alerta.",
        202: "Se envia el evento de presencia a la maquina de estados.",
        203: "Evento con motivo movimiento.",
        204: "Se acumulan los efectos devueltos.",
        205: "Se recuerda el estado del sensor para detectar el flanco.",
        207: "Distancia medida por el ultrasonido, si vencio su periodo.",
        208: "Solo con muestra nueva.",
        209: "Condicion de presencia cercana segun el umbral.",
        210: "Debe entrar en el umbral (flanco) y estar armado.",
        211: "Evento de presencia con la distancia medida.",
        212: "Motivo especifico de proximidad.",
        213: "Se adjunta la distancia al evento.",
        214: "Se acumulan efectos.",
        215: "Se recuerda si estaba dentro del umbral.",
        217: "Lectura de clima (temperatura y humedad).",
        218: "Solo si hay temperatura valida.",
        219: "Evento de temperatura hacia la maquina.",
        220: "Se envia el valor en grados.",
        221: "Se acumulan efectos.",
        223: "Solo se actua si hubo efectos.",
        224: "Se aplican sobre hardware y se publican los eventos.",
        225: "Se publica el cambio de estado si lo hubo.",
        226: "Se devuelven las lecturas nuevas al bucle.",
    },
    "backend/storage.py::Almacen.guardar_lectura": {
        157: "Firma tipada: identificador del dispositivo y diccionario de telemetria.",
        158: "Docstring: la marca de tiempo la pone el servidor.",
        159: "Garantiza la fila del dispositivo para respetar la clave foranea.",
        160: "Instante del servidor (inyectable en pruebas).",
        161: "Tupla de valores en el mismo orden que el INSERT.",
        162: "Identificador del dispositivo.",
        163: "Marca temporal numerica para indices y calculos.",
        164: "Marca temporal legible en ISO-8601.",
        165: "Temperatura ya convertida a numero o nulo.",
        166: "Humedad.",
        167: "Luminosidad.",
        168: "Distancia.",
        169: "Movimiento como 0/1.",
        170: "Estado de seguridad; DESCONOCIDO si falta.",
        171: "Alarma como 0/1.",
        172: "Sirena como 0/1.",
        173: "Cerradura como 0/1, cerrada por defecto.",
        174: "Alertas con valor por defecto cero.",
        175: "Senal WiFi.",
        176: "Numero de secuencia.",
        177: "Errores de sensor acumulados.",
        178: "Payload original en JSON compacto para auditoria.",
        179: "Cierre de la tupla.",
        180: "Escritura serializada en el hilo de base de datos.",
        181: "INSERT con columnas explicitas.",
        182: "Columnas de sensores y estado.",
        183: "Columnas de diagnostico y payload.",
        184: "Diecisiete marcadores: una consulta parametrizada.",
        185: "Valores de la tupla.",
        186: "Cierre de la llamada.",
    },
    "backend/commands.py::ServicioComandos.ejecutar": {
        123: "Firma tipada: comando, argumentos libres y origen.",
        124: "Devuelve un diccionario con el resultado y el ACK.",
        125: "Docstring del ciclo completo.",
        126: "Instante del servidor.",
        127: "Validacion: lista blanca, tipos y rangos.",
        128: "Si no es valido, se rechaza sin tocar la red.",
        129: "Contador de rechazos.",
        130: "Se notifica al panel el rechazo.",
        131: "Motivo legible del rechazo.",
        132: "Se devuelve el rechazo sin identificador.",
        134: "Limite de 30 comandos por minuto.",
        135: "Se cuenta como rechazo.",
        136: "Motivo especifico de exceso de frecuencia.",
        138: "Sin enlace con el broker no se puede enviar.",
        139: "Se cuenta como rechazo.",
        140: "Motivo de falta de conexion.",
        142: "Identificador unico de 12 caracteres hexadecimales.",
        143: "Auditoria previa: el comando se guarda antes de publicarse.",
        144: "Argumentos ya limpios y validados.",
        146: "Futuro que se resolvera cuando llegue el ACK.",
        147: "Registro del comando pendiente por identificador.",
        149: "Mensaje que viaja por el topico de comandos.",
        150: "Version del contrato.",
        151: "Identificador para correlacionar el ACK.",
        152: "Nombre del comando.",
        153: "Argumentos validados.",
        154: "Origen del comando.",
        155: "Instante en ISO-8601.",
        157: "Publicacion QoS 1.",
        158: "Si el broker no acepta el mensaje...",
        159: "...se elimina de pendientes...",
        160: "...se cierra como ERROR...",
        161: "...con su motivo...",
        162: "...y se avisa al panel.",
        164: "Se devuelve el fallo al llamador.",
        166: "Contador de comandos aceptados.",
        167: "Espera del ACK con tiempo limite.",
        168: "Bloquea hasta que llegue el ACK o venza el plazo.",
        169: "Si vence el plazo...",
        170: "...se cuenta como timeout...",
        171: "...se elimina de pendientes...",
        172: "...se cierra como TIMEOUT...",
        173: "...se avisa al panel...",
        174: "...con el motivo correspondiente...",
        175: "...y se devuelve el fallo.",
        177: "Respuesta al llamador con el ACK recibido.",
        178: "Exito segun lo que respondio el nodo.",
        179: "Identificador del comando.",
        180: "Motivo si el nodo lo rechazo.",
        181: "Confirmacion completa del dispositivo.",
        182: "Cierre del diccionario.",
    },
    "backend/web/app.py::api_stream": {
        231: "Firma tipada: recibe la peticion y devuelve una respuesta en streaming.",
        232: "Docstring: SSE es un canal de un solo sentido.",
        233: "Servicios de la aplicacion (almacen, hub, comandos...).",
        234: "El hub es el que reparte los eventos entre paneles.",
        236: "Se construye la respuesta en streaming.",
        237: "Codigo 200: el canal queda abierto.",
        238: "Cabeceras propias de SSE.",
        239: "Tipo de contenido que reconoce EventSource.",
        240: "Sin cache: cada evento debe llegar.",
        241: "Conexion persistente.",
        242: "Desactiva el buffer de proxies como Nginx.",
        243: "Fin de cabeceras.",
        244: "Cierre de la respuesta.",
        245: "Se envia la cabecera antes de los eventos.",
        247: "Cada panel tiene su propio suscriptor.",
        248: "Bloque protegido: siempre se da de baja al final.",
        249: "Comentario inicial para confirmar el canal.",
        250: "Bucle de envio.",
        251: "Espera un evento con 15 s de cortesia.",
        252: "Si no hay evento en ese tiempo...",
        253: "...se envia un comentario para mantener viva la conexion...",
        254: "...y se sigue esperando.",
        255: "Serializa los datos del evento.",
        256: "Formato SSE: tipo de evento y datos.",
        257: "Se escribe el bloque en el socket.",
        258: "Cierre ordenado: cancelacion o cliente desconectado.",
        259: "No se propaga: es una desconexion esperada.",
        260: "Limpieza garantizada.",
        261: "Se elimina el suscriptor del hub.",
        262: "Se devuelve la respuesta ya cerrada.",
    },
}

# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------
SQL_SCHEMA = [
    ("PRAGMA journal_mode = WAL", "Activa el modo WAL: lecturas concurrentes con una escritura."),
    ("PRAGMA foreign_keys = ON", "Exige que las claves foraneas se cumplan."),
    ("CREATE TABLE devices", "Nodos registrados: identificador, nombre, ubicacion, firmware "
                             "y ultima vez visto (texto y epoch)."),
    ("CREATE TABLE readings", "Una fila por telemetria: 17 columnas con sensores, estado, "
                              "diagnostico y payload original; CHECK en estado y banderas."),
    ("CREATE INDEX idx_readings_device_ts", "Indice para el historico y la ultima lectura."),
    ("CREATE INDEX idx_readings_alarm", "Indice para localizar episodios de alarma."),
    ("CREATE TABLE events", "Eventos con tipo, severidad (CHECK de tres valores), mensaje, "
                            "estado y detalle JSON."),
    ("CREATE INDEX idx_events_device_ts", "Indice del feed de eventos por dispositivo."),
    ("CREATE INDEX idx_events_severity", "Indice para filtrar por severidad."),
    ("CREATE TABLE commands", "Comandos con estado (PENDIENTE/OK/RECHAZADO/TIMEOUT/ERROR), "
                              "marcas de tiempo, latencia, resultado y motivo."),
    ("CREATE INDEX idx_commands_emitido", "Indice para el historial de comandos."),
    ("CREATE INDEX idx_commands_estado", "Indice para pendientes y expirados."),
    ("CREATE TABLE state_changes", "Transiciones de la maquina de estados con motivo."),
    ("CREATE INDEX idx_state_device_ts", "Indice de las transiciones por dispositivo."),
    ("CREATE VIEW v_ultima_lectura", "Estado actual de cada dispositivo (union con el maximo)."),
    ("CREATE VIEW v_resumen_horario", "Agregados por hora: muestras, temperatura, humedad, "
                                      "luz, distancia y alarmas."),
    ("CREATE VIEW v_salud_comandos", "Salud por dia y origen: totales, exitos, rechazos, "
                                     "timeouts y latencia media."),
    ("CREATE VIEW v_eventos_criticos", "Eventos warning y critical ordenados por fecha."),
    ("CREATE VIEW v_estado_actual", "Ultima transicion registrada por dispositivo."),
]

SQL_CONSULTAS = [
    ("01. Ultima lectura de cada dispositivo", "Estado actual de la casa; alimenta el resumen "
                                               "de la CLI."),
    ("02. Historico de las ultimas N horas", "Serie que dibuja la grafica del panel; usa "
                                             "`:horas` y `:limite`."),
    ("03. Promedios por hora de 24 horas", "Tendencia diaria sobre la vista `v_resumen_horario`."),
    ("04. Eventos criticos y advertencias", "Lista priorizada de lo que el operador debe revisar."),
    ("05. Historial de comandos con latencia", "Auditoria de accesos a la cerradura y su resultado."),
    ("06. Salud de comandos por origen", "Porcentaje de exito y latencia media por via."),
    ("07. Transiciones de la maquina de estados", "Quien armo o desarmo y con que motivo."),
    ("08. Rango termico e higrometrico por dia", "Minimos, medias y maximos diarios."),
    ("09. Actividad por franja horaria", "Mapa de movimiento y alarmas por hora del dia."),
    ("10. Episodios de alarma por dia", "Cantidad de lecturas en alarma y duracion estimada."),
    ("11. Huecos de telemetria", "Detecta caidas del nodo con `LEAD` sobre `ts_epoch`."),
    ("12. Volumen almacenado por tabla", "Mantenimiento: filas y rango temporal por tabla."),
]

SQL_SEED = [
    ("Borrado previo", "Elimina los datos del dispositivo de ejemplo para poder repetir la carga."),
    ("Alta del dispositivo", "Inserta `dev01` con su nombre y ubicacion; upsert idempotente."),
    ("288 lecturas", "Genera 24 horas con una lectura cada 5 minutos y ciclo diurno, mediante "
                     "una CTE recursiva."),
    ("Eventos", "Inserta dos eventos criticos y cinco cambios de estado alternos."),
    ("Comandos", "Seis comandos con distintos estados: OK, RECHAZADO y TIMEOUT, con latencias."),
    ("Transiciones", "Tres cambios de estado coherentes con los eventos insertados."),
]

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------
FRONTEND = {
    "backend/web/static/app.js": [
        ("Constantes `ESTADOS` y `MOTIVOS`", "Traducen los codigos del backend a textos y "
                                             "colores, y los motivos de rechazo a mensajes "
                                             "para el operador."),
        ("`pedir()`", "Envoltura de `fetch` con manejo de 401 y errores HTTP."),
        ("`aviso()`", "Muestra una notificacion efimera en la esquina inferior."),
        ("`numero()` y `hora()`", "Formatean magnitudes y horas para la interfaz."),
        ("`pintarEstado()`", "Actualiza estado, sensores, pildoras y tarjeta del sistema."),
        ("`pintarEventos()`", "Pinta el feed de eventos con su severidad y hora."),
        ("`pintarComandos()`", "Rellena la tabla de comandos con insignias de estado."),
        ("`dibujarGrafica()`", "Escala los ejes, dibuja rejilla, etiquetas y marcadores de alarma."),
        ("`dibujarSerie()`", "Traza una serie con relleno bajo la curva."),
        ("`enviarComando()`", "Publica el comando y muestra el resultado o el motivo del rechazo."),
        ("`pedirPin()`", "Dialogo modal que devuelve el PIN introducido."),
        ("`refrescarTodo()`", "Recarga estado, lecturas, eventos, comandos y estadisticas."),
        ("`conectarSSE()`", "Abre el canal de eventos y programa la reconexion con espera creciente."),
        ("`iniciar()`", "Arranque: enlaza botones, reloj, primera carga y canal en vivo. En modo "
                        "`?estatico=1` no abre SSE (se usa para capturas)."),
    ],
    "backend/web/static/index.html": [
        ("Barra superior", "Marca, nombre del dispositivo, pildoras de estado y boton Salir."),
        ("Estado de seguridad", "Estado grande, cerradura, sirena, alertas y nota contextual."),
        ("Sensores", "Seis magnitudes con icono, valor y unidad."),
        ("Estado del sistema", "Broker, nube, comandos pendientes, clientes y version."),
        ("Historico", "Canvas de la grafica y selector de 1 h / 6 h / 24 h."),
        ("Eventos", "Lista con contador en la cabecera."),
        ("Control remoto", "Cuatro botones de accion mas la nota de auditoria."),
        ("Ultimos comandos", "Tabla con comando, origen, estado y milisegundos."),
        ("Resumen 24 h", "Cuatro indicadores agregados."),
        ("Dialogo de PIN", "Elemento `<dialog>` con campo numerico y dos acciones."),
        ("Contenedor de avisos", "Zona donde se apilan las notificaciones."),
    ],
    "backend/web/static/styles.css": [
        ("Variables de tema", "Paleta oscura, radios y sombras en `:root`."),
        ("Barra y pildoras", "Cabecera fija, marca, indicadores de conexion y reloj."),
        ("Rejilla principal", "Tres columnas con dos puntos de corte para tablet y movil."),
        ("Tarjetas", "Fondo, borde, radio y sombra comun a todos los bloques."),
        ("Estado", "Color del borde izquierdo segun el estado y animacion de latido en alarma."),
        ("Magnitudes", "Rejilla de seis celdas con valor grande y unidad pequena."),
        ("Grafica y leyenda", "Altura del canvas y claves de color."),
        ("Eventos", "Lista con barra de severidad y scroll acotado."),
        ("Controles e insignias", "Botones de accion y chips de estado de comando."),
        ("Dialogo y avisos", "Modal de PIN y notificaciones flotantes."),
        ("Acceso", "Diseno de la pantalla de login."),
    ],
}

# ---------------------------------------------------------------------------
# Capitulo 3: funcionamiento, deteccion y cumplimiento
# ---------------------------------------------------------------------------
DETECCION = [
    ("PIR HC-SR501", "movimiento por infrarrojos", "flanco de subida de la salida digital",
     "alcance tipico 5-7 m con 100 grados de apertura; retencion de 1,5 s en el firmware",
     "alarma si el sistema esta ARMADO"),
    ("HC-SR04", "distancia por ultrasonido", "<= 80 cm (umbral configurable)",
     "2 a 400 cm utiles; el firmware toma la mediana de tres disparos",
     "alarma por presencia cercana si esta ARMADO"),
    ("DHT22", "temperatura", ">= 45 grados centigrados",
     "un solo punto junto al nodo", "alarma por sobrecalentamiento si esta ARMADO; aviso si no"),
    ("LDR", "luminosidad", "sin umbral de alarma",
     "mide lux del entorno; se publica como contexto", "no dispara alarma por si solo"),
    ("Pulsador", "accion manual", "pulsacion con antirrebote de 250 ms",
     "junto al nodo", "arma o desarma segun el estado actual"),
    ("Cerrojo con PIN", "control de acceso", "PIN correcto y sistema DESARMADO",
     "desde el panel o por comando de la nube", "abre 8 s y se cierra solo"),
]

NO_DETECTA = [
    "Identidad de la persona: no hay camara, reconocimiento facial ni huella.",
    "Apertura de puertas o ventanas: no hay sensor magnetico de contacto.",
    "Rotura de cristales: no hay sensor de vibracion ni de sonido.",
    "Humo, gas o monoxido: no hay detector de humo ni de gas.",
    "Presencia detras de un obstaculo: el PIR necesita linea de vision y el ultrasonido rebota.",
    "Mascotas pequenas por debajo del haz del PIR: pueden pasar sin activarlo.",
    "Manipulacion del propio nodo: la caida se detecta por MQTT, pero no se distingue un corte "
    "de corriente de un sabotaje.",
    "Personas que conozcan el PIN: el sistema autoriza, no identifica.",
]

CUMPLIMIENTO = [
    ("Mínimo 2 sensores diferentes", "Cumple", "4 sensores: DHT22, PIR, HC-SR04 y LDR",
     "`firmware/sensors.py`; telemetria con los cuatro valores"),
    ("Mínimo 2 actuadores", "Cumple", "5 actuadores: 2 LEDs, sirena, servo-cerradura y OLED",
     "`firmware/actuators.py`, `display.py`"),
    ("Código Python modular y documentado", "Cumple",
     "24 modulos, 33 clases y 328 funciones con docstrings",
     "catalogo del capitulo 1 de este documento"),
    ("Manejo de GPIO con librerías apropiadas", "Cumple",
     "`machine` (Pin, PWM, ADC, I2C, DHT22, time_pulse_us) aislado en un solo modulo",
     "`firmware/hal.py`"),
    ("Lectura de sensores en tiempo real", "Cumple",
     "periodos de 150 ms a 5 s con mediana y validacion de rangos",
     "`SensorSuite.actualizar`; capturas del monitor serie"),
    ("Control de actuadores", "Cumple",
     "LEDs, tono bitonal, angulo de servo y pantalla",
     "`Controlador._aplicar`; OLED en ARMADO y ALARMA"),
    ("Cliente MQTT en el dispositivo", "Cumple",
     "MQTT 3.1.1 propio sobre asyncio, QoS 0 y 1, LWT y reconexion",
     "`firmware/mqtt_client.py`; 45 pruebas de protocolo"),
    ("Broker HiveMQ / Mosquitto / EMQX", "Cumple",
     "HiveMQ publico en 1883 y soporte TLS 8883",
     "`config.py`, `.env.example`; telemetria real recibida"),
    ("Base de datos (SQLite local o remota)", "Cumple",
     "SQLite con 5 tablas, 5 vistas, 7 indices y WAL",
     "`sql/schema.sql`, `backend/storage.py`"),
    ("Almacenar lecturas con timestamp", "Cumple",
     "marca de tiempo del servidor en `ts_epoch` y `ts_utc`",
     "`Almacen.guardar_lectura`"),
    ("Registrar eventos y comandos ejecutados", "Cumple",
     "tablas `events` y `commands` con ACK, latencia y motivo",
     "`backend/commands.py`; tabla de comandos del panel"),
    ("Consultas para recuperar históricos", "Cumple",
     "12 consultas SQL documentadas, CLI y API REST",
     "`sql/consultas.sql`, `backend/cli.py`, `/api/lecturas`"),
    ("Plataforma en la nube", "Cumple",
     "ThingSpeak con canal de 8 campos y TalkBack",
     "`backend/cloud.py`, `docs/plataforma_nube.md`"),
    ("Dashboard de visualización en tiempo real", "Cumple",
     "panel aiohttp con SSE y grafica en canvas",
     "`backend/web/`; capturas `01` y `02`"),
    ("Recepción de comandos desde la nube", "Cumple",
     "TalkBack -> MQTT -> nodo -> ACK",
     "`Backend._bucle_talkback`; motivo `thingspeak` en la auditoria"),
    ("Programación modular y orientada a eventos", "Cumple",
     "bus de eventos con buzones y siete tareas asincronas",
     "`firmware/bus.py`, `backend/bus.py`"),
    ("Código fuente en GitHub", "Pendiente del estudiante",
     "repositorio Git inicializado con 101 archivos y sin secretos",
     "`docs/instalacion.md` seccion 8"),
    ("Código fuente en Teams", "Cumple",
     "paquete ZIP del repositorio y carpeta de entrega",
     "`entregables/`"),
    ("README", "Cumple", "presentacion, puesta en marcha y estructura",
     "`README.md`"),
    ("requirements.txt", "Cumple",
     "runtime y desarrollo separados, con versiones probadas",
     "`requirements.txt`, `requirements-dev.txt`"),
    ("Scripts SQL", "Cumple", "esquema, datos de ejemplo y consultas",
     "`sql/`"),
    ("Diagrama de la arquitectura", "Cumple", "cuatro capas con protocolos y topicos",
     "`docs/img/arquitectura.png`"),
    ("Diagrama de flujo de datos", "Cumple", "14 pasos con los topicos exactos",
     "`docs/img/flujo_datos.png`"),
    ("Diagrama de la plataforma cloud", "Cumple", "capa de nube y TalkBack",
     "`docs/img/arquitectura.png`, `docs/plataforma_nube.md`"),
    ("Diagrama del modelo de datos", "Cumple", "tablas, claves y cardinalidad",
     "`docs/img/modelo_datos.png`"),
    ("Capturas del circuito en Wokwi", "Cumple",
     "cinco capturas reales del simulador",
     "`docs/capturas/wokwi_01..05`"),
    ("Proyecto ZIP de Wokwi", "Cumple", "12 modulos, diagram.json y guia de importacion",
     "`entregables/Wokwi_Centinela_IoT.zip`"),
    ("Documentación de arquitectura, flujo y nube", "Cumple",
     "tres documentos tecnicos mas este anexo",
     "`docs/arquitectura.md`, `docs/flujo_datos.md`, `docs/plataforma_nube.md`"),
]

SALVEDADES = [
    ("Capturas propias de ThingSpeak y del repositorio",
     "El canal de ThingSpeak necesita las claves del estudiante y el repositorio aun no tiene "
     "remoto. El sistema funciona sin ellas; las capturas se toman al publicar.",
     "Crear el canal, copiar claves al `.env` y capturar; crear el remoto y hacer `push`."),
    ("Lectura del HC-SR04 en el simulador",
     "En la captura automatizada el sensor de distancia no entrego valores (`dist_cm` nulo y "
     "errores de sensor crecientes). La logica de distancia esta cubierta por pruebas "
     "unitarias, pero no se pudo verificar de extremo a extremo en el simulador.",
     "Verificar el disparo en un navegador normal y, si persiste, revisar tiempos del pulso o "
     "alimentar el sensor a 5 V."),
    ("Sensor de movimiento en navegador headless",
     "El boton *Simulate motion* del PIR no siempre llega al firmware cuando la simulacion "
     "corre sin interfaz visible; la alarma se verifico por comando de configuracion desde la "
     "nube, que es un camino legitimo del sistema.",
     "Repetir la captura en un navegador visible, donde el sensor responde."),
]


# Descripciones que faltaban (constructores y metodos internos), con clave
# calificada por ruta para no confundir nombres repetidos entre modulos.
import _datos_elementos  # noqa: E402

ELEMENTOS.update(_datos_elementos.ELEMENTOS_EXTRA)
