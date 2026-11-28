"""Cliente Supabase y login por rol (reciclado de la versión anterior).

Cambios respecto de v1: el cliente apunta al esquema `idiomas`.
- Docente: se reconoce SOLO por correo (rpc mi_docente_id: correo confirmado de Auth
  = docente.correo con activo = true). No usa perfil.rol.
- Coordinación y alumno: perfil en `idiomas.perfil`.
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


def mi_docente_id(sb=None) -> str | None:
    """RUT del docente activo cuyo correo coincide con el del usuario conectado (o None).

    Es la ÚNICA forma de reconocer a un docente: no se usa perfil.rol. Si la
    coordinación lo desmarca como «Activo», devuelve None y pierde el acceso.
    """
    try:
        return (sb or get_client()).rpc("mi_docente_id").execute().data or None
    except Exception:
        return None


def _cargar_perfil(sb, user_id: str):
    """Después de autenticarse: docente (por correo) o perfil de coordinación/alumno."""
    rut = mi_docente_id(sb)
    if rut:
        fila = sb.table("docente").select("nombres, apellidos").eq("rut", rut).execute().data
        nombre = f"{fila[0]['nombres']} {fila[0]['apellidos']}" if fila else "Docente"
        st.session_state.perfil = {"id": user_id, "rol": "docente", "nombre": nombre, "rut_docente": rut}
        return True, ""

    perfil = sb.table("perfil").select("*").eq("id", user_id).execute().data
    # Un perfil antiguo con rol 'docente' ya no da acceso: el docente se reconoce solo por correo + activo
    if not perfil or perfil[0]["rol"] == "docente":
        sb.auth.sign_out()
        if perfil:
            return False, "Tu acceso de docente no está activo. Contacta a la coordinación."
        return False, "Tu usuario no tiene acceso asignado. Contacta a la coordinación."
    st.session_state.perfil = perfil[0]
    return True, ""


def login(email: str, password: str):
    sb = get_client()
    try:
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
    except Exception:
        return False, "Correo o contraseña incorrectos."
    return _cargar_perfil(sb, res.user.id)


def enviar_codigo(email: str):
    """Envía un correo con código para crear o recuperar la contraseña."""
    try:
        get_client().auth.reset_password_for_email(email)
    except Exception:
        pass  # mismo mensaje exista o no la cuenta (no revelar qué correos están registrados)
    return True, "Si el correo tiene acceso, te llegará un mensaje con un código. Cópialo aquí; no pulses enlaces del correo."


def activar_con_codigo(email: str, codigo: str, password: str):
    """Primer ingreso (invitación) o recuperación: valida el código del correo y fija la contraseña."""
    sb = get_client()
    res = None
    for tipo in ("invite", "recovery", "email"):
        try:
            res = sb.auth.verify_otp({"email": email, "token": codigo, "type": tipo})
            if res and res.user:
                break
        except Exception:
            res = None
    if not res or not res.user:
        return False, "El código no es válido o ya venció. Pide uno nuevo."
    try:
        sb.auth.update_user({"password": password})
    except Exception:
        sb.auth.sign_out()
        return False, "No se pudo guardar la contraseña (mínimo 8 caracteres)."
    # supabase-py solo aplica la sesión a las consultas en el evento SIGNED_IN: tras verificar
    # un código (recuperación) o cambiar la contraseña, las consultas seguirían como anónimo.
    # Por eso se inicia sesión de forma normal con la contraseña recién creada.
    return login(email, password)


def docente_sigue_activo() -> bool:
    """Se revisa en cada carga: si lo desactivan, se cierra su sesión."""
    p = st.session_state.get("perfil") or {}
    return p.get("rol") != "docente" or mi_docente_id() == p.get("rut_docente")


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
