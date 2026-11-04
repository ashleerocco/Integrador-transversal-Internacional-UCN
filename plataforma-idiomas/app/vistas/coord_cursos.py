import pandas as pd
import streamlit as st

from utils.estilos import encabezado
from utils.supabase_client import get_client

sb = get_client()
encabezado("Cursos", "Registra y consulta las ofertas de cursos de idiomas")

IDIOMAS = ["Alemán", "Francés", "Inglés", "Italiano", "Portugués", "Otro"]
NIVELES = ["A1", "A2", "B1", "B2", "C1", "C2", "Otro"]
MODALIDADES = ["Presencial", "Online", "Híbrida"]

with st.expander("➕ Registrar curso", expanded=True):
    with st.form("nuevo_curso", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        idioma = c1.selectbox("Idioma *", IDIOMAS)
        if idioma == "Otro":
            idioma = c1.text_input("Especifica el idioma *")
        nivel = c2.selectbox("Nivel *", NIVELES)
        if nivel == "Otro":
            nivel = c2.text_input("Especifica el nivel *")
        semestre = c3.selectbox("Semestre *", ["1", "2"])

        c1, c2, c3 = st.columns(3)
        anio = c1.number_input("Año *", min_value=2000, max_value=2100, value=2026, step=1)
        modalidad = c2.selectbox("Modalidad *", MODALIDADES)
        valor = c3.number_input("Valor del curso (CLP) *", min_value=0, step=1000)

        c1, c2 = st.columns(2)
        cupo_minimo = c1.number_input("Cupo mínimo *", min_value=1, step=1, value=5)
        cupo_maximo = c2.number_input("Cupo máximo *", min_value=1, step=1, value=20)

        c1, c2 = st.columns(2)
        fecha_inicio = c1.date_input("Fecha de inicio *")
        fecha_termino = c2.date_input("Fecha de término *")

        guardar = st.form_submit_button("Guardar curso", type="primary")

    if guardar:
        nombre_idioma = idioma.strip() if isinstance(idioma, str) else ""
        nombre_nivel = nivel.strip() if isinstance(nivel, str) else ""
        if not nombre_idioma or not nombre_nivel:
            st.error("Completa el idioma y el nivel.")
        elif cupo_maximo < cupo_minimo:
            st.error("El cupo máximo debe ser igual o mayor que el mínimo.")
        elif fecha_termino <= fecha_inicio:
            st.error("La fecha de término debe ser posterior a la fecha de inicio.")
        else:
            nombre_curso = f"{nombre_idioma} {nombre_nivel}"
            periodo = f"{semestre}-{int(anio)}"
            try:
                catalogo = sb.table("curso").select("id").eq("nombre", nombre_curso).execute().data
                if catalogo:
                    curso_id = catalogo[0]["id"]
                else:
                    curso = sb.table("curso").insert({"nombre": nombre_curso}).execute().data
                    curso_id = curso[0]["id"]

                sb.table("oferta_curso").insert({
                    "curso_id": curso_id,
                    "periodo": periodo,
                    "estado": "convocatoria",
                    "modalidad": modalidad,
                    "valor": int(valor),
                    "cupo_minimo": int(cupo_minimo),
                    "cupo_maximo": int(cupo_maximo),
                    "fecha_inicio": fecha_inicio.isoformat(),
                    "fecha_termino": fecha_termino.isoformat(),
                }).execute()
                st.success(f"Curso {nombre_curso} ({periodo}) registrado.")
            except Exception as e:
                st.error(f"No se pudo guardar el curso: {e}")

st.subheader("Ofertas registradas")
try:
    ofertas = sb.table("oferta_curso").select(
        "id, periodo, estado, modalidad, valor, cupo_minimo, cupo_maximo, "
        "fecha_inicio, fecha_termino, curso(nombre)"
    ).order("periodo", desc=True).execute().data
except Exception as e:
    st.error(f"No se pudieron cargar las ofertas: {e}")
    st.stop()

if ofertas:
    df = pd.DataFrame([{
        "Curso": o["curso"]["nombre"],
        "Semestre": o["periodo"],
        "Modalidad": o["modalidad"],
        "Valor (CLP)": o["valor"],
        "Cupo mínimo": o["cupo_minimo"],
        "Cupo máximo": o["cupo_maximo"],
        "Inicio": o["fecha_inicio"],
        "Término": o["fecha_termino"],
        "Estado": o["estado"],
    } for o in ofertas])
    st.dataframe(df, hide_index=True, use_container_width=True)
else:
    st.info("Aún no hay cursos registrados.")
