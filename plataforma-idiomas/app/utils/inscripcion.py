"""Formulario público de inscripción (sin login).

Escribe SOLO en `solicitud_inscripcion` con la clave anon. La coordinadora
revisa y aprueba cada solicitud desde la página "Solicitudes".
"""
import streamlit as st

from utils.estilos import encabezado
from utils.supabase_client import get_client
from utils.validaciones import normalizar_rut, rut_valido, correo_valido

try:  # el insert del público no puede leer de vuelta la fila (no hay SELECT para anon)
    from postgrest.types import ReturnMethod
    MINIMAL = ReturnMethod.minimal
except Exception:  # versiones antiguas
    MINIMAL = "minimal"


def _etiqueta(o: dict) -> str:
    partes = [o["curso"]["nombre"], o["periodo"]]
    if o.get("modalidad"):
        partes.append(o["modalidad"])
    if o.get("fecha_inicio"):
        partes.append(f"inicio {o['fecha_inicio']}")
    if o.get("valor"):
        partes.append(f"${o['valor']:,}".replace(",", "."))
    return " · ".join(partes)


def _cargar_ofertas(sb):
    """Pide los datos completos; si la tabla aún no tiene alguna columna,
    cae a una consulta mínima para que el formulario siga funcionando."""
    for campos in ("id, periodo, modalidad, valor, fecha_inicio, curso(nombre)",
                   "id, periodo, curso(nombre)"):
        try:
            return (sb.table("oferta_curso").select(campos)
                    .eq("estado", "convocatoria").order("periodo", desc=True)
                    .execute().data)
        except Exception as e:
            ultimo = e
    raise ultimo


def formulario_inscripcion():
    sb = get_client()
    encabezado("Inscríbete en un curso de idiomas",
               "Completa el formulario; no necesitas crear una cuenta")

    if st.session_state.get("inscripcion_enviada"):
        st.success("¡Recibimos tu inscripción! La coordinación la revisará y te "
                   "contactará al correo que indicaste. Recuerda que el curso se "
                   "confirma al cerrar la convocatoria, según el cupo mínimo.")
        if st.button("Enviar otra inscripción"):
            st.session_state.pop("inscripcion_enviada")
            st.rerun()
        return

    try:
        ofertas = _cargar_ofertas(sb)
        tipos = sb.table("tipo_estudiante").select("id, nombre").order("id").execute().data
    except Exception as e:
        st.error(f"No pudimos cargar los cursos disponibles: {e}")
        return

    if not ofertas:
        st.info("Por ahora no hay convocatorias abiertas. Vuelve a revisar pronto.")
        return

    ofertas_op = {_etiqueta(o): o["id"] for o in ofertas}
    tipos_op = {t["nombre"]: t["id"] for t in tipos}

    with st.form("inscripcion_publica", clear_on_submit=False):
        curso = st.selectbox("Curso de interés *", list(ofertas_op))

        st.markdown("**Datos personales**")
        c1, c2 = st.columns(2)
        nombres = c1.text_input("Nombres *")
        rut = c2.text_input("RUT * (con guion, ej: 12345678-5)")
        c1, c2 = st.columns(2)
        ap_pat = c1.text_input("Apellido paterno *")
        ap_mat = c2.text_input("Apellido materno *")
        sexo = st.selectbox("Sexo *", ["", "Mujer", "Hombre", "Otro / Prefiere no decir"])

        st.markdown("**Contacto**")
        c1, c2 = st.columns(2)
        correo = c1.text_input("Correo electrónico *")
        telefono = c2.text_input("Teléfono *", placeholder="+56 9 1234 5678")

        st.markdown("**Vínculo con la UCN**")
        tipo = st.selectbox("Tipo de estudiante *", list(tipos_op))
        c1, c2 = st.columns(2)
        unidad = c1.text_input("Carrera * (o profesión si eres externo)")
        campus = c2.text_input("Campus UCN (opcional)",
                               placeholder="Ej: Casa Central - Antofagasta")

        acepta = st.checkbox("Autorizo el tratamiento de mis datos personales para "
                             "gestionar mi inscripción en los cursos de idiomas. *")
        enviar = st.form_submit_button("Enviar inscripción", type="primary")

    if not enviar:
        return

    doc = normalizar_rut(rut.strip())

    if not (nombres.strip() and ap_pat.strip() and ap_mat.strip() and doc
            and correo.strip() and telefono.strip() and sexo and unidad.strip()):
        st.error("Completa los campos obligatorios (*).")
    elif not rut_valido(doc):
        st.error("El RUT no es válido. Revisa el número y el dígito verificador.")
    elif not correo_valido(correo):
        st.error("El correo no parece válido.")
    elif not acepta:
        st.error("Debes autorizar el tratamiento de tus datos para continuar.")
    else:
        try:
            sb.table("solicitud_inscripcion").insert({
                "oferta_id": ofertas_op[curso],
                "nombres": nombres.strip(),
                "apellido_paterno": ap_pat.strip(),
                "apellido_materno": ap_mat.strip(),
                "sexo": sexo,
                "tipo_documento": "RUT",
                "documento": doc,
                "correo": correo.strip().lower(),
                "telefono": telefono.strip(),
                "tipo_estudiante_id": tipos_op[tipo],
                "unidad_ucn": unidad.strip(),
                "campus": campus.strip() or None,
                "acepta_datos": True,
            }, returning=MINIMAL).execute()
            st.session_state.inscripcion_enviada = True
            st.rerun()
        except Exception as e:
            msg = str(e)
            if "duplicate" in msg or "23505" in msg:
                st.error("Ya tenemos una solicitud pendiente tuya para este curso.")
            else:
                st.error(f"No se pudo enviar la inscripción: {msg}")
