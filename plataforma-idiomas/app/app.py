import streamlit as st
from utils.supabase_client import login, logout
from utils.estilos import (
    aplicar_estilos, encabezado, panel_login, LOGO, FAVICON,
)

st.set_page_config(
    page_title="Idiomas · DRI UCN",
    page_icon=str(FAVICON),
    layout="wide",
)
aplicar_estilos()


def pantalla_login():
    izq, der = st.columns([1.05, 1], gap="large")
    with izq:
        panel_login()
    with der:
        st.markdown("<div style='height:3.5rem'></div>", unsafe_allow_html=True)
        encabezado("Iniciar sesión", "Ingresa con tu correo y contraseña")
        with st.form("login"):
            email = st.text_input("Correo")
            password = st.text_input("Contraseña", type="password")
            enviar = st.form_submit_button("Ingresar", type="primary")
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
        st.Page("vistas/coord_resumen.py", title="Resumen", icon=":material/dashboard:", default=True),
        st.Page("vistas/coord_estudiantes.py", title="Estudiantes", icon=":material/groups:"),
        st.Page("vistas/coord_pagos.py", title="Pagos", icon=":material/payments:"),
        st.Page("vistas/coord_certificados.py", title="Certificados", icon=":material/workspace_premium:"),
        st.Page("vistas/docente_asistencia.py", title="Asistencia", icon=":material/fact_check:"),
        st.Page("vistas/docente_notas.py", title="Notas", icon=":material/edit_note:"),
    ],
    "docente": [
        st.Page("vistas/docente_asistencia.py", title="Asistencia", icon=":material/fact_check:", default=True),
        st.Page("vistas/docente_notas.py", title="Notas", icon=":material/edit_note:"),
    ],
    "estudiante": [
        st.Page("vistas/alumno_notas.py", title="Mis notas", icon=":material/edit_note:", default=True),
        st.Page("vistas/alumno_certificado.py", title="Mi certificado", icon=":material/workspace_premium:"),
    ],
}

st.logo(str(LOGO))

with st.sidebar:
    st.divider()
    st.markdown(f"**{perfil['nombre']}**")
    st.caption(perfil["rol"].capitalize())
    if st.button("Cerrar sesión"):
        logout()
        st.rerun()

st.navigation(PAGINAS[perfil["rol"]]).run()
