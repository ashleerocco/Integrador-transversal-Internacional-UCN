import streamlit as st

from utils.estilos import FAVICON, LOGO, aplicar_estilos, banner_convocatoria, encabezado, panel_login, portada_inscripcion
from utils.formulario_inscripcion import _fecha_larga, render_formulario_inscripcion
from utils.supabase_client import activar_con_codigo, docente_sigue_activo, enviar_codigo, get_client, login, logout

st.set_page_config(page_title="Idiomas · DRI UCN", page_icon=str(FAVICON), layout="wide")
aplicar_estilos()


def convocatorias_abiertas(sb):
    """Banners de las convocatorias ABIERTAS. Devuelve False si no hay ninguna."""
    try:
        convs = sb.rpc("convocatorias_publicas").execute().data or []
    except Exception:
        st.error("No pudimos cargar las convocatorias. Inténtalo en unos minutos.")
        return False
    for c in convs:
        banner_convocatoria(
            c["nombre"],
            f"Inscripciones del {_fecha_larga(c['fecha_apertura'])} al {_fecha_larga(c['fecha_cierre'])} · "
            f"Confirmación de cursos: {_fecha_larga(c.get('fecha_confirmacion'))} · "
            f"Clases: {_fecha_larga(c.get('fecha_inicio_curso'))} al {_fecha_larga(c.get('fecha_fin_curso'))}",
            ["Convocatoria abierta", f"Período {c['periodo']}"],
        )
    if not convs:
        prox = sb.rpc("proxima_convocatoria").execute().data or []
        if prox:
            st.info(f"Por ahora no hay inscripciones abiertas. Próxima convocatoria: **{prox[0]['nombre']}**, "
                    f"desde el {_fecha_larga(prox[0]['fecha_apertura'])}.")
        else:
            st.info("Por ahora no hay inscripciones abiertas. Te esperamos en la próxima convocatoria; "
                    "revisa idiomaspie.ucn.cl o escribe a idiomas.pie@ucn.cl.")
    return bool(convs)


def pantalla_inicio():
    """Pantalla pública (layout de v1): inscripción sin cuenta y acceso con login."""
    sb = get_client()
    izq, der = st.columns([0.8, 1.7], gap="large")
    with izq:
        panel_login()
    with der:
        tab_insc, tab_login = st.tabs(["Inscripción a cursos", "Iniciar sesión"])
        with tab_insc:
            portada_inscripcion()
            if convocatorias_abiertas(sb):
                render_formulario_inscripcion(sb, modo="publico")
        with tab_login:
            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
            encabezado("Iniciar sesión", "Para coordinación y docentes")
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
            with st.expander("¿Tienes un código de acceso? Crea o cambia tu contraseña"):
                st.caption("Si la coordinación te envió el acceso, usa el código que llegó a tu correo (no pulses el enlace) para crear "
                           "tu contraseña. Si no tienes código, pide uno.")
                with st.form("codigo"):
                    c_email = st.text_input("Correo", key="c_email")
                    c_codigo = st.text_input("Código del correo", max_chars=10)
                    c1, c2 = st.columns(2)
                    c_pw = c1.text_input("Nueva contraseña (mín. 8)", type="password")
                    c_pw2 = c2.text_input("Repite la contraseña", type="password")
                    activar = st.form_submit_button("Crear contraseña e ingresar", type="primary")
                    pedir = st.form_submit_button("Enviarme un código")
                if pedir:
                    if c_email.strip():
                        st.info(enviar_codigo(c_email.strip().lower())[1])
                    else:
                        st.error("Escribe tu correo.")
                if activar:
                    if not (c_email.strip() and c_codigo.strip()):
                        st.error("Completa correo y código.")
                    elif len(c_pw) < 8 or c_pw != c_pw2:
                        st.error("La contraseña debe tener al menos 8 caracteres y coincidir en ambos campos.")
                    else:
                        ok, msg = activar_con_codigo(c_email.strip().lower(), c_codigo.strip(), c_pw)
                        if ok:
                            st.rerun()
                        else:
                            st.error(msg)


perfil = st.session_state.get("perfil")
if not perfil:
    pantalla_inicio()
    st.stop()

# Desmarcar «Activo» quita el acceso de inmediato (además, RLS ya no le entrega datos)
if not docente_sigue_activo():
    logout()
    st.warning("Tu acceso de docente fue desactivado. Contacta a la coordinación.")
    pantalla_inicio()
    st.stop()

# Menú según el rol. La seguridad real la aplica Supabase con RLS.
P = st.Page
PAGINAS = {
    "coordinacion": [
        P("vistas/coord_resumen.py", title="Resumen", icon=":material/dashboard:", default=True),
        P("vistas/coord_cursos.py", title="Cursos", icon=":material/menu_book:"),
        P("vistas/coord_solicitudes.py", title="Solicitudes", icon=":material/inbox:"),
        P("vistas/coord_estudiantes.py", title="Estudiantes", icon=":material/groups:"),
        P("vistas/coord_pagos.py", title="Pagos", icon=":material/payments:"),
        P("vistas/docente_asistencia.py", title="Asistencia", icon=":material/fact_check:"),
        P("vistas/docente_notas.py", title="Notas", icon=":material/edit_note:"),
        P("vistas/coord_certificados.py", title="Certificados", icon=":material/workspace_premium:"),
    ],
    "docente": [
        P("vistas/docente_cursos.py", title="Mis cursos", icon=":material/school:", default=True),
        P("vistas/docente_asistencia.py", title="Asistencia", icon=":material/fact_check:"),
        P("vistas/docente_notas.py", title="Notas", icon=":material/edit_note:"),
    ],
    "alumno": [
        P("vistas/alumno_notas.py", title="Mis notas y asistencia", icon=":material/edit_note:", default=True),
        P("vistas/alumno_certificado.py", title="Mi certificado", icon=":material/workspace_premium:"),
    ],
}

st.logo(str(LOGO))

with st.sidebar:
    st.divider()
    st.markdown(f"**{perfil['nombre']}**")
    st.caption({"coordinacion": "Coordinación", "docente": "Docente", "alumno": "Estudiante"}[perfil["rol"]])
    if st.button("Cerrar sesión"):
        logout()
        st.rerun()

st.navigation(PAGINAS[perfil["rol"]]).run()
