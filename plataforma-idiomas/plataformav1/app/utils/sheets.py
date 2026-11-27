"""Espejo de solo lectura Supabase -> Google Sheets ("A+S Idiomas – Base de datos").

Supabase es la fuente de verdad. Cada pestaña se reescribe completa desde su
vista, así la hoja nunca "pelea" con la BD. Tras cada escritura se sincroniza en
un hilo aparte (no bloquea al usuario). Cada intento queda en `sync_log`
(solo nombre de la pestaña, filas y tipo de error: nunca datos personales).
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from utils.datos import leer_todo, log
from utils.excel import etiqueta

# pestaña -> (vista o tabla, columnas, orden)
ESPEJO = {
    "solicitudes": ("v_solicitud", "codigo, estado, creado_en, rut, tipo_documento, nombre_completo, correo, telefono, "
                    "idioma_nombre, modalidad, curso, otro_idioma_nivel, vinculo_nombre, campus_nombre, carrera, "
                    "nacionalidad, forma_pago_nombre, cedula_drive_url, licencia_drive_url, cedula_estado, "
                    "licencia_estado, motivo_rechazo, revisado_en", "creado_en"),
    "estudiantes": ("v_estudiante", "rut, tipo_documento, nombre_completo, nombre_social, pronombres, correo, telefono, "
                    "sexo, genero, fecha_nacimiento, edad, nacionalidad, carrera, campus_nombre, vinculo_nombre, "
                    "vinculo_detalle_nombre, salud_tiene_condicion, salud_requerimiento, cursos, cedula_url, "
                    "licencia_url, origen, creado_en", "creado_en"),
    "estudiantes_pagados": ("v_estudiante_pagado", "rut, nombre_completo, curso, idioma, vinculo_nombre, genero, "
                            "campus_nombre, monto_total, monto_pagado, saldo, estado_pago, fecha_primer_pago", "curso"),
    "convocatorias_ofertas": ("v_inscritos_vs_minimo", "oferta_id, convocatoria, periodo, estado_convocatoria, curso, "
                              "idioma, modalidad, sede, estado_oferta, cupo_minimo, cupo_maximo, inscritos, "
                              "solicitudes_pendientes, pagados, faltan, alcanza_minimo", "oferta_id"),
    "pagos": ("v_pago", "id, n, nombre, banco, rut, fecha, monto, n_transaccion, n_boleta, forma_pago_nombre, n_cuota, "
              "curso, idioma_nombre, codigo_proyecto, mes, estado, motivo_anulacion, comprobante_drive_url", "fecha"),
    "asistencia": ("asistencia", "rut_estudiante, oferta_id, fecha, estado", "fecha"),
    "notas": ("v_nota", "rut_estudiante, oferta_id, curso, nota1, nota2, nota3, nota_final", "oferta_id"),
    "certificados": ("certificado", "rut_estudiante, nombre_completo, curso, estado, fecha_solicitada, fecha_firma, "
                     "fecha_entrega, drive_url, observacion", "fecha_solicitada"),
    "docentes": ("docente", "rut, nombres, apellidos, correo, telefono, activo", "apellidos"),
}


def configurado() -> bool:
    try:
        return bool(st.secrets.get("gcp_service_account")) and bool(st.secrets.get("SHEETS_ID"))
    except Exception:
        return False


def leer(sb, pestana: str) -> pd.DataFrame:
    vista, cols, orden = ESPEJO[pestana]
    return pd.DataFrame(leer_todo(sb.table(vista).select(cols).order(orden)))


def _valores(df: pd.DataFrame) -> list[list]:
    filas = [[etiqueta(c) for c in df.columns]]
    for fila in df.itertuples(index=False):
        filas.append(["" if v is None or (isinstance(v, float) and pd.isna(v))
                      else (", ".join(map(str, v)) if isinstance(v, list) else v) for v in fila])
    return filas


def _sincronizar(sb, pestanas: list[str], cred: dict, hoja_id: str) -> dict[str, str]:
    import gspread

    resultado = {}
    try:
        libro = gspread.service_account_from_dict(cred).open_by_key(hoja_id)
        existentes = {w.title: w for w in libro.worksheets()}
    except Exception as e:
        for p in pestanas:
            _registrar(sb, p, "error", None, type(e).__name__)
        return {p: "error" for p in pestanas}
    for p in pestanas:
        try:
            df = leer(sb, p)
            ws = existentes.get(p) or libro.add_worksheet(title=p, rows=max(len(df) + 10, 100), cols=max(len(df.columns), 5))
            ws.clear()
            ws.update(_valores(df), value_input_option="RAW")
            _registrar(sb, p, "ok", len(df))
            resultado[p] = "ok"
        except Exception as e:
            _registrar(sb, p, "error", None, type(e).__name__)
            resultado[p] = "error"
    return resultado


def _registrar(sb, pestana: str, estado: str, filas: int | None, detalle: str | None = None):
    try:
        sb.table("sync_log").insert({"tabla": pestana, "estado": estado, "filas": filas, "detalle": detalle},
                                    returning="minimal").execute()
        if estado == "ok":  # un éxito resuelve los errores previos de esa pestaña
            (sb.table("sync_log").update({"estado": "reintentado", "resuelto_en": datetime.now(timezone.utc).isoformat()})
             .eq("tabla", pestana).eq("estado", "error").is_("resuelto_en", "null").execute())
    except Exception as e:
        log.warning("No se pudo escribir sync_log: %s", type(e).__name__)


def sincronizar_ahora(sb, pestanas: list[str] | None = None) -> dict[str, str]:
    """Sincronización visible (botón "Sincronizar ahora")."""
    if not configurado():
        return {}
    return _sincronizar(sb, pestanas or list(ESPEJO), dict(st.secrets["gcp_service_account"]), st.secrets["SHEETS_ID"])


def tras_escritura(sb, pestanas: list[str]):
    """Se llama después de cada escritura: sincroniza en segundo plano y no bloquea."""
    if not configurado():
        return
    cred, hoja = dict(st.secrets["gcp_service_account"]), st.secrets["SHEETS_ID"]
    threading.Thread(target=_sincronizar, args=(sb, list(pestanas), cred, hoja), daemon=True).start()


def pestanas_con_error(sb) -> list[str]:
    try:
        data = sb.table("sync_log").select("tabla").eq("estado", "error").is_("resuelto_en", "null").execute().data
        return sorted({d["tabla"] for d in data})
    except Exception:
        return []
