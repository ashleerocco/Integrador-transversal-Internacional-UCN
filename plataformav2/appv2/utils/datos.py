"""Ayudas de datos (adaptado de v1: `nombre_completo` se recicla tal cual)."""
import logging
import re

import pandas as pd
import streamlit as st

DIAS = {1: "lunes", 2: "martes", 3: "miércoles", 4: "jueves", 5: "viernes", 6: "sábado", 7: "domingo"}

# ---------------------------------------------------------------------------
# Logging sin datos personales: se borran RUT, correos y enlaces de Drive
# ---------------------------------------------------------------------------
_PATRONES_SENSIBLES = [
    re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-?[\dkK]\b"),          # RUT
    re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+"),                       # correo
    re.compile(r"https://(drive|docs)\.google\.com/\S+"),          # enlaces de Drive
]


class FiltroDatosPersonales(logging.Filter):
    def filter(self, record):
        msg = str(record.getMessage())
        for p in _PATRONES_SENSIBLES:
            msg = p.sub("[oculto]", msg)
        record.msg, record.args = msg, ()
        return True


log = logging.getLogger("idiomas")
if not log.filters:
    log.addFilter(FiltroDatosPersonales())


# ---------------------------------------------------------------------------
def nombre_completo(e: dict) -> str:
    partes = [e.get("nombres"), e.get("apellido_paterno"), e.get("apellido_materno")]
    return " ".join(p for p in partes if p)


def clp(n) -> str:
    try:
        return f"${float(n):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def horario(o: dict) -> str:
    """'lunes y miércoles 19:45 - 21:15' a partir de los datos de la oferta."""
    if o.get("horario_texto"):
        return o["horario_texto"]
    dias = [DIAS[d] for d in (o.get("dias") or []) if d in DIAS]
    txt = " y ".join([", ".join(dias[:-1]), dias[-1]]) if len(dias) > 1 else "".join(dias)
    if o.get("hora_inicio") and o.get("hora_fin"):
        txt += f" {str(o['hora_inicio'])[:5]} - {str(o['hora_fin'])[:5]}"
    return txt.strip() or "horario por confirmar"


def leer_todo(consulta, tamano: int = 1000) -> list[dict]:
    """Lee todas las filas paginando (PostgREST limita a 1000 por defecto)."""
    filas, desde = [], 0
    while True:
        lote = consulta.range(desde, desde + tamano - 1).execute().data
        filas.extend(lote)
        if len(lote) < tamano:
            return filas
        desde += tamano


def tabla(sb, nombre: str, columnas: str = "*", orden: str | None = None, desc: bool = False, **filtros) -> pd.DataFrame:
    q = sb.table(nombre).select(columnas)
    for col, val in filtros.items():
        q = q.in_(col, val) if isinstance(val, (list, tuple)) else q.eq(col, val)
    if orden:
        q = q.order(orden, desc=desc)
    return pd.DataFrame(leer_todo(q))


def ofertas_opciones(sb, solo_activas: bool = False) -> dict[str, int]:
    """{'Inglés Básico A1 · Antofagasta (1-2026)': oferta_id} según lo que el RLS deja ver."""
    q = sb.table("v_oferta").select("oferta_id, etiqueta, estado, estado_convocatoria").order("oferta_id", desc=True)
    data = q.execute().data
    if solo_activas:
        data = [o for o in data if o["estado"] in ("abierta", "confirmada")]
    return {o["etiqueta"]: o["oferta_id"] for o in data}


def invalidar_cache():
    for k in [k for k in st.session_state if k.startswith("cache_")]:
        del st.session_state[k]
