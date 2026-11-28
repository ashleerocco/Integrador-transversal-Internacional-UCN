"""Mis cursos (docente): sus cursos asignados y acceso directo a Asistencia y Notas.

Los datos vienen de idiomas.mis_cursos_docente(): solo los cursos donde
oferta.rut_docente es el docente conectado (reconocido por su correo).
"""
import streamlit as st

from utils.formulario_inscripcion import _fecha_larga
from utils.estilos import encabezado
from utils.supabase_client import exigir_rol, get_client

exigir_rol("docente")
sb = get_client()
encabezado("Mis cursos", "Registra la asistencia y las notas de tus alumnos")

cursos = sb.rpc("mis_cursos_docente").execute().data or []
if not cursos:
    st.info("Aún no tienes cursos asignados. La coordinación te asigna los cursos en «Ofertas de cursos».")
    st.stop()

ESTADOS = {"abierta": "Abierta", "confirmada": "Confirmada", "no_se_dicta": "No se dicta", "cerrada": "Cerrada"}


def ir(pagina: str, oferta_id: int):
    st.session_state.curso_docente = oferta_id  # Asistencia y Notas abren este curso
    st.switch_page(pagina)


for c in cursos:
    with st.container(border=True):
        izq, der = st.columns([3, 2], vertical_alignment="center")
        with izq:
            st.markdown(f"**{c['etiqueta']}**")
            datos = [ESTADOS.get(c["estado"], c["estado"] or ""), c.get("modalidad") or "", c.get("horario_texto") or ""]
            if c.get("fecha_inicio_curso"):
                datos.append(f"Clases: {_fecha_larga(c['fecha_inicio_curso'])} al {_fecha_larga(c.get('fecha_fin_curso'))}")
            st.caption(" · ".join(d for d in datos if d))
            st.caption(f"{c['alumnos_pagados']} alumno(s) en «Estudiantes pagados»")
        with der:
            b1, b2 = st.columns(2)
            if b1.button("Asistencia", key=f"asis_{c['oferta_id']}", icon=":material/fact_check:", width="stretch"):
                ir("vistas/docente_asistencia.py", c["oferta_id"])
            if b2.button("Notas", key=f"notas_{c['oferta_id']}", icon=":material/edit_note:", width="stretch"):
                ir("vistas/docente_notas.py", c["oferta_id"])
