import {
  guardarResultado, getPendientes, marcarSincronizado, getConteoPendientes,
  cachearOficinas, getOficinas, cachearResponsables, getResponsables,
  existeCodigo, getFotosPendientes, actualizarFotoUrl
} from '/static/js/db.js?v=3';

let currentDetalle = null;
let oficinasCache = [];
let responsablesCache = [];
let currentGPS = null;

// Safe Quagga helpers (avoids 'Quagga is not defined' when CDN is slow)
function quaggaDisponible() { return typeof Quagga !== 'undefined'; }

function quaggaStop() { try { if (quaggaDisponible()) Quagga.stop(); } catch(e) { /* ignore */ } }

// ─── GPS ────────────────────────────────────────────────────────────────

function capturarGPS() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve(null);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        currentGPS = {
          lat: Math.round(pos.coords.latitude * 1e7) / 1e7,
          lng: Math.round(pos.coords.longitude * 1e7) / 1e7,
        };
        resolve(currentGPS);
      },
      () => resolve(null),
      { enableHighAccuracy: true, timeout: 5000, maximumAge: 60000 }
    );
  });
}

// ─── Sincronización ────────────────────────────────────────────────────

async function subirFotosOffline(pendientes) {
  for (const p of pendientes) {
    if (!p.foto_base64) continue;
    try {
      const formData = new FormData();
      const blob = await (await fetch(p.foto_base64)).blob();
      formData.append('foto', blob, `${p.codigo}.jpg`);
      const r = await fetch('/inventario/api/foto', { method: 'POST', body: formData });
      const d = await r.json();
      if (d.url) {
        await actualizarFotoUrl(p.id, d.url);
        p.foto_url = d.url;
      }
    } catch (e) {
      console.warn('Error subiendo foto offline:', p.codigo, e);
    }
  }
}

async function sincronizar() {
  const btn = document.getElementById('btn-sync');
  if (!btn) return;
  btn.disabled = true;
  btn.textContent = 'Sincronizando...';

  const pendientes = await getPendientes();
  if (pendientes.length === 0) {
    btn.textContent = '0 pendientes';
    btn.disabled = false;
    return;
  }

  // 1. Subir fotos pendientes primero
  await subirFotosOffline(pendientes);

  // 2. Subir resultados
  try {
    const r = await fetch('/inventario/api/resultados', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(pendientes.map(p => ({
        codigo: p.codigo,
        resultado: p.resultado,
        observacion: p.observacion,
        foto_url: p.foto_url || '',
        ubicacion: '',
        responsable: p.responsable_text || '',
        nueva_oficina_id: p.nueva_oficina_id || null,
        nuevo_responsable_id: p.nuevo_responsable_id || null,
        nuevo_estado: p.nuevo_estado || null,
        lat: p.lat,
        lng: p.lng,
        fecha_toma: p.fecha_toma,
        dispositivo: p.dispositivo || '',
      }))),
    });
    const data = await r.json();
    if (data.created > 0) {
      for (const p of pendientes) {
        await marcarSincronizado(p.id);
      }
      await actualizarEstadisticas();
      btn.textContent = `${data.created} sincronizados`;
      if (data.errors && data.errors.length > 0) {
        console.warn('Errores de sync:', data.errors);
      }
    } else {
      btn.textContent = 'Error en sync';
    }
  } catch (e) {
    btn.textContent = 'Error de conexión';
    console.error(e);
  }
  btn.disabled = false;
  setTimeout(() => actualizarPendientes(), 1000);
}

async function actualizarPendientes() {
  const pendientes = await getConteoPendientes();
  const el = document.getElementById('pendientes-count');
  if (el) el.textContent = pendientes;
  const btn = document.getElementById('btn-sync');
  if (btn) btn.textContent = pendientes > 0 ? `Sincronizar (${pendientes})` : '0 pendientes';
}

async function actualizarEstadisticas() {
  try {
    const r = await fetch('/inventario/api/estadisticas');
    const d = await r.json();
    for (const [k, v] of Object.entries(d)) {
      const el = document.getElementById(`stat-${k}`);
      if (el) el.textContent = v;
    }
  } catch (e) { /* offline */ }
}

// ─── Carga de datos de referencia ───────────────────────────────────────

