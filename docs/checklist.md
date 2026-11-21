# Checklist de entregables

Verificación punto por punto del enunciado del **Parcial #2** (escenario 4:
*Sistema de Seguridad — Detección y alertas*).

---

## 1. Requisitos funcionales

| Requisito del enunciado | Estado | Dónde se cumple |
|-------------------------|--------|-----------------|
| Mínimo 2 sensores diferentes | ✅ **4** | DHT22, PIR, HC-SR04 y LDR en `firmware/sensors.py` |
| Mínimo 2 actuadores | ✅ **5** | LED rojo, LED verde, buzzer, servo-cerradura y OLED en `firmware/actuators.py` y `display.py` |
| Código Python modular y documentado | ✅ | 12 módulos de firmware + 11 de backend, con docstrings y comentarios |
| Manejo de GPIO con librerías apropiadas | ✅ | `machine` (Pin, PWM, ADC, I2C, `time_pulse_us`) aislado en `firmware/hal.py` |
| Lectura de sensores en tiempo real | ✅ | periodos de 150 ms a 5 s con mediana y validación (`sensors.py`) |
| Control de actuadores | ✅ | `_aplicar` en `firmware/app.py` y `actuators.py` |
| Cliente MQTT en el dispositivo | ✅ | MQTT 3.1.1 propio sobre asyncio, QoS 0/1, LWT (`firmware/mqtt_client.py`) |
| Broker HiveMQ / Mosquitto / EMQX | ✅ | HiveMQ público y soporte TLS 8883 (`config.py`, `.env.example`) |
| Base de datos (SQLite) | ✅ | 5 tablas, 5 vistas e índices (`sql/schema.sql`, `backend/storage.py`) |
| Almacenar lecturas con timestamp | ✅ | `readings.ts_epoch` y `readings.ts_utc` puestos por el servidor |
| Registrar eventos y comandos ejecutados | ✅ | tablas `events` y `commands` con ACK, latencia y motivo |
| Consultas para recuperar históricos | ✅ | 12 consultas SQL + CLI + API REST |
| Plataforma en la nube | ✅ | ThingSpeak: canal de 8 campos (`backend/cloud.py`) |
| Dashboard de visualización en tiempo real | ✅ | panel aiohttp con SSE y gráfica en canvas |
| Recepción de comandos desde la nube | ✅ | TalkBack → `.../cmd` → ACK (`backend/main.py`) |
| Programación modular y orientada a eventos | ✅ | bus de eventos + FSM + tareas asíncronas |

---

## 2. Entregables

| Entregable | Estado | Ubicación |
|------------|--------|-----------|
| Código fuente estructurado en GitHub | ⏳ listo para `git push` | instrucciones en [`instalacion.md`](instalacion.md#8-publicación-en-github-y-teams) |
| Código en Teams | ✅ | `entregables/Parcial2_IoT_Seguridad.zip` |
| README | ✅ | `README.md` |
| `requirements.txt` | ✅ | `requirements.txt` (runtime) y `requirements-dev.txt` (pruebas y herramientas) |
| Scripts SQL | ✅ | `sql/schema.sql`, `sql/seed.sql`, `sql/consultas.sql` |
| Diagrama de la arquitectura | ✅ | `docs/img/arquitectura.png` + [`arquitectura.md`](arquitectura.md) |
| Diagrama de flujo de datos | ✅ | `docs/img/flujo_datos.png` + [`flujo_datos.md`](flujo_datos.md) |
| Diagrama de la plataforma cloud | ✅ | `docs/img/arquitectura.png` (capa 4) + [`plataforma_nube.md`](plataforma_nube.md) |
| Diagrama del modelo de datos | ✅ | `docs/img/modelo_datos.png` + [`base_datos.md`](base_datos.md) |
| Diagrama de la máquina de estados | ✅ | `docs/img/fsm.png` |
| Diagrama del circuito | ✅ | `docs/img/circuito.png` |
| Capturas del circuito en Wokwi | ✅ | `docs/capturas/wokwi_01..05_*.png` (proyecto real, ver [`guia_demo.md`](guia_demo.md#4-capturas-del-simulador-de-wokwi)) |
| Proyecto ZIP de Wokwi | ✅ | `entregables/Wokwi_Centinela_IoT.zip` |
| Documentación de la arquitectura IoT | ✅ | [`arquitectura.md`](arquitectura.md) |
| Documentación del flujo de datos | ✅ | [`flujo_datos.md`](flujo_datos.md) |
| Documentación de la plataforma Cloud | ✅ | [`plataforma_nube.md`](plataforma_nube.md) |
| Manual técnico | ✅ | `docs/manuales/Manual_Tecnico_Centinela_IoT.docx` (33 páginas) |
| Manual del usuario | ✅ | `docs/manuales/Manual_Usuario_Centinela_IoT.docx` (22 páginas) |
| Informe técnico | ✅ | `docs/manuales/Informe_Tecnico_Centinela_IoT.docx` (21 páginas) |
| Documentación extendida | ✅ | `docs/manuales/Documentacion_Extendida_Centinela_IoT.docx` (45 páginas) |
| Guía de prueba del monitoreo | ✅ | `docs/manuales/Guia_Prueba_Monitoreo.docx` (12 páginas) |
| Guía de instalación y montaje | ✅ | `docs/manuales/Guia_Instalacion_Montaje.docx` (20 páginas) |
| Guía de entrega | ✅ | `entregables/LEEME_ENTREGA.md` |
| Capturas de ejecución | ✅ | `docs/capturas/` (12 imágenes reales: panel, login, CLI y simulador) |
| Manifiesto con hashes | ✅ | `entregables/MANIFIESTO.txt` |

Leyenda: ✅ incluido · ⏳ requiere un paso del estudiante · ⚠️ requiere su cuenta.

---

## 3. Criterios de evaluación

| Criterio | Cómo se demuestra |
|----------|-------------------|
| Funcionamiento completo | `python scripts/demo.py` recorre sensores → alarma → panel → nube → comando |
| Calidad del código | módulos de una sola responsabilidad, docstrings, sin números mágicos (`config.py`), 100 % SQL parametrizado |
| Integración de todos los componentes | MQTT real con HiveMQ, SQLite, ThingSpeak, aiohttp y ESP32 en Wokwi |
| Documentación | 6 documentos técnicos + 5 diagramas + 7 capturas reales |

---

## 4. Evidencias de ejecución

| Evidencia | Archivo |
|-----------|---------|
| 324 pruebas automatizadas | `docs/capturas/` y salida de `python -m pytest` |
| Panel en operación | `docs/capturas/01_panel_estado.png` |
| Alarma en curso | `docs/capturas/02_panel_alarma.png` |
| Acceso al panel | `docs/capturas/03_login.png` |
| Histórico por consola | `docs/capturas/04_cli_historico.png` |
| Eventos del sistema | `docs/capturas/05_cli_eventos.png` |
| Estadísticas | `docs/capturas/06_cli_estadisticas.png` |
| Comandos auditados | `docs/capturas/07_cli_comandos.png` |

---

## 5. Antes de entregar

1. `python -m pytest` → 324 aprobadas.
2. `python scripts\demo.py --reset --sembrar` → panel con datos y alarma.
3. Importar el ZIP en Wokwi y comprobar que conecta.
4. Completar `.env` con las claves de ThingSpeak y ver una subida.
5. Tomar las capturas de la sección 4 de `guia_demo.md`.
6. Confirmar que no se suben `.env` ni `data/*.db`.
7. `python scripts\empaquetar.py` para regenerar los ZIP y el manifiesto.
8. Subir a GitHub y a Teams.
