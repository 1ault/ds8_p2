-- =============================================================================
--  Centinela IoT - Consultas de historicos (12 casos de uso)
--
--  Pensadas para ejecutarse con sqlite3 o desde el backend. Los parametros
--  usan la forma :nombre; los valores sugeridos van en el comentario de cada
--  consulta. En la CLI del backend equivalen a los comandos indicados.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 01. Ultima lectura de cada dispositivo (estado actual de la casa)
--     CLI: python -m backend.cli resumen
-- -----------------------------------------------------------------------------
SELECT device_id                AS dispositivo,
       ts_utc                   AS momento,
       temp_c                   AS temperatura_c,
       hum_pct                  AS humedad_pct,
       lux                      AS luz_lux,
       dist_cm                  AS distancia_cm,
       state                    AS estado,
       alarm                    AS alarma
  FROM v_ultima_lectura
 ORDER BY device_id;


-- -----------------------------------------------------------------------------
-- 02. Historico de lecturas de las ultimas N horas
--     Parametros: :horas (6), :limite (200)
--     CLI: python -m backend.cli historico --horas 6
-- -----------------------------------------------------------------------------
SELECT ts_utc, temp_c, hum_pct, lux, dist_cm, motion, state
  FROM readings
 WHERE device_id = :device_id
   AND ts_epoch >= strftime('%s', 'now', '-' || :horas || ' hours')
 ORDER BY ts_epoch DESC
 LIMIT :limite;


-- -----------------------------------------------------------------------------
-- 03. Promedios por hora de las ultimas 24 horas (grafica de tendencia)
-- -----------------------------------------------------------------------------
SELECT strftime('%Y-%m-%d %H:00', bucket_epoch, 'unixepoch') AS hora,
       muestras,
       temp_media,
       temp_min,
       temp_max,
       hum_media,
       lux_media,
       dist_min,
       alarmas
  FROM v_resumen_horario
 WHERE device_id = :device_id
   AND bucket_epoch >= CAST(strftime('%s', 'now', '-24 hours') AS INTEGER)
 ORDER BY bucket_epoch;


-- -----------------------------------------------------------------------------
-- 04. Eventos criticos y advertencias (lo que el operador debe revisar)
--     CLI: python -m backend.cli eventos --severidad critical
-- -----------------------------------------------------------------------------
SELECT ts_utc, kind, severity, message, state
  FROM v_eventos_criticos
 WHERE device_id = :device_id
 ORDER BY ts_epoch DESC
 LIMIT 50;


-- -----------------------------------------------------------------------------
-- 05. Historial de comandos con su latencia y resultado
--     CLI: python -m backend.cli comandos
-- -----------------------------------------------------------------------------
SELECT emitido_utc                AS emitido,
       cmd                        AS comando,
       source                     AS origen,
       estado,
       latencia_ms,
       motivo
  FROM commands
 WHERE device_id = :device_id
 ORDER BY emitido_epoch DESC
 LIMIT 30;


