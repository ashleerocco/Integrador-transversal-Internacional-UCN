"""Archivos en Google Drive (carpeta raíz "A+S Idiomas").

- Se usa una cuenta de servicio (st.secrets["gcp_service_account"]) con la
  carpeta raíz compartida con ella (st.secrets["DRIVE_CARPETA_RAIZ_ID"]).
- Los archivos NO se comparten con "cualquiera con el enlace": heredan el
  acceso de la carpeta (solo cuentas autorizadas de la unidad).
- En la BD solo se guarda drive_file_id y drive_url, nunca el binario.
- Si Drive falla, el archivo se deja en una cola local ("pendiente de subir")
  y la solicitud se guarda igual; `reintentar_pendientes` lo vuelve a intentar.

Estructura:
  A+S Idiomas/Documentos estudiantes/{RUT}/
  A+S Idiomas/Pagos/{periodo}/
  A+S Idiomas/Certificados/{curso}/
"""
from __future__ import annotations

import io
import json
import os
import time
import uuid
from datetime import date
from pathlib import Path

import streamlit as st

from utils.datos import log

SCOPES = ["https://www.googleapis.com/auth/drive"]
MIME = {"pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}
CARPETA_DOCS = "Documentos estudiantes"
CARPETA_PAGOS = "Pagos"
CARPETA_CERTIFICADOS = "Certificados"


def _cola() -> Path:
    ruta = Path(os.environ.get("PENDIENTES_DIR") or st.secrets.get("PENDIENTES_DIR", ".pendientes_drive"))
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def configurado() -> bool:
    try:
        return bool(st.secrets.get("gcp_service_account")) and bool(st.secrets.get("DRIVE_CARPETA_RAIZ_ID"))
    except Exception:
        return False


@st.cache_resource(show_spinner=False)
def _servicio():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    cred = service_account.Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=SCOPES)
    return build("drive", "v3", credentials=cred, cache_discovery=False)


@st.cache_resource(show_spinner=False)
def _cache_carpetas() -> dict:
    return {}


def nombre_archivo(rut: str, tipo: str, ext: str) -> str:
    return f"{rut}_{tipo}_{date.today():%Y%m%d}.{ext}"


def _carpeta(nombre: str, padre: str) -> str:
    cache = _cache_carpetas()
    clave = f"{padre}/{nombre}"
    if clave in cache:
        return cache[clave]
    srv = _servicio()
    seguro = nombre.replace("\\", "\\\\").replace("'", "\\'")
    q = (f"name = '{seguro}' and '{padre}' in parents and "
         "mimeType = 'application/vnd.google-apps.folder' and trashed = false")
    res = srv.files().list(q=q, fields="files(id)", supportsAllDrives=True,
                           includeItemsFromAllDrives=True).execute()
    if res.get("files"):
        cache[clave] = res["files"][0]["id"]
    else:
        meta = {"name": nombre, "mimeType": "application/vnd.google-apps.folder", "parents": [padre]}
        cache[clave] = srv.files().create(body=meta, fields="id", supportsAllDrives=True).execute()["id"]
    return cache[clave]


def asegurar_ruta(partes: list[str]) -> str:
    """Crea (si no existen) las carpetas bajo la raíz y devuelve el id de la última."""
    padre = st.secrets["DRIVE_CARPETA_RAIZ_ID"]
    for p in partes:
        padre = _carpeta(p, padre)
    return padre


def subir(contenido: bytes, nombre: str, ext: str, ruta: list[str], intentos: int = 3) -> dict:
    """Sube a Drive con reintentos. Devuelve {drive_file_id, drive_url}. Lanza excepción si falla."""
    from googleapiclient.http import MediaIoBaseUpload

    ultimo = None
    for i in range(intentos):
        try:
            carpeta = asegurar_ruta(ruta)
            media = MediaIoBaseUpload(io.BytesIO(contenido), mimetype=MIME.get(ext, "application/octet-stream"),
                                      resumable=False)
            f = _servicio().files().create(body={"name": nombre, "parents": [carpeta]}, media_body=media,
                                           fields="id, webViewLink", supportsAllDrives=True).execute()
            return {"drive_file_id": f["id"], "drive_url": f["webViewLink"]}
        except Exception as e:  # red, cuota, permisos
            ultimo = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"Drive no disponible ({type(ultimo).__name__})")