async function cargarReferencias() {
  try {
    const [rOficinas, rResp] = await Promise.all([
      fetch('/inventario/api/oficinas'),
      fetch('/inventario/api/responsables'),
    ]);
    const oficinas = await rOficinas.json();
    const responsables = await rResp.json();
    await Promise.all([
      cachearOficinas(oficinas),
      cachearResponsables(responsables),
    ]);
    oficinasCache = oficinas;
    responsablesCache = responsables;
  } catch (e) {
    console.warn('offline, usando caché local');
    oficinasCache = await getOficinas();
    responsablesCache = await getResponsables();
  }
  llenarSelectOficinas();
}

function llenarSelectOficinas() {
  const sel = document.getElementById('nueva-oficina');
  sel.innerHTML = '<option value="">— Sin cambio —</option>';
  for (const o of oficinasCache.sort((a, b) => a.nombre.localeCompare(b.nombre))) {
    const opt = document.createElement('option');
    opt.value = o.id;
    opt.textContent = `${o.nombre}`;
    sel.appendChild(opt);
  }
}

function llenarSelectResponsables(oficinaId, selectedId) {
  const sel = document.getElementById('nuevo-responsable');
  sel.innerHTML = '<option value="">— Sin cambio —</option>';
  let lista = responsablesCache;
  if (oficinaId) {
    lista = lista.filter(r => r.oficina_id == oficinaId);
  }
  for (const r of lista.sort((a, b) => a.nombre.localeCompare(b.nombre))) {
    const opt = document.createElement('option');
    opt.value = r.id;
    opt.textContent = `${r.nombre}${r.cargo ? ' — ' + r.cargo : ''}`;
    if (selectedId && r.id == selectedId) opt.selected = true;
    sel.appendChild(opt);
  }
}

// ─── Búsqueda de activo ─────────────────────────────────────────────────

async function buscarActivo(codigo) {
  try {
    const r = await fetch(`/inventario/api/activos/${encodeURIComponent(codigo.trim())}`, {
      credentials: 'same-origin',
    });
    const ct = r.headers.get('content-type') || '';
    if (!r.ok || !ct.includes('application/json')) {
      console.warn('buscarActivo: status=%d, type=%s', r.status, ct);
      return null;
    }
    return await r.json();
  } catch (e) {
    console.error('buscarActivo error:', e);
    return null;
  }
}

// ─── Mostrar detalle del activo ─────────────────────────────────────────

async function mostrarDetalleActivo(activo) {
  currentDetalle = activo;

  document.getElementById('detalle-codigo').textContent = activo.codigo;
  document.getElementById('detalle-descripcion').textContent = activo.descripcion;
  document.getElementById('detalle-fecha').textContent = activo.fecha_incorporacion || '-';
  document.getElementById('detalle-grupo').textContent = activo.grupo || '-';
  document.getElementById('detalle-auxiliar').textContent = activo.auxiliar || '-';
  document.getElementById('detalle-costo').textContent = `Bs. ${Number(activo.costo_inicial).toLocaleString('es-BO', {minimumFractionDigits:2})}`;
  document.getElementById('detalle-depreciacion').textContent = `Bs. ${Number(activo.depreciacion_acumulada).toLocaleString('es-BO', {minimumFractionDigits:2})}`;
  document.getElementById('detalle-vida-util').textContent = activo.vida_util + ' años';
  document.getElementById('detalle-estado-bien').textContent = activo.estado_bien || '-';
  document.getElementById('detalle-observaciones').textContent = activo.observaciones || '-';

  // Asignación actual
  document.getElementById('actual-oficina').textContent = activo.oficina || '-';
  document.getElementById('actual-responsable').textContent = activo.responsable || '-';

  // Reset selects
  var el;
  el = document.getElementById('nueva-oficina'); if (el) el.value = '';
  llenarSelectResponsables(null, null);
  el = document.getElementById('nuevo-estado'); if (el) el.value = '';
  el = document.getElementById('detalle-estado-actual'); if (el) el.textContent = activo.estado_bien || '-';

  el = document.getElementById('scanner-overlay'); if (el) el.classList.add('hidden');
  el = document.getElementById('result-panel'); if (el) el.classList.remove('hidden');

  el = document.getElementById('foto-preview'); if (el) el.classList.add('hidden');
  el = document.getElementById('foto-input'); if (el) el.value = '';
  el = document.getElementById('observacion'); if (el) el.value = '';
  el = document.getElementById('foto-url-guardado'); if (el) el.value = '';

  // Capturar GPS en background
  capturarGPS();
}

// ─── Registro de resultado ──────────────────────────────────────────────

const RESULTADOS_VALIDOS = ['VERIFICADO', 'NOVEDAD', 'NO_ENCONTRADO'];

