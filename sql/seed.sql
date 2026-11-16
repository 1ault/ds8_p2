-- =============================================================================
--  Centinela IoT - Datos de demostracion
--  Genera 24 horas de lecturas, eventos y comandos realistas para que el panel
--  y las consultas tengan contenido sin necesidad de esperar al simulador.
--
--  Uso:  sqlite3 data/centinela.db < sql/seed.sql
--  El script es idempotente: borra los datos del dispositivo dev01 antes de
--  insertarlos de nuevo.
-- =============================================================================

PRAGMA foreign_keys = ON;

DELETE FROM readings      WHERE device_id = 'dev01';
DELETE FROM events        WHERE device_id = 'dev01';
DELETE FROM commands      WHERE device_id = 'dev01';
DELETE FROM state_changes WHERE device_id = 'dev01';

INSERT INTO devices (device_id, nombre, ubicacion, firmware, creado_utc, visto_utc, visto_epoch)
VALUES ('dev01', 'Centinela - Puerta principal', 'Casa del estudiante',
        '2.0.0', strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-30 days'),
        strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), strftime('%s', 'now'))
ON CONFLICT(device_id) DO UPDATE SET
    nombre = excluded.nombre,
    visto_utc = excluded.visto_utc,
    visto_epoch = excluded.visto_epoch;

-- -----------------------------------------------------------------------------
-- Lecturas: una cada 5 minutos durante 24 horas (288 filas) con ciclo diurno
-- -----------------------------------------------------------------------------
WITH RECURSIVE serie(n) AS (
    SELECT 0
    UNION ALL
    SELECT n + 1 FROM serie WHERE n < 287
)
INSERT INTO readings (device_id, ts_epoch, ts_utc, temp_c, hum_pct, lux, dist_cm,
                      motion, state, alarm, siren, locked, alerts, rssi, seq, sensor_errors)
SELECT 'dev01',
       strftime('%s', 'now', '-24 hours', '+' || (n * 5) || ' minutes') + 0.0,
       strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-24 hours', '+' || (n * 5) || ' minutes'),
       ROUND(24.0 + 3.0 * sin((n % 288) * 3.14159 / 144.0) + (abs(random()) % 100) / 200.0, 1),
       ROUND(58.0 - 8.0 * sin((n % 288) * 3.14159 / 144.0) + (abs(random()) % 100) / 250.0, 1),
       CASE
           WHEN (n % 288) BETWEEN 96 AND 204 THEN 20.0 + (abs(random()) % 60)
           ELSE 1.0 + (abs(random()) % 18)
       END,
       ROUND(150.0 + (abs(random()) % 180) - 40.0 * sin((n % 288) * 3.14159 / 72.0), 1),
       CASE WHEN (abs(random()) % 100) < 6 THEN 1 ELSE 0 END,
       CASE
           WHEN (n % 288) BETWEEN 150 AND 156 THEN 'ALARM'
           WHEN (n % 288) BETWEEN 60  AND 149 THEN 'ARMED'
           ELSE 'DISARMED'
       END,
       CASE WHEN (n % 288) BETWEEN 150 AND 156 THEN 1 ELSE 0 END,
       0,
       1,
       0,
       -52 - (abs(random()) % 12),
       n,
       0
  FROM serie;

-- Dos lecturas con alarma y su evento critico asociado
INSERT INTO events (device_id, ts_epoch, ts_utc, kind, severity, message, state, data_json)
SELECT 'dev01',
       strftime('%s', 'now', '-6 hours') + 0.0,
       strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-6 hours'),
       'intrusion', 'critical', 'Alerta: presencia_cercana', 'ALARM',
       '{"cm": 42.5, "alerts": 1}'
UNION ALL
SELECT 'dev01',
       strftime('%s', 'now', '-5 hours') + 0.0,
       strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-5 hours'),
       'alarm_off', 'warning', 'Sirena silenciada (mute)', 'ALARM',
       NULL;

