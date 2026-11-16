"""Backend del sistema Centinela IoT (Parcial #2 - Desarrollo de Software VIII).

Paquetes:
    config      configuracion por entorno
    storage     acceso a SQLite
    mqtt_bridge puente paho-mqtt -> asyncio
    commands    validacion y auditoria de comandos
    cloud       ThingSpeak (canal + TalkBack)
    bus         eventos para el panel (SSE)
    web         API REST + panel
    cli         consultas de historicos por consola
"""

VERSION = "2.0.0"

__all__ = ["VERSION"]
