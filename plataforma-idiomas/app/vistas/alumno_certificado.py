import streamlit as st
import pandas as pd
from utils.supabase_client import get_client
from utils.estilos import encabezado
from utils.exportar import boton_descarga

sb = get_client()
encabezado("Mi certificado")

# RLS solo deja pasar certificados propios con estado 'entregado' y archivo cargado
certs = sb.table("certificado").select(
    "archivo_path, fecha_entrega, inscripcion(oferta_curso(periodo, curso(nombre)))"
).execute().data

if not certs:
    st.info("Aún no tienes certificados disponibles. Cuando la coordinación lo cargue, aparecerá aquí.")
    st.stop()

df = pd.DataFrame([{
    "Curso": c["inscripcion"]["oferta_curso"]["curso"]["nombre"],
    "Período": c["inscripcion"]["oferta_curso"]["periodo"],
    "Entregado": c["fecha_entrega"],
} for c in certs])
boton_descarga(df, "mis_certificados", "Mis certificados", key="export_mis_certificados")
st.dataframe(df, hide_index=True, use_container_width=True)

for c in certs:
    oferta = c["inscripcion"]["oferta_curso"]
    st.subheader(f"{oferta['curso']['nombre']} · {oferta['periodo']}")
    st.caption(f"Entregado el {c['fecha_entrega']}")
    try:
        pdf = sb.storage.from_("certificados").download(c["archivo_path"])
        st.download_button("⬇️ Descargar certificado (PDF)", data=pdf,
                           file_name=f"certificado_{oferta['periodo']}.pdf",
                           mime="application/pdf", key=c["archivo_path"])
    except Exception as e:
        st.error(f"No se pudo obtener el archivo: {e}")
