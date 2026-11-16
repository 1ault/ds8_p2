/* ==========================================================================
   Centinela IoT - logica del panel
   - carga inicial + refresco periodico
   - actualizaciones en vivo por SSE (con reconexion)
   - grafica dibujada a mano en canvas (sin librerias)
   ========================================================================== */

(() => {
  'use strict';

  const ESTADOS = {
    DISARMED: { texto: 'DESARMADO', color: '#38bdf8' },
    ARMING:   { texto: 'ARMANDO',   color: '#f59e0b' },
    ARMED:    { texto: 'ARMADO',    color: '#22c55e' },
    ALARM:    { texto: 'ALARMA',    color: '#ef4444' },
  };

  const MOTIVOS = {
    timeout: 'El nodo no confirmó el comando (timeout)',
    sin_conexion_mqtt: 'Sin conexión con el broker MQTT',
    pin_invalido: 'El PIN debe tener entre 4 y 8 dígitos',
    pin_incorrecto: 'PIN incorrecto',
    pin_bloqueado: 'Demasiados intentos: cerradura bloqueada 30 s',
    sistema_armado: 'Desarma el sistema antes de abrir la cerradura',
    comando_no_permitido: 'Comando no permitido',
    publicacion_fallida: 'No se pudo publicar el comando',
    demasiados_comandos: 'Demasiados comandos en poco tiempo',
    json_invalido: 'Petición inválida',
  };

  const $ = (id) => document.getElementById(id);
  const estado = {
    horas: 1,
    series: [],
    sse: null,
    intentosSSE: 0,
    temporizador: null,
    ultimaActualizacion: 0,
  };

  // ------------------------------------------------------------ utilidades
  async function pedir(url, opciones) {
    const respuesta = await fetch(url, Object.assign({ headers: { 'Accept': 'application/json' } }, opciones || {}));
    if (respuesta.status === 401) { window.location.href = '/login'; throw new Error('sin sesión'); }
    if (!respuesta.ok) throw new Error('HTTP ' + respuesta.status);
    return respuesta.json();
  }

  function aviso(texto, tipo) {
    const caja = document.createElement('div');
    caja.className = 'aviso ' + (tipo || '');
    caja.textContent = texto;
    $('avisos').appendChild(caja);
    setTimeout(() => caja.remove(), 4200);
  }

  function numero(valor, decimales) {
    if (valor === null || valor === undefined || isNaN(valor)) return '—';
    return Number(valor).toFixed(decimales === undefined ? 1 : decimales);
  }

  function hora(iso) {
    if (!iso) return '--:--';
    const fecha = new Date(iso);
    if (isNaN(fecha)) return '--:--';
    return fecha.toLocaleTimeString('es-PA', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  // --------------------------------------------------------------- estado
  function pintarEstado(datos) {
    const lectura = datos.lectura || {};
    const estadoNombre = datos.estado_seguridad || 'DESCONOCIDO';
    const info = ESTADOS[estadoNombre] || { texto: estadoNombre, color: '#93a4c0' };

    const tarjeta = $('tarjeta-estado');
    tarjeta.dataset.estado = estadoNombre;
    $('estado-nombre').textContent = info.texto;
    $('estado-nombre').style.color = info.color;
    $('estado-indicador').style.background = info.color;
    $('estado-indicador').style.boxShadow = '0 0 0 6px ' + info.color + '22';

    $('estado-cerradura').textContent = lectura.locked ? 'Cerrada' : 'ABIERTA';
    $('estado-sirena').textContent = lectura.siren ? 'Sonando' : 'Silenciosa';
    $('estado-alertas').textContent = lectura.alerts ?? 0;

    const partes = [];
    if (lectura.ts_utc) partes.push('Última lectura ' + hora(lectura.ts_utc));

    if (datos.dispositivo && datos.dispositivo.nombre) {
      $('dispositivo').textContent = datos.dispositivo.nombre + ' · ' + (datos.dispositivo.device_id || 'dev01');
    }

    // magnitudes
    $('valor-temp').textContent = numero(lectura.temp_c);
    $('valor-hum').textContent = numero(lectura.hum_pct);
    $('valor-lux').textContent = numero(lectura.lux, 0);
    $('valor-dist').textContent = numero(lectura.dist_cm, 0);
    $('valor-mov').textContent = lectura.motion ? 'Sí' : 'No';
    $('valor-mov').style.color = lectura.motion ? '#f59e0b' : '';
    $('valor-rssi').textContent = lectura.rssi ?? '—';

    if (estadoNombre === 'ARMING') partes.push('Cuenta regresiva de salida en curso');
    if (estadoNombre === 'ALARM') partes.push('Alarma activa: revisa los eventos');
    if (!datos.mqtt.conectado) partes.push('Broker MQTT desconectado');
    $('estado-nota').textContent = partes.join(' · ') || 'Sin datos todavía';

    pildoras(datos);
    $('eventos-total').textContent = datos.alertas ?? 0;
    $('stat-alarmas').textContent = (datos.comandos && datos.comandos.TIMEOUT) || 0;

    $('sistema-mqtt').textContent = datos.mqtt.conectado ? 'conectado' : 'desconectado';
    $('sistema-nube').textContent = datos.nube.activa
      ? 'activa · ' + (datos.nube.enviados || 0) + ' envíos'
      : 'desactivada';
    $('sistema-pendientes').textContent = datos.comandos_pendientes ?? 0;
    $('sistema-clientes').textContent = datos.clientes_sse ?? 0;
    $('sistema-version').textContent = datos.version || '—';
  }

  function pildoras(datos) {
    const mqtt = $('pildora-mqtt');
    mqtt.classList.toggle('ok', !!datos.mqtt.conectado);
    mqtt.classList.toggle('mal', !datos.mqtt.conectado);
    mqtt.querySelector('b').textContent = datos.mqtt.conectado ? 'OK' : 'OFF';

    const nube = $('pildora-nube');
    nube.classList.toggle('ok', !!datos.nube.activa);
    nube.querySelector('b').textContent = datos.nube.activa ? (datos.nube.enviados + '↑') : 'OFF';
  }

  // -------------------------------------------------------------- eventos
  function pintarEventos(datos) {
    const lista = $('lista-eventos');
    const eventos = datos.eventos || [];
    if (!eventos.length) {
      lista.innerHTML = '<li class="vacio">Sin eventos registrados</li>';
      return;
    }
    lista.innerHTML = eventos.map((evento) => {
      const severidad = evento.severity || 'info';
      return '<li class="sev-' + severidad + '">' +
        '<span class="hora">' + hora(evento.ts_utc) + '</span>' +
        '<span class="texto">' + escapar(evento.message || '') +
        '<span class="tipo">' + escapar(evento.kind || '') + ' · ' + severidad + '</span></span>' +
        '</li>';
    }).join('');
  }

  function pintarComandos(datos) {
    const cuerpo = $('tabla-comandos');
    const comandos = datos.comandos || [];
    $('comandos-total').textContent = comandos.length;
    if (!comandos.length) {
      cuerpo.innerHTML = '<tr><td colspan="4" class="vacio">Sin comandos</td></tr>';
      return;
    }
    cuerpo.innerHTML = comandos.map((c) => {
      const insignia = '<span class="insignia ' + (c.estado || 'PENDIENTE') + '">' + (c.estado || '—') + '</span>';
      return '<tr><td>' + escapar(c.cmd || '') + '</td>' +
        '<td>' + escapar(c.source || '') + '</td>' +
        '<td>' + insignia + '</td>' +
        '<td>' + (c.latencia_ms === null || c.latencia_ms === undefined ? '—' : c.latencia_ms) + '</td></tr>';
    }).join('');
  }

  function pintarEstadisticas(datos) {
    $('stat-lecturas').textContent = datos.total || 0;
    $('stat-temp-media').textContent = numero(datos.temp_media, 1);
    $('stat-alarmas').textContent = datos.alarmas || 0;
    $('stat-latencia').textContent = datos.latencia_media_ms === null || datos.latencia_media_ms === undefined
      ? '—' : Math.round(datos.latencia_media_ms);
  }

  function escapar(texto) {
    return String(texto).replace(/[&<>"']/g, (c) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }

  // --------------------------------------------------------------- grafica
  function dibujarGrafica(series) {
    const canvas = $('grafica');
    const ancho = canvas.clientWidth || 640;
    const alto = 240;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(ancho * dpr);
    canvas.height = Math.round(alto * dpr);
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, ancho, alto);

    const margen = { izq: 44, der: 46, arr: 14, abajo: 26 };
    const util = {
      x: margen.izq,
      y: margen.arr,
      ancho: ancho - margen.izq - margen.der,
      alto: alto - margen.arr - margen.abajo,
    };

    const puntos = (series || []).filter((p) => p.temp_c !== null || p.hum_pct !== null);
    if (puntos.length < 2) {
      ctx.fillStyle = '#93a4c0';
      ctx.font = '13px "Segoe UI", system-ui, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Sin datos suficientes en este rango', ancho / 2, alto / 2);
      $('muestras').textContent = '0 muestras';
      return;
    }

    const temps = puntos.map((p) => p.temp_c).filter((v) => v !== null && v !== undefined);
    let tMin = Math.min.apply(null, temps);
    let tMax = Math.max.apply(null, temps);
    if (tMax - tMin < 2) { tMin -= 1; tMax += 1; }
    const tPad = (tMax - tMin) * 0.12;
    tMin -= tPad; tMax += tPad;

    const hMin = 0, hMax = 100;
    const n = puntos.length;
    const X = (i) => util.x + (util.ancho * i) / (n - 1);
    const Ytemp = (v) => util.y + util.alto - ((v - tMin) / (tMax - tMin)) * util.alto;
    const Yhum = (v) => util.y + util.alto - ((v - hMin) / (hMax - hMin)) * util.alto;

    // rejilla horizontal
    ctx.strokeStyle = 'rgba(35, 48, 74, .8)';
    ctx.lineWidth = 1;
    ctx.font = '11px "Segoe UI", system-ui, sans-serif';
    ctx.textBaseline = 'middle';
    for (let i = 0; i <= 4; i += 1) {
      const y = util.y + (util.alto * i) / 4;
      ctx.beginPath();
      ctx.moveTo(util.x, y);
      ctx.lineTo(util.x + util.ancho, y);
      ctx.stroke();

      const valorTemp = tMax - ((tMax - tMin) * i) / 4;
      ctx.fillStyle = '#ef4444';
      ctx.textAlign = 'right';
      ctx.fillText(valorTemp.toFixed(1) + '°', util.x - 8, y);

      const valorHum = hMax - ((hMax - hMin) * i) / 4;
      ctx.fillStyle = '#38bdf8';
      ctx.textAlign = 'left';
      ctx.fillText(Math.round(valorHum) + '%', util.x + util.ancho + 8, y);
    }

    // etiquetas de tiempo
    ctx.fillStyle = '#93a4c0';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    const marcas = Math.min(6, n);
    for (let i = 0; i < marcas; i += 1) {
      const indice = Math.round((n - 1) * (i / (marcas - 1 || 1)));
      ctx.fillText(hora(puntos[indice].ts_utc), X(indice), util.y + util.alto + 8);
    }

    dibujarSerie(ctx, puntos, (p) => p.hum_pct, X, Yhum, '#38bdf8',
                 'rgba(56, 189, 248, .16)', util.y + util.alto);
    dibujarSerie(ctx, puntos, (p) => p.temp_c, X, Ytemp, '#ef4444',
                 'rgba(239, 68, 68, .14)', util.y + util.alto);

    // marcadores de alarma
    puntos.forEach((p, i) => {
      if (!p.alarm) return;
      ctx.beginPath();
      ctx.arc(X(i), util.y + util.alto - 4, 3.2, 0, Math.PI * 2);
      ctx.fillStyle = '#ef4444';
      ctx.fill();
    });

    $('muestras').textContent = n + ' muestras';
  }

  function dibujarSerie(ctx, puntos, valor, X, Y, color, relleno, baseY) {
    const coordenadas = [];
    puntos.forEach((p, i) => {
      const v = valor(p);
      if (v === null || v === undefined || isNaN(v)) { coordenadas.push(null); return; }
      coordenadas.push([X(i), Y(Number(v))]);
    });

    const validas = coordenadas.filter(Boolean);
    if (!validas.length) return;

    // area bajo la curva
    if (validas.length > 1) {
      ctx.beginPath();
      ctx.moveTo(validas[0][0], baseY);
      validas.forEach((c) => ctx.lineTo(c[0], c[1]));
      ctx.lineTo(validas[validas.length - 1][0], baseY);
      ctx.closePath();
      ctx.fillStyle = relleno;
      ctx.fill();
    }

    // linea
    ctx.beginPath();
    let empezado = false;
    coordenadas.forEach((c) => {
      if (!c) { empezado = false; return; }
      if (!empezado) { ctx.moveTo(c[0], c[1]); empezado = true; }
      else ctx.lineTo(c[0], c[1]);
    });
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.stroke();
  }

  // ---------------------------------------------------------------- control
  async function enviarComando(cmd, args, boton) {
    if (boton) boton.disabled = true;
    try {
      const resultado = await pedir('/api/comando', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cmd: cmd, args: args || {} }),
      });
      if (resultado.ok) {
        aviso('Comando «' + cmd + '» confirmado por el nodo', 'ok');
      } else {
        const motivo = MOTIVOS[resultado.motivo] || ('Rechazado: ' + (resultado.motivo || 'desconocido'));
        aviso(motivo, 'mal');
      }
      await refrescarTodo();
    } catch (error) {
      aviso('Error enviando el comando: ' + error.message, 'mal');
    } finally {
      if (boton) boton.disabled = false;
    }
  }

  function pedirPin() {
    const dialogo = $('dialogo-pin');
    const campo = $('campo-pin');
    campo.value = '';
    dialogo.showModal();
    setTimeout(() => campo.focus(), 60);

    return new Promise((resolver) => {
      const alCerrar = () => {
        dialogo.removeEventListener('close', alCerrar);
        const texto = campo.value.trim();
        resolver(dialogo.returnValue === 'aceptar' ? texto : null);
      };
      dialogo.addEventListener('close', alCerrar);
      $('form-pin').onsubmit = () => {
        dialogo.close('aceptar');
        return false;
      };
    });
  }

  // --------------------------------------------------------------- refresco
  async function refrescarTodo() {
    try {
      const [estadoDatos, lecturas, eventos, comandos, estadisticas] = await Promise.all([
        pedir('/api/estado'),
        pedir('/api/lecturas?horas=' + estado.horas + '&limite=600'),
        pedir('/api/eventos?limite=30'),
        pedir('/api/comandos?limite=12'),
        pedir('/api/estadisticas'),
      ]);
      pintarEstado(estadoDatos);
      estado.series = lecturas.series || [];
      dibujarGrafica(estado.series);
      pintarEventos(eventos);
      pintarComandos(comandos);
      pintarEstadisticas(estadisticas);
      estado.ultimaActualizacion = Date.now();
    } catch (error) {
      aviso('No se pudo refrescar: ' + error.message, 'mal');
    }
  }

  function programarRefresco() {
    if (estado.temporizador) return;
    estado.temporizador = setTimeout(() => {
      estado.temporizador = null;
      refrescarTodo();
    }, 400);
  }

  // ------------------------------------------------------------------- SSE
  function conectarSSE() {
    if (estado.sse) estado.sse.close();
    const pildora = $('pildora-sse');
    const fuente = new EventSource('/api/stream');
    estado.sse = fuente;

    fuente.onopen = () => {
      estado.intentosSSE = 0;
      pildora.classList.add('ok');
      pildora.classList.remove('mal');
      pildora.querySelector('b').textContent = 'ON';
    };

    fuente.onerror = () => {
      pildora.classList.remove('ok');
      pildora.classList.add('mal');
      pildora.querySelector('b').textContent = 'OFF';
      fuente.close();
      estado.intentosSSE += 1;
      const espera = Math.min(15000, 1000 * Math.pow(1.6, estado.intentosSSE));
      setTimeout(conectarSSE, espera);
    };

    ['lectura', 'evento', 'comando', 'estado'].forEach((tipo) => {
      fuente.addEventListener(tipo, (mensaje) => {
        try {
          const datos = JSON.parse(mensaje.data);
          if (tipo === 'evento' && datos.message) {
            aviso(datos.message, datos.severity === 'critical' ? 'mal' : '');
          }
        } catch (e) { /* ignora payloads raros */ }
        programarRefresco();
      });
    });
  }

  // ---------------------------------------------------------------- arranque
  function reloj() {
    const ahora = new Date();
    $('reloj').textContent = ahora.toLocaleTimeString('es-PA', { hour12: false });
  }

  function enlazar() {
    document.querySelectorAll('[data-comando]').forEach((boton) => {
      boton.addEventListener('click', async () => {
        const cmd = boton.dataset.comando;
        if (cmd === 'unlock') {
          const pin = await pedirPin();
          if (!pin) return;
          enviarComando('unlock', { pin: pin }, boton);
          return;
        }
        enviarComando(cmd, {}, boton);
      });
    });

    document.querySelectorAll('.selector button').forEach((boton) => {
      boton.addEventListener('click', async () => {
        document.querySelectorAll('.selector button').forEach((b) => b.classList.remove('activo'));
        boton.classList.add('activo');
        estado.horas = Number(boton.dataset.horas);
        const lecturas = await pedir('/api/lecturas?horas=' + estado.horas + '&limite=600');
        estado.series = lecturas.series || [];
        dibujarGrafica(estado.series);
      });
    });

    window.addEventListener('resize', () => dibujarGrafica(estado.series));
  }

  async function iniciar() {
    enlazar();
    reloj();
    setInterval(reloj, 1000);
    await refrescarTodo();

    // Modo estatico (?estatico=1): sin SSE ni refresco periodico. Se usa para
    // capturar la pantalla con un navegador headless sin que la conexion
    // abierta impida que el navegador termine.
    if (new URLSearchParams(window.location.search).get('estatico') === '1') {
      const pildoraSse = $('pildora-sse');
      pildoraSse.classList.add('ok');
      pildoraSse.querySelector('b').textContent = 'CAPTURA';
      return;
    }

    conectarSSE();
    setInterval(() => {
      if (!estado.sse || estado.sse.readyState !== 1) programarRefresco();
    }, 20000);
  }

  document.addEventListener('DOMContentLoaded', iniciar);
})();