async function registrarResultado(resultado) {
  if (!currentDetalle) return;

  // Validar resultado
  if (!RESULTADOS_VALIDOS.includes(resultado)) {
    alert('Resultado inválido: ' + resultado);
    return;
  }

  var btn = document.getElementById('btn-verificado');
  if (btn && btn.disabled) return;
  if (btn) btn.disabled = true;

  try {
    // Verificar duplicado
    const duplicado = await existeCodigo(currentDetalle.codigo);
    if (duplicado) {
      if (!confirm(`El activo ${currentDetalle.codigo} ya fue escaneado. ¿Deseas registrarlo de todas formas?`)) {
        if (btn) btn.disabled = false;
        return;
      }
    }

    var ofId = document.getElementById('nueva-oficina');
    var respId = document.getElementById('nuevo-responsable');
    var estId = document.getElementById('nuevo-estado');
    var obsEl = document.getElementById('observacion');
    var fotoEl = document.getElementById('foto-url-guardado');

    // Obtener foto como Base64 si existe (para offline)
    let fotoBase64 = null;
    let fotoUrl = fotoEl ? fotoEl.value : '';

    const preview = document.getElementById('foto-preview');
    if (preview && preview.src && !preview.classList.contains('hidden') && !fotoUrl) {
      // La foto está como preview pero no se subió (offline)
      try {
        const canvas = document.createElement('canvas');
        canvas.width = preview.naturalWidth;
        canvas.height = preview.naturalHeight;
        canvas.getContext('2d').drawImage(preview, 0, 0);
        fotoBase64 = canvas.toDataURL('image/jpeg', 0.7);
      } catch (e) { /* no se pudo convertir */ }
    }

    var registro = {
      codigo: currentDetalle.codigo,
      resultado: resultado,
      observacion: obsEl ? obsEl.value : '',
      foto_url: fotoUrl,
      foto_base64: fotoBase64,
      ubicacion: '',
      nueva_oficina_id: ofId && ofId.value ? parseInt(ofId.value) : null,
      nuevo_responsable_id: respId && respId.value ? parseInt(respId.value) : null,
      nuevo_estado: estId && estId.value ? estId.value : null,
      lat: currentGPS ? currentGPS.lat : null,
      lng: currentGPS ? currentGPS.lng : null,
      responsable_text: '',
    };

    // Intentar enviar al servidor primero
    let enviado = false;
    try {
      const r = await fetch('/inventario/api/guardar', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          codigo: registro.codigo,
          resultado: registro.resultado,
          observacion: registro.observacion,
          foto_url: registro.foto_url,
          ubicacion: registro.ubicacion,
          nueva_oficina_id: registro.nueva_oficina_id,
          nuevo_responsable_id: registro.nuevo_responsable_id,
          nuevo_estado: registro.nuevo_estado,
          lat: registro.lat,
          lng: registro.lng,
          fecha_toma: new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 19),
        }),
      });
      if (r.ok) {
        enviado = true;
        document.getElementById('ultimo-guardado').textContent = currentDetalle.codigo;
        await actualizarEstadisticas();
        mostrarConfirmacion(currentDetalle.codigo);
      }
    } catch (e) {
      // Offline — guardar en IndexedDB
    }

    if (!enviado) {
      // Guardar en IndexedDB para sincronizar después
      await guardarResultado(registro);
      await actualizarPendientes();
      document.getElementById('ultimo-guardado').textContent = currentDetalle.codigo + ' (pendiente)';
      mostrarConfirmacion(currentDetalle.codigo);
    }

  } catch (e) {
    alert('Error interno: ' + e.message);
    if (btn) btn.disabled = false;
  }
}

function mostrarConfirmacion(codigo) {
  var el;
  el = document.getElementById('acciones-registro'); if (el) el.classList.add('hidden');
  el = document.getElementById('confirmacion-guardado'); if (el) el.classList.remove('hidden');
}

window.registrarResultado = registrarResultado;

function volverAEscanear() {
  currentDetalle = null;
  currentGPS = null;
  detenerCamara();
  quaggaStop();
  var container = document.querySelector('#scanner-container');
  if (container) container.innerHTML = '';
  var el;
  el = document.getElementById('result-panel'); if (el) el.classList.add('hidden');
  el = document.getElementById('scanner-overlay'); if (el) el.classList.remove('hidden');
  el = document.getElementById('acciones-registro'); if (el) el.classList.remove('hidden');
  el = document.getElementById('confirmacion-guardado'); if (el) el.classList.add('hidden');
  var btn = document.getElementById('btn-verificado'); if (btn) btn.disabled = false;
  iniciarScanner();
}

