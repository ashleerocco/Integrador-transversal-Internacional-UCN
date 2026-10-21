import streamlit as st
import pandas as pd
from datetime import date
from utils.supabase_client import get_client
from utils.datos import inscripciones_etiquetadas, nombre_completo, etiqueta_curso

sb = get_client()
st.title("Certificados")  # RF-09
st.caption("Flujo: cumple requisitos → solicitado → (llega firmado) → subir PDF → el estudiante lo descarga.")

opciones = inscripciones_etiquetadas(sb)
if not opciones:
    st.info("No hay inscripciones registradas.")
    st.stop()

sel = st.selectbox("Inscripción", list(opciones))
insc_id = opciones[sel]

actual = sb.table("certificado").select("*").eq("inscripcion_id", insc_id).execute().data
estado_actual = actual[0]["estado"] if actual else "sin registro"
st.write(f"Estado actual: **{estado_actual}**")

c1, c2 = st.columns(2)
try:
    if c1.button("Marcar que cumple requisitos"):
        sb.table("certificado").upsert(
            {"inscripcion_id": insc_id, "cumple_requisitos": True},
            on_conflict="inscripcion_id",
        ).execute()
        st.success("Marcado como cumple requisitos.")
    if c2.button("Marcar como solicitado"):
        sb.table("certificado").upsert({
            "inscripcion_id": insc_id, "cumple_requisitos": True,
            "estado": "solicitado", "fecha_solicitud": date.today().isoformat(),
        }, on_conflict="inscripcion_id").execute()
        st.success("Marcado como solicitado.")
except Exception as e:
    st.error(f"No se pudo actualizar: {e}")

st.divider()
st.subheader("Adjuntar certificado firmado")
archivo = st.file_uploader("Archivo PDF", type=["pdf"])
if archivo and st.button("Guardar y entregar al estudiante"):
    ruta = f"{insc_id}.pdf"
    try:
        sb.storage.from_("certificados").upload(
            ruta, archivo.getvalue(),
            {"content-type": "application/pdf", "upsert": "true"},
        )
        sb.table("certificado").upsert({
            "inscripcion_id": insc_id, "cumple_requisitos": True,
            "estado": "entregado", "archivo_path": ruta,
            "fecha_entrega": date.today().isoformat(),
        }, on_conflict="inscripcion_id").execute()
        st.success("Certificado cargado. El estudiante ya puede verlo y descargarlo.")
    except Exception as e:
        st.error(f"No se pudo subir el archivo: {e}")

st.divider()
st.subheader("Todos los certificados")
certs = sb.table("certificado").select(
    "cumple_requisitos, estado, fecha_solicitud, fecha_entrega, "
    "inscripcion(estudiante(nombres, apellido_paterno), oferta_curso(periodo, curso(nombre)))"
).execute().data
if certs:
    df = pd.DataFrame([{
        "Estudiante": nombre_completo(c["inscripcion"]["estudiante"]),
        "Curso": etiqueta_curso(c["inscripcion"]["oferta_curso"]),
        "Cumple requisitos": c["cumple_requisitos"],
        "Estado": c["estado"],
        "Solicitado": c["fecha_solicitud"],
        "Entregado": c["fecha_entrega"],
    } for c in certs])
    filtro = st.multiselect("Filtrar por estado", ["pendiente", "solicitado", "firmado", "entregado"])
    if filtro:
        df = df[df["Estado"].isin(filtro)]
    st.dataframe(df, hide_index=True, use_container_width=True)
else:
    st.info("Aún no hay certificados registrados.")
