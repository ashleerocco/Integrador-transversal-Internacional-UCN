/**
 * Puente entre la plataforma de idiomas (Streamlit) y la carpeta "A+S Idiomas" de Drive.
 *
 * Lo instala UNA VEZ la cuenta del socio comunitario (la que administra la carpeta):
 *   1. script.google.com → Nuevo proyecto → pegar este archivo completo.
 *   2. Completar CARPETA_RAIZ_ID y TOKEN (abajo).
 *   3. Ejecutar la función "probar" (botón ▶) y aceptar los permisos de Drive.
 *   4. Implementar → Nueva implementación → tipo "Aplicación web"
 *        Ejecutar como: Yo   ·   Quién tiene acceso: Cualquier usuario
 *   5. Copiar la URL que termina en /exec y entregarla, junto al TOKEN, a quien administre la app.
 *
 * Los archivos quedan a nombre de esta cuenta, dentro de A+S Idiomas, y heredan sus permisos.
 * El script solo puede leer o borrar archivos que estén dentro de A+S Idiomas.
 */

// ID de la carpeta A+S Idiomas: la parte final de su URL (drive.google.com/drive/folders/ESTE_ID)
const CARPETA_RAIZ_ID = 'PEGAR_AQUI_EL_ID_DE_LA_CARPETA';
// Clave secreta larga (inventar 30+ caracteres al azar). La app debe tener la misma.
const TOKEN = 'PEGAR_AQUI_UNA_CLAVE_LARGA_Y_SECRETA';

function doPost(e) {
  try {
    const p = JSON.parse(e.postData.contents);
    if (TOKEN.indexOf('PEGAR_AQUI') === 0 || p.token !== TOKEN) return responder({ ok: false, error: 'no autorizado' });
    switch (p.accion) {
      case 'subir': return responder(subir(p));
      case 'descargar': return responder(descargar(p.id));
      case 'eliminar': return responder(eliminar(p.id));
      case 'probar': return responder(probar());
      default: return responder({ ok: false, error: 'acción desconocida' });
    }
  } catch (err) {
    return responder({ ok: false, error: String(err) });
  }
}

function responder(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

/** Devuelve (creando si falta) la subcarpeta ruta[0]/ruta[1]/... bajo A+S Idiomas. */
function carpeta(ruta) {
  const lock = LockService.getScriptLock();
  lock.waitLock(30000); // evita carpetas duplicadas si llegan dos subidas a la vez
  try {
    let actual = DriveApp.getFolderById(CARPETA_RAIZ_ID);
    (ruta || []).forEach(function (nombre) {
      const it = actual.getFoldersByName(String(nombre));
      actual = it.hasNext() ? it.next() : actual.createFolder(String(nombre));
    });
    return actual;
  } finally {
    lock.releaseLock();
  }
}

function subir(p) {
  const blob = Utilities.newBlob(Utilities.base64Decode(p.contenido), p.mime || 'application/octet-stream', p.nombre);
  const f = carpeta(p.ruta).createFile(blob);
  return { ok: true, id: f.getId(), url: f.getUrl() };
}

/** true si el archivo está (a cualquier profundidad) dentro de A+S Idiomas. */
function dentroDeRaiz(archivo) {
  let pendientes = [];
  const it = archivo.getParents();
  while (it.hasNext()) pendientes.push(it.next());
  for (let nivel = 0; nivel < 10 && pendientes.length; nivel++) {
    const siguientes = [];
    for (const c of pendientes) {
      if (c.getId() === CARPETA_RAIZ_ID) return true;
      const padres = c.getParents();
      while (padres.hasNext()) siguientes.push(padres.next());
    }
    pendientes = siguientes;
  }
  return false;
}

function archivoPermitido(id) {
  const f = DriveApp.getFileById(id);
  if (!dentroDeRaiz(f)) throw new Error('archivo fuera de A+S Idiomas');
  return f;
}

function descargar(id) {
  const f = archivoPermitido(id);
  return { ok: true, nombre: f.getName(), contenido: Utilities.base64Encode(f.getBlob().getBytes()) };
}

function eliminar(id) {
  archivoPermitido(id).setTrashed(true);
  return { ok: true };
}

/** Ejecutar desde el editor para autorizar y comprobar el acceso a la carpeta. */
function probar() {
  const nombre = DriveApp.getFolderById(CARPETA_RAIZ_ID).getName();
  Logger.log('Acceso correcto a la carpeta: ' + nombre);
  return { ok: true, carpeta: nombre };
}
