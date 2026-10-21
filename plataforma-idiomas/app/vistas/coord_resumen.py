import streamlit as st
import pandas as pd
from utils.supabase_client import get_client
from utils.estilos import encabezado

sb = get_client()
encabezado("Resumen general")


def clp(n):
    return f"${n:,.0f}".replace(",", ".")


# RF-01: estudiantes por tipo
est = sb.table("estudiante").select("id, tipo_estudiante(nombre)").execute().data
pagos = sb.table("pago").select("monto, estado").execute().data
pagado = sum(p["monto"] for p in pagos if p["estado"] == "pagado")
pendiente = sum(p["monto"] for p in pagos if p["estado"] == "pendiente")

c1, c2, c3 = st.columns(3)
c1.metric("Estudiantes registrados", len(est))
c2.metric("Pagado", clp(pagado))
c3.metric("Pendiente de pago", clp(pendiente))

st.subheader("Estudiantes por tipo")
if est:
    df = pd.DataFrame([e["tipo_estudiante"]["nombre"] for e in est], columns=["Tipo"])
    st.bar_chart(df["Tipo"].value_counts(), color="#6D5CE8")
else:
    st.info("Aún no hay estudiantes registrados.")

# RF-03: inscritos vs mínimo
st.subheader("Inscritos frente al mínimo para abrir el curso")
v = sb.table("v_inscritos_vs_minimo").select("*").execute().data
if v:
    df = pd.DataFrame(v).rename(columns={
        "curso": "Curso", "periodo": "Período", "cupo_minimo": "Mínimo",
        "inscritos": "Inscritos", "alcanza_minimo": "Alcanza mínimo",
    }).drop(columns=["oferta_id"])
    st.dataframe(df, hide_index=True, use_container_width=True)
else:
    st.info("No hay ofertas de cursos registradas.")
