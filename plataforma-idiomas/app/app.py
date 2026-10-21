import streamlit as st
from utils.supabase_client import login, logout

st.set_page_config(page_title="Gestión de Idiomas · UCN", page_icon="🌎", layout="wide")


def pantalla_login():
    st.title("Sección de Idiomas · UCN Internacional")
    st.caption("Ingresa con tu correo y contraseña")
    with st.form("login"):
        email = st.text_input("Correo")
        password = st.text_input("Contraseña", type="password")
        enviar = st.form_submit_button("Ingresar")
    if enviar:
        ok, msg = login(email.strip(), password)
        if ok:
            st.rerun()
        else:
            st.error(msg)


perfil = st.session_state.get("perfil")
if not perfil:
    pantalla_login()
    st.stop()

# Menú según el rol (RF-06). La seguridad real la aplica Supabase con RLS;
# esto solo evita mostrar páginas que el usuario no puede usar.
PAGINAS = {
    "coordinadora": [
        st.Page("vistas/coord_resumen.py", title="Resumen", icon="📊", default=True),
        st.Page("vistas/coord_pagos.py", title="Pagos", icon="💳"),
        st.Page("vistas/coord_certificados.py", title="Certificados", icon="🎓"),
        st.Page("vistas/docente_asistencia.py", title="Asistencia", icon="✅"),
        st.Page("vistas/docente_notas.py", title="Notas", icon="📝"),
    ],
    "docente": [
        st.Page("vistas/docente_asistencia.py", title="Asistencia", icon="✅", default=True),
        st.Page("vistas/docente_notas.py", title="Notas", icon="📝"),
    ],
    "estudiante": [
        st.Page("vistas/alumno_notas.py", title="Mis notas", icon="📝", default=True),
        st.Page("vistas/alumno_certificado.py", title="Mi certificado", icon="🎓"),
    ],
}

with st.sidebar:
    st.markdown(f"**{perfil['nombre']}**")
    st.caption(perfil["rol"].capitalize())
    if st.button("Cerrar sesión"):
        logout()
        st.rerun()

st.navigation(PAGINAS[perfil["rol"]]).run()
