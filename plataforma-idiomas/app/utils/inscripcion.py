"""Formulario público de inscripción. Las solicitudes quedan pendientes de revisión."""

import streamlit as st

from utils.estilos import encabezado
from utils.formulario_estudiante import render_formulario_estudiante, subir_documento
from utils.supabase_client import get_client

try:
    from postgrest.types import ReturnMethod
    MINIMAL = ReturnMethod.minimal
except Exception:
    MINIMAL = "minimal"


def _etiqueta(oferta: dict) -> str:
    partes = [oferta["curso"]["nombre"], oferta["periodo"]]
    if oferta.get("modalidad"):
        partes.append(oferta["modalidad"])
    if oferta.get("fecha_inicio"):
        partes.append(f"inicio {oferta['fecha_inicio']}")
    if oferta.get("valor"):
        partes.append(f"${oferta['valor']:,}".replace(",", "."))
    return " · ".join(partes)


def _cargar_ofertas(sb):
    for campos in (
        "id, periodo, modalidad, valor, fecha_inicio, curso(nombre)",
        "id, periodo, curso(nombre)",
    ):
        try:
            return (sb.table("oferta_curso").select(campos)
                    .eq("estado", "convocatoria").order("periodo", desc=True)
                    .execute().data)
        except Exception as error:
            ultimo = error
    raise ultimo


def formulario_inscripcion():
    sb = get_client()
    encabezado("Inscríbete en un curso de idiomas",
               "Completa el formulario; no necesitas crear una cuenta")

    if st.session_state.get("inscripcion_enviada"):
        st.success("¡Recibimos tu inscripción! La coordinación la revisará y te contactará al correo indicado.")
        if st.button("Enviar otra inscripción"):
            st.session_state.pop("inscripcion_enviada", None)
            st.rerun()
        return

    try:
        ofertas = _cargar_ofertas(sb)
    except Exception:
        st.error("No pudimos cargar los cursos disponibles. Inténtalo nuevamente.")
        return
    if not ofertas:
        st.info("Por ahora no hay convocatorias abiertas. Vuelve a revisar pronto.")
        return

    opciones = {_etiqueta(oferta): oferta["id"] for oferta in ofertas}
    curso = st.selectbox("Curso de interés *", list(opciones))
    datos = render_formulario_estudiante(sb, modo="inscripcion")
    if datos is None:
        return

    try:
        cedula_path = subir_documento(sb, datos.pop("_cedula"), datos["documento"], "cedula", solicitud_publica=True)
        licencia_path = subir_documento(sb, datos.pop("_licencia"), datos["documento"], "licencia_media", solicitud_publica=True)
        datos.pop("_existing_id", None)
        datos.pop("_sin_cambios", None)
        solicitud = {
            **datos,
            "oferta_id": opciones[curso],
            "estado": "pendiente",
            "cedula_path": cedula_path,
            "licencia_media_path": licencia_path,
            "acepta_datos": True,
        }
        sb.table("solicitud_inscripcion").insert(solicitud, returning=MINIMAL).execute()
        st.session_state.inscripcion_enviada = True
        st.rerun()
    except Exception as error:
        mensaje = str(error).lower()
        if "duplicate" in mensaje or "23505" in mensaje:
            st.error("Ya existe una solicitud para este RUT y curso.")
        else:
            st.error("No se pudo enviar la inscripción. Revisa los datos y vuelve a intentarlo.")