def subir_o_encolar(contenido: bytes, nombre: str, ext: str, ruta: list[str], destino: dict) -> dict:
    """Intenta subir; si no se puede, deja el archivo en la cola local.

    `destino` describe dónde anotar el resultado cuando se suba más tarde, p. ej.
    {"tabla": "solicitud", "clave": {"codigo": "SOL-..."}, "prefijo": "cedula"}.
    Devuelve los campos a guardar en la BD (id/url o estado pendiente).
    """
    if configurado():
        try:
            return {**subir(contenido, nombre, ext, ruta), "estado": "subido"}
        except Exception as e:
            log.warning("Subida a Drive en cola: %s", type(e).__name__)
    else:
        log.warning("Drive no configurado: archivo en cola local")
    ticket = uuid.uuid4().hex
    cola = _cola()
    (cola / f"{ticket}.bin").write_bytes(contenido)
    (cola / f"{ticket}.json").write_text(json.dumps(
        {"nombre": nombre, "ext": ext, "ruta": ruta, "destino": destino}, ensure_ascii=False))
    return {"drive_file_id": None, "drive_url": None, "estado": "pendiente_subir"}


def pendientes() -> int:
    try:
        return len(list(_cola().glob("*.json")))
    except Exception:
        return 0


def reintentar_pendientes(sb) -> tuple[int, int]:
    """Sube lo que quedó en cola y actualiza la fila de destino. Devuelve (ok, fallidos)."""
    ok = fallidos = 0
    if not configurado():
        return 0, pendientes()
    for meta_path in sorted(_cola().glob("*.json")):
        meta = json.loads(meta_path.read_text())
        binario = meta_path.with_suffix(".bin")
        try:
            res = subir(binario.read_bytes(), meta["nombre"], meta["ext"], meta["ruta"])
            _anotar(sb, meta["destino"], res)
            meta_path.unlink()
            binario.unlink(missing_ok=True)
            ok += 1
        except Exception as e:
            log.warning("Reintento de subida fallido: %s", type(e).__name__)
            fallidos += 1
    return ok, fallidos


def _anotar(sb, destino: dict, res: dict):
    tabla, clave, pref = destino["tabla"], destino["clave"], destino.get("prefijo")
    if tabla == "solicitud":
        cambios = {f"{pref}_drive_file_id": res["drive_file_id"], f"{pref}_drive_url": res["drive_url"],
                   f"{pref}_estado": "subido"}
        q = sb.table("solicitud").update(cambios)
        for k, v in clave.items():
            q = q.eq(k, v)
        q.execute()
        # si la solicitud ya fue aceptada, también se actualiza el documento del estudiante
        sol = sb.table("solicitud").select("rut, estado").eq("codigo", clave.get("codigo", "")).execute().data
        if sol and sol[0]["estado"] == "aceptada":
            sb.table("documento_estudiante").upsert({
                "rut_estudiante": sol[0]["rut"], "tipo": pref, "drive_file_id": res["drive_file_id"],
                "drive_url": res["drive_url"], "estado_archivo": "subido"}).execute()
    elif tabla == "documento_estudiante":
        sb.table("documento_estudiante").upsert({**clave, "drive_file_id": res["drive_file_id"],
                                                 "drive_url": res["drive_url"], "estado_archivo": "subido"}).execute()
    elif tabla == "pago":
        sb.table("pago").update({"comprobante_drive_file_id": res["drive_file_id"],
                                 "comprobante_drive_url": res["drive_url"],
                                 "comprobante_estado": "subido"}).eq("id", clave["id"]).execute()


def descargar(file_id: str) -> bytes:
    """Descarga con la cuenta de servicio (el enlace no es público)."""
    from googleapiclient.http import MediaIoBaseDownload

    buf = io.BytesIO()
    req = _servicio().files().get_media(fileId=file_id, supportsAllDrives=True)
    bajada = MediaIoBaseDownload(buf, req)
    listo = False
    while not listo:
        _, listo = bajada.next_chunk()
    return buf.getvalue()


def eliminar(file_ids: list[str]):
    """Borra archivos recién subidos cuando la BD rechaza el registro (evita huérfanos)."""
    for fid in file_ids or []:
        try:
            _servicio().files().delete(fileId=fid, supportsAllDrives=True).execute()
        except Exception as e:
            log.warning("No se pudo eliminar archivo huérfano: %s", type(e).__name__)