-- -----------------------------------------------------------------------------
-- 06. Salud de los comandos por origen (que via funciona mejor)
-- -----------------------------------------------------------------------------
SELECT source                        AS origen,
       COUNT(*)                      AS total,
       SUM(CASE WHEN estado = 'OK' THEN 1 ELSE 0 END)        AS ok,
       SUM(CASE WHEN estado = 'RECHAZADO' THEN 1 ELSE 0 END) AS rechazados,
       SUM(CASE WHEN estado = 'TIMEOUT' THEN 1 ELSE 0 END)   AS sin_respuesta,
       ROUND(100.0 * SUM(CASE WHEN estado = 'OK' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_exito,
       ROUND(AVG(latencia_ms), 0)    AS latencia_media_ms
  FROM commands
 WHERE device_id = :device_id
 GROUP BY source
 ORDER BY total DESC;


-- -----------------------------------------------------------------------------
-- 07. Transiciones de la maquina de estados (quien armo o desarmo)
-- -----------------------------------------------------------------------------
SELECT ts_utc, desde, hacia, motivo
  FROM state_changes
 WHERE device_id = :device_id
 ORDER BY ts_epoch DESC
 LIMIT 25;


-- -----------------------------------------------------------------------------
-- 08. Rango termico e higrometrico por dia
-- -----------------------------------------------------------------------------
SELECT date(ts_epoch, 'unixepoch') AS dia,
       COUNT(*)                    AS lecturas,
       ROUND(MIN(temp_c), 1)       AS temp_min,
       ROUND(AVG(temp_c), 1)       AS temp_media,
       ROUND(MAX(temp_c), 1)       AS temp_max,
       ROUND(MIN(hum_pct), 1)      AS hum_min,
       ROUND(MAX(hum_pct), 1)      AS hum_max
  FROM readings
 WHERE device_id = :device_id
 GROUP BY dia
 ORDER BY dia DESC
 LIMIT 14;


-- -----------------------------------------------------------------------------
-- 09. Detecciones de movimiento por franja horaria (mapa de actividad)
-- -----------------------------------------------------------------------------
SELECT CAST(strftime('%H', ts_epoch, 'unixepoch') AS INTEGER) AS hora,
       COUNT(*)                                               AS lecturas,
       SUM(motion)                                            AS con_movimiento,
       SUM(alarm)                                             AS alarmas
  FROM readings
 WHERE device_id = :device_id
   AND ts_epoch >= strftime('%s', 'now', '-7 days')
 GROUP BY hora
 ORDER BY hora;


-- -----------------------------------------------------------------------------
-- 10. Alarmas por dia y duracion estimada de cada episodio
--     (cada grupo de lecturas consecutivas en ALARM = un episodio)
-- -----------------------------------------------------------------------------
SELECT date(ts_epoch, 'unixepoch')                          AS dia,
       COUNT(*)                                             AS lecturas_en_alarma,
       ROUND((MAX(ts_epoch) - MIN(ts_epoch)) / 60.0, 1)     AS minutos_estimados,
       MIN(ts_utc)                                          AS inicio,
       MAX(ts_utc)                                          AS fin
  FROM readings
 WHERE device_id = :device_id
   AND state = 'ALARM'
 GROUP BY dia
 ORDER BY dia DESC;


-- -----------------------------------------------------------------------------
-- 11. Huecos de telemetria (deteccion de caidas del nodo)
--     Muestra intervalos mayores a 30 s entre lecturas consecutivas.
-- -----------------------------------------------------------------------------
SELECT ts_utc                                          AS desde,
       ROUND(siguiente - ts_epoch, 1)                  AS segundos_sin_datos,
       datetime(ts_epoch, 'unixepoch')                 AS inicio,
       datetime(siguiente, 'unixepoch')                AS fin
  FROM (
        SELECT ts_epoch,
               ts_utc,
               LEAD(ts_epoch) OVER (ORDER BY ts_epoch) AS siguiente
          FROM readings
         WHERE device_id = :device_id
           AND ts_epoch >= strftime('%s', 'now', '-2 days')
       )
 WHERE siguiente - ts_epoch > 30
 ORDER BY ts_epoch DESC
 LIMIT 20;


-- -----------------------------------------------------------------------------
-- 12. Volumen almacenado por tabla y dispositivo (mantenimiento)
-- -----------------------------------------------------------------------------
SELECT 'readings' AS tabla, COUNT(*) AS filas, MIN(ts_utc) AS desde, MAX(ts_utc) AS hasta
  FROM readings WHERE device_id = :device_id
UNION ALL
SELECT 'events', COUNT(*), MIN(ts_utc), MAX(ts_utc)
  FROM events WHERE device_id = :device_id
UNION ALL
SELECT 'commands', COUNT(*), MIN(emitido_utc), MAX(emitido_utc)
  FROM commands WHERE device_id = :device_id
UNION ALL
SELECT 'state_changes', COUNT(*), MIN(ts_utc), MAX(ts_utc)
  FROM state_changes WHERE device_id = :device_id;
