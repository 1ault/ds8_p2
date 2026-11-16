"""Descripcion de los elementos que no tienen docstring propio.

Las claves van calificadas con la ruta del modulo (`ruta::Elemento`) porque hay
nombres repetidos entre archivos: `log` existe en los dos `main.py`, `_json` en
`storage.py` y en `web/app.py`, y `_texto` en la CLI.
"""

from __future__ import annotations

ELEMENTOS_EXTRA = {
    # ---------------------------------------------------------- actuators.py
    "firmware/actuators.py::Led.__init__": "Constructor: crea el pin de salida, lo apaga y "
                                           "guarda su nombre.",
    "firmware/actuators.py::Led.fijar": "Enciende o apaga segun el booleano recibido.",
    "firmware/actuators.py::Buzzer.__init__": "Constructor: crea el PWM en silencio (ciclo 0).",
    "firmware/actuators.py::Buzzer.fijar": "Enciende con la frecuencia indicada o apaga.",
    "firmware/actuators.py::Buzzer.deinit": "Apaga la sirena y libera el PWM.",
    "firmware/actuators.py::ServoLock.__init__": "Constructor: configura el PWM a 50 Hz y deja "
                                                 "el servo en la posicion cerrada.",
    "firmware/actuators.py::ServoLock._duty_para": "Convierte un angulo (0-180) en el ciclo de "
                                                   "trabajo de 16 bits que espera el servo.",
    "firmware/actuators.py::ServoLock.cerrar": "Lleva el servo a la posicion cerrada.",
    "firmware/actuators.py::ServoLock.abrir": "Lleva el servo a la posicion abierta.",
    "firmware/actuators.py::ServoLock.deinit": "Libera el PWM del servo.",
    "firmware/actuators.py::PanelActuadores.__init__": "Constructor: agrupa los actuadores y "
                                                       "prepara el estado de parpadeo.",
    "firmware/actuators.py::PanelActuadores.estado": "Devuelve el estado de los cuatro "
                                                     "actuadores en un diccionario.",

    # ---------------------------------------------------------------- app.py
    "firmware/app.py::Controlador.__init__": "Constructor: guarda dependencias, crea el bus, "
                                             "el buzon de comandos y el pulsador, y fija los "
                                             "contadores de secuencia y eventos.",
    "firmware/app.py::Controlador._ahora": "Devuelve el instante del reloj inyectado.",
    "firmware/app.py::Controlador.uptime_s": "Segundos transcurridos desde el arranque.",
    "firmware/app.py::Controlador._publicar_telemetria": "Construye y publica la telemetria, y "
                                                        "anota el instante del ultimo envio.",
    "firmware/app.py::Controlador._ciclo": "Un ciclo de seguridad: sensores, temporizadores, "
                                           "reglas y efectos.",
    "firmware/app.py::Controlador._ack": "Publica la confirmacion de un comando con su estado.",
    "firmware/app.py::Controlador._bucle_sensores": "Tarea que repite el ciclo de seguridad "
                                                    "cada 50 ms.",
    "firmware/app.py::Controlador._bucle_telemetria": "Tarea que publica telemetria cada 5 s.",
    "firmware/app.py::Controlador._bucle_comandos": "Tarea que consume el buzon de comandos y "
                                                    "los procesa fuera del callback de red.",
    "firmware/app.py::Controlador._bucle_leds": "Tarea de parpadeo de LEDs y tono bitonal de "
                                                "la sirena.",
    "firmware/app.py::Controlador._bucle_pantalla": "Tarea que refresca el OLED cada 600 ms.",
    "firmware/app.py::Controlador._bucle_boton": "Tarea que lee el pulsador con antirrebote.",
    "firmware/app.py::Controlador._bucle_mqtt": "Tarea supervisora: conecta, se suscribe, "
                                                "publica estado y reintenta con espera creciente.",

    # ---------------------------------------------------------------- bus.py
    "firmware/bus.py::Mailbox.__init__": "Constructor: buzon vacio con capacidad limitada.",
    "firmware/bus.py::Mailbox.offer": "Encola un evento; si esta lleno, descarta el mas viejo.",
    "firmware/bus.py::Mailbox.size": "Numero de eventos pendientes en el buzon.",
    "firmware/bus.py::Mailbox.get": "Espera y devuelve el siguiente evento.",
    "firmware/bus.py::Bus.__init__": "Constructor: lista de suscripciones vacia.",
    "firmware/bus.py::Bus.suscribir": "Crea un buzon para un patron de topico y lo registra.",
    "firmware/bus.py::Bus._coincide": "Compara el patron con el topico, con soporte de `*` y "
                                      "de comodin final `/*`.",

    # ------------------------------------------------------------ display.py
    "firmware/display.py::Pantalla.__init__": "Constructor: intenta crear el OLED y deja la "
                                              "pantalla marcada como no disponible si falla.",
    "firmware/display.py::Pantalla._linea": "Dibuja una linea de texto en la fila indicada.",
    "firmware/display.py::Pantalla.limpiar": "Borra el contenido de la pantalla.",
    "firmware/display.py::construir_desde_config": "Crea la pantalla con los pines y el tamano "
                                                   "del configuracion.",

    # ---------------------------------------------------------------- fsm.py
    "firmware/fsm.py::SecurityFSM.__init__": "Constructor: fija umbrales y tiempos, y deja el "
                                             "sistema desarmado y cerrado.",
    "firmware/fsm.py::SecurityFSM.armado": "Verdadero si la vigilancia esta activa (armando, "
                                           "armado o en alarma).",
    "firmware/fsm.py::SecurityFSM.en_alarma": "Verdadero solo en estado de alarma.",
    "firmware/fsm.py::SecurityFSM.restante_salida": "Segundos que faltan para armarse; cero si "
                                                    "no hay cuenta regresiva.",
    "firmware/fsm.py::SecurityFSM.resumen": "Resumen del estado para la telemetria.",
    "firmware/fsm.py::SecurityFSM._presencia": "Convierte una deteccion en alarma y sirena, "
                                               "respetando el antirrebote.",
    "firmware/fsm.py::_fx": "Construye un efecto con nombre y datos opcionales.",

    # ---------------------------------------------------------------- hal.py
    "firmware/hal.py::Pin.__init__": "Constructor: crea el pin de inmediato para fallar pronto "
                                     "si el GPIO no existe.",
    "firmware/hal.py::PWM.__init__": "Constructor: crea el PWM y aplica frecuencia y ciclo si "
                                     "se indican.",
    "firmware/hal.py::PWM._instancia": "Crea el objeto `machine.PWM` la primera vez.",
    "firmware/hal.py::PWM.deinit": "Libera el canal PWM.",
    "firmware/hal.py::ADC.__init__": "Constructor: guarda el numero de GPIO del conversor.",
    "firmware/hal.py::ADC._instancia": "Crea el ADC con atenuacion de 11 dB y ancho de 12 bits.",
    "firmware/hal.py::ADC.max_raw": "Valor maximo que puede entregar el conversor.",
    "firmware/hal.py::I2C": "Bus I2C 0 con SDA y SCL configurables y frecuencia dada.",
    "firmware/hal.py::I2C.__init__": "Constructor: guarda pines y frecuencia.",
    "firmware/hal.py::I2C._instancia": "Crea el objeto `machine.I2C` la primera vez.",
    "firmware/hal.py::I2C.writeto": "Escribe un bloque de bytes en una direccion.",
    "firmware/hal.py::I2C.scan": "Lista las direcciones que responden en el bus.",
    "firmware/hal.py::DHT22.__init__": "Constructor: guarda el GPIO del sensor.",
    "firmware/hal.py::DHT22._instancia": "Crea el objeto `dht.DHT22` la primera vez.",
    "firmware/hal.py::DHT22.measure": "Dispara una medicion y devuelve temperatura y humedad.",
    "firmware/hal.py::Reset.hard": "Reinicia el microcontrolador.",
    "firmware/hal.py::_machine": "Importa `machine` solo cuando se necesita.",
    "firmware/hal.py::pull_up": "Devuelve la constante de resistencia de subida del puerto.",
    "firmware/hal.py::entrada": "Crea un pin configurado como entrada.",
    "firmware/hal.py::salida": "Crea un pin configurado como salida.",

    # -------------------------------------------------------- mqtt_client.py
    "firmware/mqtt_client.py::MqttClient.__init__": "Constructor: guarda la configuracion y "
                                                    "prepara el estado de conexion y de ACK.",
    "firmware/mqtt_client.py::MqttClient._siguiente_id": "Entrega el siguiente identificador de "
                                                         "paquete, saltando el cero.",
    "firmware/mqtt_client.py::MqttClient._enviar": "Escribe en el socket con el lock tomado, "
                                                   "para que dos tareas no se intercalen.",
    "firmware/mqtt_client.py::_paquete": "Antepone tipo y longitud variable al cuerpo.",
    "firmware/mqtt_client.py::encode_puback": "Paquete PUBACK con el identificador recibido.",
    "firmware/mqtt_client.py::encode_pingreq": "Paquete PINGREQ (sin cuerpo).",
    "firmware/mqtt_client.py::encode_disconnect": "Paquete DISCONNECT (sin cuerpo).",
    "firmware/mqtt_client.py::_leer_cadena": "Lee una cadena con prefijo de longitud de dos bytes.",

    # ---------------------------------------------------------------- net.py
    "firmware/net.py::Wifi": "Conexion WiFi de la estacion con reintentos y consulta de estado.",
    "firmware/net.py::Wifi.__init__": "Constructor: guarda credenciales y tiempo limite.",
    "firmware/net.py::Wifi._interfaz": "Crea la interfaz de estacion la primera vez.",
    "firmware/net.py::Wifi.conectado": "Indica si la interfaz tiene conexion.",
    "firmware/net.py::Wifi.ip": "Direccion IP asignada.",
    "firmware/net.py::Wifi.estado": "Diccionario con conexion, IP, senal e intentos.",
    "firmware/net.py::_network": "Importa `network` solo cuando se necesita.",

    # ------------------------------------------------------------ sensors.py
    "firmware/sensors.py::DhtSensor.__init__": "Constructor: guarda reintentos y ventana de "
                                               "suavizado.",
    "firmware/sensors.py::PirSensor.__init__": "Constructor: crea el pin de entrada y el tiempo "
                                               "de retencion.",
    "firmware/sensors.py::UltrasonicSensor.__init__": "Constructor: prepara los pines de disparo "
                                                      "y eco, y deja el disparo en bajo.",
    "firmware/sensors.py::LightSensor.__init__": "Constructor: guarda la calibracion del modulo "
                                                 "(tension, RL10 y gamma).",
    "firmware/sensors.py::LightSensor._tope": "Valor maximo de lux que se informa.",
    "firmware/sensors.py::SensorSuite.__init__": "Constructor: prepara el estado por sensor y "
                                                 "marca todos como vencidos.",
    "firmware/sensors.py::SensorSuite.nombres": "Lista de los sensores registrados.",
    "firmware/sensors.py::SensorSuite.instantanea": "Copia de las ultimas lecturas conocidas.",
    "firmware/sensors.py::SensorSuite.total_errores": "Suma de lecturas fallidas.",
    "firmware/sensors.py::_mediana": "Mediana de una lista, sin ordenar la original.",

    # ------------------------------------------------------------ ssd1306.py
    "firmware/ssd1306.py::SSD1306.__init__": "Constructor: crea el framebuffer y envia la "
                                             "secuencia de inicializacion.",
    "firmware/ssd1306.py::SSD1306._comando": "Envia comandos al controlador (prefijo 0x00).",
    "firmware/ssd1306.py::SSD1306._datos": "Envia datos de pantalla (prefijo 0x40).",
    "firmware/ssd1306.py::SSD1306.iniciar": "Inicializa el panel, lo limpia y lo enciende.",
    "firmware/ssd1306.py::SSD1306.apagar": "Apaga el panel (comando 0xAE).",
    "firmware/ssd1306.py::SSD1306.encender": "Enciende el panel (comando 0xAF).",
    "firmware/ssd1306.py::SSD1306.contraste": "Ajusta el contraste del panel.",
    "firmware/ssd1306.py::SSD1306.limpiar": "Borra el framebuffer.",
    "firmware/ssd1306.py::SSD1306.pixel": "Dibuja un pixel.",
    "firmware/ssd1306.py::SSD1306.texto": "Dibuja texto con la fuente de 8x8 de `framebuf`.",
    "firmware/ssd1306.py::SSD1306.linea": "Dibuja una linea entre dos puntos.",
    "firmware/ssd1306.py::SSD1306.rectangulo": "Dibuja el contorno de un rectangulo.",
    "firmware/ssd1306.py::SSD1306.rectangulo_relleno": "Dibuja un rectangulo relleno.",
    "firmware/ssd1306.py::SSD1306.linea_horizontal": "Dibuja una linea horizontal.",

    # ---------------------------------------------------------------- bus.py
    "backend/bus.py::Suscriptor.__init__": "Constructor: cola acotada y contador de descartes.",
    "backend/bus.py::Suscriptor.pendientes": "Eventos en espera de envio.",
    "backend/bus.py::Hub.__init__": "Constructor: conjunto de suscriptores vacio.",
    "backend/bus.py::Hub.baja": "Elimina un suscriptor (panel desconectado).",
    "backend/bus.py::Hub.clientes": "Numero de paneles conectados.",

    # -------------------------------------------------------------- cloud.py
    "backend/cloud.py::NubeThingSpeak.__init__": "Constructor: guarda la configuracion y los "
                                                 "contadores de envio.",
    "backend/cloud.py::NubeThingSpeak.activa": "Verdadero si hay canal y clave de escritura.",
    "backend/cloud.py::NubeThingSpeak.talkback": "Verdadero si hay identificador y clave de "
                                                 "TalkBack.",
    "backend/cloud.py::NubeThingSpeak.estado": "Estado de la integracion para el panel.",
    "backend/cloud.py::NubeThingSpeak._obtener_sesion": "Crea la sesion HTTP la primera vez.",
    "backend/cloud.py::NubeThingSpeak.cerrar": "Cierra la sesion HTTP propia.",
    "backend/cloud.py::NubeNula.activa": "Siempre falso: modo local.",
    "backend/cloud.py::NubeNula.talkback": "Siempre falso: no hay cola de comandos.",
    "backend/cloud.py::NubeNula.estado": "Estado vacio para el panel.",
    "backend/cloud.py::NubeNula.subir": "No hace nada y devuelve falso.",
    "backend/cloud.py::NubeNula.siguiente_comando": "No hay comandos remotos.",
    "backend/cloud.py::NubeNula.cerrar": "Nada que cerrar.",

    # ----------------------------------------------------------- commands.py
    "backend/commands.py::ServicioComandos.__init__": "Constructor: prepara validador, "
                                                      "pendientes y contadores.",
    "backend/commands.py::ServicioComandos._publicar_hub": "Avisa al panel del resultado.",
    "backend/commands.py::ServicioComandos.pendientes": "Comandos esperando ACK.",
    "backend/commands.py::ServicioComandos.cerrar": "Cancela las esperas pendientes al apagar.",

    # ------------------------------------------------------------- config.py
    "backend/config.py::Config.base_topicos": "Prefijo comun de los topicos del dispositivo.",
    "backend/config.py::Config.topico_telemetria": "Topico de telemetria.",
    "backend/config.py::Config.topico_eventos": "Topico de eventos.",
    "backend/config.py::Config.topico_estado": "Topico de estado con retencion.",
    "backend/config.py::Config.topico_comando": "Topico de comandos.",
    "backend/config.py::Config.topico_ack": "Topico de confirmaciones.",
    "backend/config.py::Config.topico_config": "Topico de configuracion en caliente.",
    "backend/config.py::Config.topico_suscripcion": "Comodin con el que se suscribe el backend.",
    "backend/config.py::Config.nube_activa": "Verdadero si ThingSpeak esta configurado.",
    "backend/config.py::Config.talkback_activo": "Verdadero si TalkBack esta configurado.",
    "backend/config.py::_booleano": "Interpreta un valor de entorno como booleano.",

    # --------------------------------------------------------------- main.py
    "backend/main.py::Backend.__init__": "Constructor: crea almacen, hub, puente, nube, "
                                         "servicio de comandos y aplicacion web.",
    "backend/main.py::Backend._iniciar_web": "Arranca el servidor aiohttp en el puerto "
                                             "configurado.",
    "backend/main.py::Backend.esperar": "Se bloquea hasta que se solicite la parada.",
    "backend/main.py::Backend.solicitar_parada": "Marca la parada ordenada (senales del sistema).",

    # -------------------------------------------------------- mqtt_bridge.py
    "backend/mqtt_bridge.py::PuenteMqtt.__init__": "Constructor: cola asincrona y contadores.",
    "backend/mqtt_bridge.py::PuenteMqtt._crear_cliente": "Crea el cliente paho con credenciales "
                                                         "y TLS si estan configurados.",
    "backend/mqtt_bridge.py::PuenteMqtt._conectar_callbacks": "Asocia los callbacks de conexion, "
                                                              "desconexion y mensaje.",
    "backend/mqtt_bridge.py::PuenteMqtt.detener": "Detiene el bucle de red y desconecta.",
    "backend/mqtt_bridge.py::PuenteMqtt._al_conectar": "Suscribe al comodin y libera la espera "
                                                       "del arranque.",
    "backend/mqtt_bridge.py::PuenteMqtt._al_desconectar": "Marca la caida y avisa a la cola.",
    "backend/mqtt_bridge.py::PuenteMqtt._al_recibir": "Copia el mensaje y lo entrega al bucle "
                                                      "asincrono.",
    "backend/mqtt_bridge.py::PuenteMqtt.estado": "Estado del enlace para el panel.",

    # ------------------------------------------------------------- storage.py
    "backend/storage.py::Almacen.__init__": "Constructor: guarda la ruta, el reloj y el lock.",
    "backend/storage.py::Almacen._crear_conexion": "Abre SQLite con WAL, claves foraneas y "
                                                   "sincronizacion normal.",
    "backend/storage.py::Almacen._cerrar_hilo": "Confirma y cierra la conexion en su hilo.",
    "backend/storage.py::Almacen._leer": "Ejecuta una consulta de lectura serializada.",
    "backend/storage.py::Almacen._filas": "Devuelve todas las filas de una consulta.",
    "backend/storage.py::Almacen._ejecutar_escritura": "Ejecuta un INSERT y devuelve el rowid.",
    "backend/storage.py::Almacen._ejecutar_actualizacion": "Ejecuta un UPDATE y devuelve las "
                                                           "filas afectadas.",
    "backend/storage.py::Almacen._requerir": "Devuelve la conexion o falla si el almacen esta "
                                             "cerrado.",
    "backend/storage.py::Almacen.dispositivos": "Lista de dispositivos registrados.",
    "backend/storage.py::Almacen._expirar_hilo": "Marca TIMEOUT los comandos vencidos.",
    "backend/storage.py::Almacen.estado_comandos": "Conteo de comandos por estado.",
    "backend/storage.py::Almacen.registrar_cambio_estado": "Guarda una transicion de la maquina "
                                                           "de estados.",
    "backend/storage.py::Almacen.cambios_estado": "Ultimas transiciones del dispositivo.",
    "backend/storage.py::Almacen._purgar_hilo": "Borra datos anteriores al limite en una "
                                                "transaccion.",
    "backend/storage.py::a_epoch": "Convierte un datetime en segundos epoch.",
    "backend/storage.py::desde_epoch": "Convierte segundos epoch en datetime UTC.",
    "backend/storage.py::_ent": "Convierte a entero con valor por defecto.",
    "backend/storage.py::_json": "Convierte texto JSON en objeto, tolerando errores.",
    "backend/storage.py::_con_datos": "Convierte la fila de evento y expande `data_json`.",

    # ------------------------------------------------------------ web/app.py
    "backend/web/app.py::_json": "Respuesta JSON con UTF-8 sin escapar.",
    "backend/web/app.py::_html": "Devuelve un archivo HTML de los estaticos.",
    "backend/web/app.py::_servicios": "Acceso al diccionario de servicios de la aplicacion.",

    # ----------------------------------------------------------- web/auth.py
    "backend/web/auth.py::_b64": "Codifica en base64url sin relleno.",
    "backend/web/auth.py::_de_b64": "Decodifica base64url anadiendo el relleno que falta.",
}