INSERT INTO events (device_id, ts_epoch, ts_utc, kind, severity, message, state, data_json)
SELECT 'dev01',
       strftime('%s', 'now', '-' || h || ' hours') + 0.0,
       strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-' || h || ' hours'),
       'state', 'info',
       CASE WHEN h % 2 = 0 THEN 'Cambio de estado DESARMED -> ARMED'
            ELSE 'Cambio de estado ARMED -> DISARMED' END,
       CASE WHEN h % 2 = 0 THEN 'ARMED' ELSE 'DISARMED' END,
       CASE WHEN h % 2 = 0 THEN '{"from": "DISARMED", "to": "ARMED", "reason": "arm"}'
            ELSE '{"from": "ARMED", "to": "DISARMED", "reason": "disarm"}' END
  FROM (SELECT 12 AS h UNION SELECT 10 UNION SELECT 8 UNION SELECT 4 UNION SELECT 2);

-- -----------------------------------------------------------------------------
-- Comandos: mezcla de ejecutados, rechazados y expirados
-- -----------------------------------------------------------------------------
INSERT INTO commands (id, device_id, cmd, args_json, source, estado,
                      emitido_epoch, emitido_utc, confirmado_epoch, confirmado_utc,
                      latencia_ms, resultado_json, motivo)
SELECT 'seed-arm-0001', 'dev01', 'arm', '{}', 'panel', 'OK',
       strftime('%s', 'now', '-10 hours') + 0.0,
       strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-10 hours'),
       strftime('%s', 'now', '-10 hours') + 0.42,
       strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-10 hours'),
       420, '{"state": "ARMING"}', NULL
UNION ALL
SELECT 'seed-unlock-0002', 'dev01', 'unlock', '{"pin": "****"}', 'panel', 'OK',
       strftime('%s', 'now', '-9 hours') + 0.0,
       strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-9 hours'),
       strftime('%s', 'now', '-9 hours') + 0.31,
       strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-9 hours'),
       310, '{"locked": false, "auto_relock_s": 8}', NULL
UNION ALL
SELECT 'seed-mute-0003', 'dev01', 'mute', '{}', 'dashboard', 'OK',
       strftime('%s', 'now', '-6 hours') + 0.0,
       strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-6 hours'),
       strftime('%s', 'now', '-6 hours') + 0.28,
       strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-6 hours'),
       280, '{"siren": false}', NULL
UNION ALL
SELECT 'seed-disarm-0004', 'dev01', 'disarm', '{}', 'thingspeak', 'OK',
       strftime('%s', 'now', '-5 hours') + 0.0,
       strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-5 hours'),
       strftime('%s', 'now', '-5 hours') + 0.55,
       strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-5 hours'),
       550, '{"state": "DISARMED"}', NULL
UNION ALL
SELECT 'seed-unlock-0005', 'dev01', 'unlock', '{"pin": "0000"}', 'dashboard', 'RECHAZADO',
       strftime('%s', 'now', '-4 hours') + 0.0,
       strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-4 hours'),
       strftime('%s', 'now', '-4 hours') + 0.19,
       strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-4 hours'),
       190, NULL, 'pin_incorrecto'
UNION ALL
SELECT 'seed-arm-0006', 'dev01', 'arm', '{}', 'panel', 'TIMEOUT',
       strftime('%s', 'now', '-3 hours') + 0.0,
       strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-3 hours'),
       NULL, NULL, NULL, NULL, 'sin_ack';

-- -----------------------------------------------------------------------------
-- Transiciones de estado
-- -----------------------------------------------------------------------------
INSERT INTO state_changes (device_id, ts_epoch, ts_utc, desde, hacia, motivo)
SELECT 'dev01', strftime('%s', 'now', '-10 hours') + 0.0,
       strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-10 hours'),
       'DISARMED', 'ARMING', 'arm'
UNION ALL
SELECT 'dev01', strftime('%s', 'now', '-6 hours') + 0.0,
       strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-6 hours'),
       'ARMED', 'ALARM', 'presencia_cercana'
UNION ALL
SELECT 'dev01', strftime('%s', 'now', '-5 hours') + 0.0,
       strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-5 hours'),
       'ALARM', 'DISARMED', 'disarm';