window.volverAEscanear = volverAEscanear;

// ─── Event listeners ────────────────────────────────────────────────────

function setupSync() {
  const btn = document.getElementById('btn-sync');
  if (btn) btn.addEventListener('click', sincronizar);
  actualizarPendientes();
  actualizarEstadisticas();
}

function setupFoto() {
  const btn = document.getElementById('btn-foto');
  const input = document.getElementById('foto-input');
  if (btn && input) {
    btn.addEventListener('click', () => input.click());
    input.addEventListener('change', async e => {
      const file = e.target.files[0];
      if (!file) return;

      // Mostrar preview inmediatamente
      const preview = document.getElementById('foto-preview');
      const reader = new FileReader();
      reader.onload = () => {
        preview.src = reader.result;
        preview.classList.remove('hidden');
      };
      reader.readAsDataURL(file);

      // Intentar subir a Cloudinary
      const formData = new FormData();
      formData.append('foto', file);
      try {
        const r = await fetch('/inventario/api/foto', { method: 'POST', body: formData });
        const d = await r.json();
        if (d.url) {
          document.getElementById('foto-url-guardado').value = d.url;
        }
      } catch (e) {
        // Offline — la foto queda como preview, se sincronizará después
        console.warn('Foto no subida (offline), se guardará localmente');
      }
    });
  }
}

function setupButtons() {
  document.getElementById('btn-verificado').addEventListener('click', () => registrarResultado('VERIFICADO'));
  document.getElementById('btn-novedad').addEventListener('click', () => registrarResultado('NOVEDAD'));
  document.getElementById('btn-no-encontrado').addEventListener('click', () => registrarResultado('NO_ENCONTRADO'));
  document.getElementById('btn-cancelar').addEventListener('click', volverAEscanear);
  var setBtnResultados = function(id, fn) { var el = document.getElementById(id); if (el) el.addEventListener('click', fn); };
  setBtnResultados('btn-ver-resultados', function() { window.location.href = '/inventario/resultados'; });
  setBtnResultados('btn-volver-escanear', volverAEscanear);
}

function setupOficinaFilter() {
  const selOf = document.getElementById('nueva-oficina');
  selOf.addEventListener('change', () => {
    const ofId = selOf.value;
    llenarSelectResponsables(ofId ? parseInt(ofId) : null, null);
  });
}

// ─── Sincronización automática al recuperar conexión ────────────────────

function setupAutoSync() {
  window.addEventListener('online', async () => {
    const pendientes = await getConteoPendientes();
    if (pendientes > 0) {
      sincronizar();
    }
  });
}

// ─── Scanner ────────────────────────────────────────────────────────────

var scannerStream = null;
var scannerTimer = null;

function detenerCamara() {
  if (scannerStream) {
    scannerStream.getTracks().forEach(function(t) { t.stop(); });
    scannerStream = null;
  }
  if (scannerTimer) {
    clearTimeout(scannerTimer);
    scannerTimer = null;
  }
}

