import streamlit as st
import pandas as pd
from utils.supabase_client import get_client

sb = get_client()
st.title("Mis notas")

# RLS garantiza que solo llegan las inscripciones y notas de este estudiante
insc = sb.table("inscripcion").select(
    "id, estado, nota_final, oferta_curso(periodo, curso(nombre)), nota(numero, nota)"
).execute().data

if not insc:
    st.info("Aún no tienes cursos inscritos.")
    st.stop()

for i in insc:
    st.subheader(f"{i['oferta_curso']['curso']['nombre']} · {i['oferta_curso']['periodo']}")
    st.caption(f"Estado: {i['estado']}")
    notas = sorted(i["nota"], key=lambda n: n["numero"])
    if notas:
        st.dataframe(pd.DataFrame([{"Evaluación": f"Nota {n['numero']}", "Nota": n["nota"]} for n in notas]),
                     hide_index=True)
    else:
        st.write("Aún no hay notas registradas.")
    if i["nota_final"] is not None:
        st.metric("Nota final", i["nota_final"])
