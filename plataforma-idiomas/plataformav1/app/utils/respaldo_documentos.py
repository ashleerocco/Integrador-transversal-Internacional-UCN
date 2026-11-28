"""Respaldo de documentos: todos los archivos de Drive en un ZIP ordenado por carpetas.

Lee de la BD dónde está cada archivo (solo drive_file_id) y los descarga uno a uno con
drive.descargar_archivo, que les pone su extensión real (.pdf, .jpg, .png). Incluye
también los archivos de la cola local que aún no se suben a Drive.

Estructura del ZIP:
  Documentos estudiantes/{RUT}/            identidad y licencia (ficha del estudiante)
  Solicitudes sin aceptar/{código}_{RUT}/  documentos de solicitudes pendientes o rechazadas
  Comprobantes de pago/{RUT}/              un archivo por cuota
  Certificados/{curso}/                    PDF firmado de cada estudiante
  Pendientes de subir a Drive/             cola local (Drive no respondía al enviarlos)
"""
from __future__ import annotations

import io
import json
import re
import zipfile
from datetime import date

from utils import drive
from utils.datos import tabla

ETIQUETA = {"cedula": "documento_identidad", "licencia": "licencia_media"}


def _limpio(texto) -> str:
    """Nombre válido para carpetas/archivos en Windows."""
    return re.sub(r'[\\/:*?"<>|]+', "-", str(texto)).strip(" .") or "sin_nombre"


def _vacio(v) -> bool:
    return v is None or v != v or str(v).strip() == ""  # v != v detecta NaN


def recopilar(sb) -> list[dict]:
    """Lista [{id, carpeta, base}] de los archivos a respaldar, sin repetir el mismo archivo."""
    items, vistos = [], set()

    def agregar(fid, carpeta, base):
        if not _vacio(fid) and fid not in vistos:
            vistos.add(fid)
            items.append({"id": fid, "carpeta": carpeta, "base": base})

    docs = tabla(sb, "documento_estudiante", "rut_estudiante, tipo, drive_file_id")
    for d in docs.to_dict("records"):
        agregar(d["drive_file_id"], f"Documentos estudiantes/{_limpio(d['rut_estudiante'])}",
                f"{_limpio(d['rut_estudiante'])}_{ETIQUETA.get(d['tipo'], d['tipo'])}")

    sols = tabla(sb, "solicitud", "codigo, rut, estado, cedula_drive_file_id, licencia_drive_file_id")
    for s in sols.to_dict("records"):
        if s["estado"] == "aceptada":
            continue  # sus documentos ya están en la ficha del estudiante
        carpeta = f"Solicitudes sin aceptar/{_limpio(s['codigo'])}_{_limpio(s['rut'])}"
        for pref in ("cedula", "licencia"):
            agregar(s.get(f"{pref}_drive_file_id"), carpeta, f"{_limpio(s['rut'])}_{ETIQUETA[pref]}")

    pagos = tabla(sb, "pago", "id, rut_estudiante, n_cuota, fecha, comprobante_drive_file_id")
    for p in pagos.to_dict("records"):
        cuota = "" if _vacio(p.get("n_cuota")) else f"_cuota{int(p['n_cuota'])}"
        agregar(p["comprobante_drive_file_id"], f"Comprobantes de pago/{_limpio(p['rut_estudiante'])}",
                f"{_limpio(p['rut_estudiante'])}_comprobante{cuota}_{_limpio(p.get('fecha') or p['id'])}")

    certs = tabla(sb, "certificado", "rut_estudiante, curso, drive_file_id")
    for c in certs.to_dict("records"):
        agregar(c["drive_file_id"], f"Certificados/{_limpio(c.get('curso') or 'sin curso')}",
                f"{_limpio(c['rut_estudiante'])}_certificado")
    return items


def _pendientes_locales() -> list[tuple[str, bytes]]:
    """Archivos de la cola local (aún no subidos a Drive)."""
    salida = []
    try:
        for meta_path in sorted(drive._cola().glob("*.json")):
            meta = json.loads(meta_path.read_text())
            binario = meta_path.with_suffix(".bin")
            if binario.exists():
                salida.append((_limpio(meta.get("nombre") or meta_path.stem), binario.read_bytes()))
    except Exception:
        pass
    return salida


def generar_zip(sb, progreso=None) -> tuple[bytes, int, list[str]]:
    """Arma el ZIP. Devuelve (zip_en_bytes, archivos_incluidos, descripciones_de_fallos).

    `progreso(i, total)` se llama tras cada archivo (para una barra de avance).
    """
    items = recopilar(sb) if drive.configurado() else []
    locales = _pendientes_locales()
    total = len(items) + len(locales)
    fallidos, incluidos, usados = [], 0, set()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for i, it in enumerate(items, 1):
            try:
                a = drive.descargar_archivo(it["id"], it["base"])
                ext = a["nombre"].rpartition(".")[2] if "." in a["nombre"] else ""
                ruta = f"{it['carpeta']}/{it['base']}" + (f".{ext}" if ext else "")
                n = 2
                while ruta in usados:  # dos archivos con el mismo nombre en la misma carpeta
                    ruta = f"{it['carpeta']}/{it['base']}_{n}" + (f".{ext}" if ext else "")
                    n += 1
                usados.add(ruta)
                z.writestr(ruta, a["contenido"])
                incluidos += 1
            except Exception as e:
                fallidos.append(f"{it['carpeta']}/{it['base']} (no se pudo descargar: {type(e).__name__})")
            if progreso:
                progreso(i, total)
        for j, (nombre, contenido) in enumerate(locales, len(items) + 1):
            base, punto, ext = nombre.rpartition(".")
            ruta, n = f"Pendientes de subir a Drive/{nombre}", 2
            while ruta in usados:
                ruta = f"Pendientes de subir a Drive/{base}_{n}.{ext}" if punto else f"Pendientes de subir a Drive/{nombre}_{n}"
                n += 1
            usados.add(ruta)
            z.writestr(ruta, contenido)
            incluidos += 1
            if progreso:
                progreso(j, total)
        if fallidos:
            z.writestr("archivos_no_incluidos.txt",
                       f"Respaldo del {date.today():%d-%m-%Y}. Archivos que no se pudieron descargar de Drive:\n\n"
                       + "\n".join(fallidos))
    return buf.getvalue(), incluidos, fallidos
