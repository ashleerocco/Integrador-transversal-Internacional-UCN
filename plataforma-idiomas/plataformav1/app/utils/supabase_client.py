"""Cliente Supabase y login por rol (reciclado de la versión anterior).

Cambios respecto de v1: el cliente apunta al esquema `idiomas` y el perfil se
lee de `idiomas.perfil` (roles coordinacion / docente / alumno).
La app usa SOLO la clave anon/publishable: Supabase aplica RLS con la sesión de
cada usuario. La clave service_role no se usa ni se envía al navegador.
"""
import streamlit as st
from supabase import ClientOptions, create_client, Client

ESQUEMA = "idiomas"


def get_client() -> Client:
    """Un cliente POR SESIÓN de navegador (nunca compartido entre usuarios)."""
    if "sb" not in st.session_state:
        st.session_state.sb = create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_ANON_KEY"],
            options=ClientOptions(schema=ESQUEMA, persist_session=False),
        )
    return st.session_state.sb


def login(email: str, password: str):
    sb = get_client()
    try:
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
    except Exception:
        return False, "Correo o contraseña incorrectos."

    perfil = sb.table("perfil").select("*").eq("id", res.user.id).execute().data
    if not perfil:
        sb.auth.sign_out()
        return False, "Tu usuario no tiene un perfil asignado. Contacta a la coordinación."

    st.session_state.perfil = perfil[0]
    return True, ""


def logout():
    try:
        get_client().auth.sign_out()
    except Exception:
        pass
    st.session_state.clear()


def perfil_actual() -> dict:
    return st.session_state.get("perfil") or {}


def exigir_rol(*roles: str):
    """Defensa en la interfaz; la seguridad real la aplica RLS."""
    if perfil_actual().get("rol") not in roles:
        st.error("No tienes acceso a esta sección.")
        st.stop()
