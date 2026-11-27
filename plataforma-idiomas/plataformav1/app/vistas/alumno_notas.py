"""Mis notas y asistencia (v1 + asistencia). RLS: solo llegan las filas del RUT del alumno."""
import pandas as pd
import streamlit as st

from utils.datos import tabla
from utils.estilos import encabezado
from utils.supabase_client import exigir_rol, get_client

exigir_rol("alumno")
sb = get_client()
encabezado("Mis notas y asistencia")

insc = tabla(sb, "inscripcion", "oferta_id, estado")
if insc.empty:
    st.info("Aún no tienes cursos inscritos.")
    st.stop()

ofertas = {o["oferta_id"]: o for o in sb.table("v_oferta").select("oferta_id, etiqueta, docente")
           .in_("oferta_id", insc["oferta_id"].tolist()).execute().data}
notas = {n["oferta_id"]: n for n in tabla(sb, "nota").to_dict("records")}
asis = {a["oferta_id"]: a for a in tabla(sb, "v_asistencia_resumen").to_dict("records")}

for i in insc.to_dict("records"):
    o = ofertas.get(i["oferta_id"], {})
    st.subheader(o.get("etiqueta", "Curso"))
    st.caption(f"Estado: {i['estado']}" + (f" · Docente: {o['docente']}" if o.get("docente") else ""))
    n = notas.get(i["oferta_id"])
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, k in zip((c1, c2, c3), (1, 2, 3)):
        v = (n or {}).get(f"nota{k}")
        col.metric(f"Nota {k}", f"{v:.1f}".replace(".", ",") if v is not None else "—")
    nf = (n or {}).get("nota_final")
    c4.metric("Nota final", f"{nf:.1f}".replace(".", ",") if nf is not None else "—")
    a = asis.get(i["oferta_id"])
    c5.metric("Asistencia", f"{a['porcentaje']}%" if a and a.get("porcentaje") is not None else "—")
    if not a:
        st.caption("La asistencia y las notas aparecen cuando tu pago esté registrado.")
    else:
        det = tabla(sb, "asistencia", "fecha, estado", oferta_id=i["oferta_id"], orden="fecha")
        if not det.empty:
            with st.expander("Detalle de asistencia"):
                det["fecha"] = pd.to_datetime(det["fecha"]).dt.strftime("%d/%m/%Y")
                det["estado"] = det["estado"].map({"P": "Presente", "A": "Ausente", "J": "Justificado", "S": "Suspendida"})
                st.dataframe(det.rename(columns={"fecha": "Fecha", "estado": "Estado"}), hide_index=True)