async function iniciarScanner() {
  var container = document.querySelector('#scanner-container');
  var errEl = document.getElementById('scanner-error');
  var lastReadEl = document.getElementById('ultimo-codigo');
  if (!container) return;

  // BarcodeDetector nativo de Chrome (mas preciso)
  if ('BarcodeDetector' in window) {
    try {
      var detector = new BarcodeDetector({
        formats: ['code_128', 'code_39', 'ean_13', 'ean_8', 'upc_a', 'upc_e', 'codabar', 'itf', 'qr_code', 'code_93']
      });
      var video = document.createElement('video');
      video.setAttribute('autoplay', '');
      video.setAttribute('playsinline', '');
      video.setAttribute('muted', '');
      video.style.width = '100%';
      video.style.display = 'block';
      container.innerHTML = '';
      container.appendChild(video);
      scannerStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: {ideal: 640}, height: {ideal: 480} }
      });
      video.srcObject = scannerStream;
      await video.play();
      var lastCode = '';
      errEl.textContent = 'Escaneando...';

      async function detectar() {
        if (!scannerStream) return;
        try {
          var codes = await detector.detect(video);
          for (var i = 0; i < codes.length; i++) {
            var code = codes[i].rawValue;
            if (!code || code.length < 3 || code === lastCode) continue;
            lastCode = code;
            if (lastReadEl) lastReadEl.textContent = 'Leyendo: ' + code;
            var activo = await buscarActivo(code);
            if (activo) {
              detenerCamara();
              await mostrarDetalleActivo(activo);
              return;
            } else {
              errEl.textContent = 'Leido: ' + code + ' — no registrado. Busca por c\u00f3digo de activo.';
              var manualInput = document.getElementById('codigo-manual');
              if (manualInput) { manualInput.value = code; manualInput.focus(); }
              setTimeout(function() { errEl.textContent = 'Escaneando...'; lastCode = ''; }, 5000);
            }
          }
        } catch (e) {}
        if (scannerStream) scannerTimer = setTimeout(detectar, 200);
      }
      scannerTimer = setTimeout(detectar, 500);
      return;
    } catch (e) {
      detenerCamara();
      container.innerHTML = '<div style="color:white;padding:40px;text-align:center">Error de camara</div>';
    }
  }

  // Fallback Quagga
  if (!quaggaDisponible()) {
    setTimeout(iniciarScanner, 1000);
    return;
  }
  Quagga.init({
    inputStream: {
      name: 'Live',
      type: 'LiveStream',
      target: container,
      constraints: { width: 640, height: 480, facingMode: 'environment' },
    },
    locator: { patchSize: 'large', halfSample: false },
    numOfWorkers: navigator.hardwareConcurrency || 2,
    frequency: 5,
    decoder: { readers: [
      'code_128_reader', 'code_39_reader', 'code_39_vin_reader',
      'code_93_reader', 'i2of5_reader', 'codabar_reader',
      'ean_reader', 'ean_8_reader', 'upc_reader', 'upc_e_reader',
    ]},
    locate: true,
  }, function(err) {
    if (err) { errEl.textContent = 'Error al iniciar camara: ' + err; return; }
    Quagga.start();
    errEl.textContent = '';
  });

  var lastCode = '';
  Quagga.onDetected(async function(data) {
    if (!data || !data.codeResult) return;
    var code = data.codeResult.code;
    if (!code || code.length < 3 || code === lastCode) return;
    lastCode = code;
    if (lastReadEl) lastReadEl.textContent = 'Leyendo: ' + code;
    var activo = await buscarActivo(code);
    if (activo) {
      quaggaStop();
      await mostrarDetalleActivo(activo);
    } else {
      errEl.textContent = 'Leido: ' + code + ' — no registrado. Busca por c\u00f3digo de activo.';
      var manualInput = document.getElementById('codigo-manual');
      if (manualInput) { manualInput.value = code; manualInput.focus(); }
      setTimeout(function() { errEl.textContent = ''; lastCode = ''; }, 5000);
    }
  });
}

// ─── Búsqueda manual ────────────────────────────────────────────────────

function setupManualSearch() {
  const input = document.getElementById('codigo-manual');
  const btn = document.getElementById('btn-buscar-manual');
  const error = document.getElementById('manual-error');

  function doSearch() {
    try {
      const code = input.value.trim().toUpperCase();
      if (!code) {
        error.textContent = 'Ingresa un c\u00f3digo de activo';
        error.style.display = 'block';
        return;
      }
      if (code.length < 3) {
        error.textContent = 'El c\u00f3digo debe tener al menos 3 caracteres';
        error.style.display = 'block';
        return;
      }
      error.style.display = 'none';
      btn.disabled = true;
      btn.textContent = 'Buscando...';

      buscarActivo(code).then(async activo => {
        btn.disabled = false;
        btn.textContent = 'Buscar';
        if (activo) {
          detenerCamara();
          quaggaStop();
          await mostrarDetalleActivo(activo);
          input.value = '';
        } else {
          error.textContent = 'No se encontr\u00f3 activo con c\u00f3digo "' + code + '".';
          error.style.display = 'block';
        }
      }).catch(err => {
        btn.disabled = false;
        btn.textContent = 'Buscar';
        error.textContent = 'Error: ' + (err && err.message ? err.message : 'desconocido');
        error.style.display = 'block';
        console.error('doSearch.catch:', err);
      });
    } catch (err) {
      btn.disabled = false;
      btn.textContent = 'Buscar';
      error.textContent = 'Error interno: ' + (err && err.message ? err.message : 'desconocido');
      error.style.display = 'block';
      console.error('doSearch.error:', err);
    }
  }

  btn.addEventListener('click', doSearch);
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') doSearch();
  });
}


// ─── Init ───────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  setupSync();
  setupFoto();
  setupButtons();
  setupOficinaFilter();
  setupManualSearch();
  setupAutoSync();
  cargarReferencias();
  iniciarScanner();
  capturarGPS();
});
