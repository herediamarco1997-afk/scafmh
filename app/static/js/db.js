const DB_NAME = 'scafmh_inventario';
const DB_VERSION = 2;
const STORE_RESULTADOS = 'resultados';
const STORE_OFICINAS = 'oficinas';
const STORE_RESPONSABLES = 'responsables';

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = e => {
      const db = e.target.result;

      if (!db.objectStoreNames.contains(STORE_RESULTADOS)) {
        const store = db.createObjectStore(STORE_RESULTADOS, { keyPath: 'id', autoIncrement: true });
        store.createIndex('codigo', 'codigo', { unique: false });
        store.createIndex('sincronizado', 'sincronizado', { unique: false });
      }

      if (!db.objectStoreNames.contains(STORE_OFICINAS)) {
        const s = db.createObjectStore(STORE_OFICINAS, { keyPath: 'id' });
        s.createIndex('nombre', 'nombre', { unique: false });
      }

      if (!db.objectStoreNames.contains(STORE_RESPONSABLES)) {
        const s = db.createObjectStore(STORE_RESPONSABLES, { keyPath: 'id' });
        s.createIndex('oficina_id', 'oficina_id', { unique: false });
        s.createIndex('nombre', 'nombre', { unique: false });
      }
    };
    req.onsuccess = e => resolve(e.target.result);
    req.onerror = e => reject(e.target.error);
  });
}

// ─── Resultados ─────────────────────────────────────────────────────────

export async function guardarResultado(resultado) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_RESULTADOS, 'readwrite');
    tx.objectStore(STORE_RESULTADOS).add({
      ...resultado,
      sincronizado: false,
      fecha_toma: new Date().toISOString(),
      dispositivo: navigator.userAgent,
    });
    tx.oncomplete = () => resolve();
    tx.onerror = e => reject(e.target.error);
  });
}

export async function getPendientes() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_RESULTADOS, 'readonly');
    const store = tx.objectStore(STORE_RESULTADOS);
    const index = store.index('sincronizado');
    const items = [];
    index.openCursor(IDBKeyRange.only(false)).onsuccess = e => {
      const cursor = e.target.result;
      if (cursor) { items.push(cursor.value); cursor.continue(); }
      else resolve(items);
    };
    tx.onerror = e => reject(e.target.error);
  });
}

export async function marcarSincronizado(id) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_RESULTADOS, 'readwrite');
    const store = tx.objectStore(STORE_RESULTADOS);
    const req = store.get(id);
    req.onsuccess = () => {
      const item = req.result;
      if (item) {
        item.sincronizado = true;
        store.put(item);
      }
    };
    tx.oncomplete = () => resolve();
    tx.onerror = e => reject(e.target.error);
  });
}

export async function getConteoPendientes() {
  const items = await getPendientes();
  return items.length;
}

// ─── Oficinas (caché offline) ───────────────────────────────────────────

export async function cachearOficinas(oficinas) {
  const db = await openDB();
  const tx = db.transaction(STORE_OFICINAS, 'readwrite');
  const store = tx.objectStore(STORE_OFICINAS);
  store.clear();
  for (const o of oficinas) store.put(o);
  return new Promise(resolve => { tx.oncomplete = () => resolve(); });
}

export async function getOficinas() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_OFICINAS, 'readonly');
    const items = [];
    tx.objectStore(STORE_OFICINAS).openCursor().onsuccess = e => {
      const cursor = e.target.result;
      if (cursor) { items.push(cursor.value); cursor.continue(); }
      else resolve(items);
    };
    tx.onerror = e => reject(e.target.error);
  });
}

// ─── Responsables (caché offline) ────────────────────────────────────────

export async function cachearResponsables(responsables) {
  const db = await openDB();
  const tx = db.transaction(STORE_RESPONSABLES, 'readwrite');
  const store = tx.objectStore(STORE_RESPONSABLES);
  store.clear();
  for (const r of responsables) store.put(r);
  return new Promise(resolve => { tx.oncomplete = () => resolve(); });
}

export async function getResponsables(oficinaId) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_RESPONSABLES, 'readonly');
    const store = tx.objectStore(STORE_RESPONSABLES);
    if (oficinaId) {
      const index = store.index('oficina_id');
      const items = [];
      index.openCursor(IDBKeyRange.only(oficinaId)).onsuccess = e => {
        const cursor = e.target.result;
        if (cursor) { items.push(cursor.value); cursor.continue(); }
        else resolve(items);
      };
    } else {
      const items = [];
      store.openCursor().onsuccess = e => {
        const cursor = e.target.result;
        if (cursor) { items.push(cursor.value); cursor.continue(); }
        else resolve(items);
      };
    }
    tx.onerror = e => reject(e.target.error);
  });
}
