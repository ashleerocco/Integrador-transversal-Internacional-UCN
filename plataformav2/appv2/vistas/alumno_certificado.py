"""Mi certificado (v1). El PDF está en Drive (privado); la app lo descarga con la cuenta de servicio
y solo si el RLS deja ver la fila: certificado propio, «Entregado» y con archivo."""
import streamlit as st

from utils import drive
from utils.datos import tabla
from utils.estilos import encabezado
from utils.supabase_client import exigir_rol, get_client

exigir_rol("alumno")
sb = get_client()
encabezado("Mi certificado")

certs = tabla(sb, "certificado", "rut_estudiante, oferta_id, curso, fecha_entrega, drive_file_id")
if certs.empty:
    st.info("Aún no tienes certificados disponibles. Cuando la coordinación lo entregue, aparecerá aquí.")
    st.stop()

for c in certs.to_dict("records"):
    st.subheader(c["curso"])
    st.caption(f"Entregado el {c['fecha_entrega']}")
    clave = f"cert_{c['oferta_id']}"
    if clave not in st.session_state:
        if st.button("Preparar descarga", key=f"prep_{c['oferta_id']}"):
            try:
                st.session_state[clave] = drive.descargar(c["drive_file_id"])
                st.rerun()
            except Exception:
                st.error("No se pudo obtener el archivo en este momento. Inténtalo más tarde.")
    else:
        st.download_button("⬇️ Descargar certificado (PDF)", data=st.session_state[clave],
                           file_name=f"certificado_{c['oferta_id']}.pdf", mime="application/pdf",
                           key=f"dl_{c['oferta_id']}", on_click="ignore")
