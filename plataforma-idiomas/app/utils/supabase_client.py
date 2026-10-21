import streamlit as st
from supabase import create_client, Client


def get_client() -> Client:
    """Un cliente POR SESIÓN de navegador (nunca compartido entre usuarios).
    Usa la clave anon: así Supabase aplica las políticas RLS del usuario logueado."""
    if "sb" not in st.session_state:
        st.session_state.sb = create_client(
            st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"]
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
