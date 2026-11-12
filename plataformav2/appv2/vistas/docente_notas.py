"""Notas (pantalla de v1). Nuevo: solo alumnos pagados, una fila por alumno y
nota final calculada en la BD (columna generada: promedio de las 3 notas, 1 decimal)."""
import pandas as pd
import streamlit as st

from utils import sheets
from utils.datos import ofertas_opciones, tabla
from utils.errores import mensaje_error
from utils.estilos import encabezado
from utils.excel import boton_excel
from utils.supabase_client import exigir_rol, get_client

exigir_rol("coordinacion", "docente")
sb = get_client()
encabezado("Notas")

op = ofertas_opciones(sb)
if not op:
    st.info("No tienes cursos asignados.")
    st.stop()
oferta_id = op[st.selectbox("Curso", list(op))]

alumnos = sb.rpc("alumnos_de_oferta", {"p_oferta_id": oferta_id}).execute().data
if not alumnos:
    st.info("Este curso aún no tiene alumnos en «Estudiantes pagados».")
    st.stop()

notas = tabla(sb, "nota", oferta_id=oferta_id)
mapa = {n["rut_estudiante"]: n for n in notas.to_dict("records")} if not notas.empty else {}


def num(v):
    return None if v is None or pd.isna(v) else float(v)


df = pd.DataFrame([{
    "rut": a["rut"],
    "Estudiante": a["nombre_completo"] + (f" ({a['nombre_social']})" if a.get("nombre_social") else ""),
    "Nota 1": num(mapa.get(a["rut"], {}).get("nota1")),
    "Nota 2": num(mapa.get(a["rut"], {}).get("nota2")),
    "Nota 3": num(mapa.get(a["rut"], {}).get("nota3")),
    "Nota final": num(mapa.get(a["rut"], {}).get("nota_final")),
} for a in alumnos])

cfg = {"rut": None, "Nota final": st.column_config.NumberColumn("Nota final (automática)", format="%.1f")}
for c in ("Nota 1", "Nota 2", "Nota 3"):
    cfg[c] = st.column_config.NumberColumn(c, min_value=1.0, max_value=7.0, step=0.1, format="%.1f")

editado = st.data_editor(df, hide_index=True, width="stretch",
                         disabled=["rut", "Estudiante", "Nota final"], column_config=cfg, key=f"notas_{oferta_id}")
st.caption("Escala 1,0 a 7,0. La nota final se calcula sola cuando las 3 notas están ingresadas.")

if st.button("Guardar notas", type="primary"):
    filas, errores = [], []
    for r in editado.to_dict("records"):
        valores = {f"nota{k}": (round(float(r[f'Nota {k}']), 1) if pd.notna(r[f"Nota {k}"]) else None) for k in (1, 2, 3)}
        if any(v is not None and not 1.0 <= v <= 7.0 for v in valores.values()):
            errores.append(r["Estudiante"])
        elif any(v is not None for v in valores.values()) or r["rut"] in mapa:
            filas.append({"rut_estudiante": r["rut"], "oferta_id": oferta_id, **valores})
    if errores:
        st.error("Notas fuera de rango (1,0 a 7,0): " + ", ".join(errores))
    elif not filas:
        st.warning("No hay notas para guardar.")
    else:
        try:
            sb.table("nota").upsert(filas, on_conflict="rut_estudiante,oferta_id").execute()
            sheets.tras_escritura(sb, ["notas"])
            st.success("Notas guardadas.")
            st.rerun()
        except Exception as e:
            st.error(mensaje_error(e, "guardar las notas"))

boton_excel(df.drop(columns=["rut"]), "notas_curso", "xl_notas")
