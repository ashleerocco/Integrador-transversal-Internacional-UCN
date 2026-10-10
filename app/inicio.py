"""Página principal: prueba de conexión y resumen general."""
import pandas as pd
import streamlit as st

from supabase_client import get_client

st.set_page_config(page_title="Gestión Idiomas UCN", page_icon="🌎", layout="wide")

st.title("Sistema de gestión – Sección de Idiomas")
st.caption("Prototipo del Hito Intermedio · Integrador Transversal · Datos de prueba")

try:
    client = get_client()

    # Conteo de registros por tabla (comprueba que la conexión funciona)
    tablas = {
        "Estudiantes": "estudiante",
        "Ofertas de curso": "oferta_curso",
        "Inscripciones": "inscripcion",
        "Pagos": "pago",
        "Certificados": "certificado",
    }
    st.success("Conexión con Supabase correcta.")
    columnas = st.columns(len(tablas))
    for col, (etiqueta, tabla) in zip(columnas, tablas.items()):
        resp = client.table(tabla).select("id", count="exact").limit(1).execute()
        col.metric(etiqueta, resp.count)

    # RF-03: inscritos frente al cupo mínimo
    st.subheader("Inscritos frente al cupo mínimo")
    vista = client.table("v_inscritos_vs_minimo").select("*").execute()
    if vista.data:
        df = pd.DataFrame(vista.data).rename(
            columns={
                "curso": "Curso",
                "periodo": "Período",
                "cupo_minimo": "Cupo mínimo",
                "inscritos": "Inscritos",
                "alcanza_minimo": "Alcanza el mínimo",
            }
        )
        st.dataframe(df.drop(columns=["oferta_id"]), width="stretch", hide_index=True)
    else:
        st.info("Aún no hay ofertas de curso registradas.")

except Exception as error:  # noqa: BLE001
    st.error(
        "No se pudo conectar con Supabase. Revisa que exista el archivo "
        ".streamlit/secrets.toml con SUPABASE_URL y SUPABASE_KEY."
    )
    st.caption(f"Detalle técnico: {type(error).__name__}")
