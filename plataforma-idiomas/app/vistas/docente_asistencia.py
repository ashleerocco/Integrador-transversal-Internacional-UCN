import streamlit as st
import pandas as pd
from utils.supabase_client import get_client
from utils.estilos import encabezado
from utils.datos import nombre_completo

sb = get_client()
perfil = st.session_state.perfil
encabezado("Asistencia")  # RF-04

# Cursos a mostrar: la coordinadora ve todos; el docente solo los suyos
q = sb.table("oferta_curso").select("id, periodo, estado, curso(nombre)")
if perfil["rol"] == "docente":
    q = q.eq("docente_id", perfil["docente_id"])
ofertas = q.order("periodo", desc=True).execute().data

if not ofertas:
    st.info("No hay cursos asignados.")
    st.stop()

op = {f"{o['curso']['nombre']} · {o['periodo']} ({o['estado']})": o["id"] for o in ofertas}
oferta_id = op[st.selectbox("Curso", list(op))]

sesiones = sb.table("sesion").select("*").eq("oferta_id", oferta_id).order("numero").execute().data

with st.expander("➕ Crear nueva sesión"):
    siguiente = (max(s["numero"] for s in sesiones) + 1) if sesiones else 1
    n = st.number_input("N° de sesión", min_value=1, value=siguiente, step=1)
    f = st.date_input("Fecha")
    if st.button("Crear sesión"):
        try:
            sb.table("sesion").insert(
                {"oferta_id": oferta_id, "numero": int(n), "fecha": f.isoformat()}
            ).execute()
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo crear (¿ya existe esa sesión?): {e}")

if not sesiones:
    st.info("Este curso aún no tiene sesiones. Crea la primera arriba.")
    st.stop()

ses_op = {f"Sesión {s['numero']} · {s['fecha'] or 's/f'}": s["id"] for s in sesiones}
sesion_id = ses_op[st.selectbox("Sesión", list(ses_op))]

insc = sb.table("inscripcion").select(
    "id, estudiante(nombres, apellido_paterno, apellido_materno)"
).eq("oferta_id", oferta_id).in_("estado", ["inscrito", "aprobado", "reprobado"]).execute().data

if not insc:
    st.info("No hay estudiantes inscritos en este curso.")
    st.stop()

previas = sb.table("asistencia").select("inscripcion_id, estado").eq("sesion_id", sesion_id).execute().data
mapa = {a["inscripcion_id"]: a["estado"] for a in previas}

df = pd.DataFrame([{
    "inscripcion_id": i["id"],
    "Estudiante": nombre_completo(i["estudiante"]),
    "Estado": mapa.get(i["id"], "P"),
} for i in insc])

editado = st.data_editor(
    df, hide_index=True, use_container_width=True,
    disabled=["inscripcion_id", "Estudiante"],
    column_config={
        "inscripcion_id": None,
        "Estado": st.column_config.SelectboxColumn(
            "Estado", options=["P", "A", "J"], required=True,
            help="P = Presente, A = Ausente, J = Justificado"),
    },
    key=f"asis_{sesion_id}",
)

if st.button("Guardar asistencia", type="primary"):
    filas = [{"sesion_id": sesion_id, "inscripcion_id": int(r.inscripcion_id), "estado": r.Estado}
             for r in editado.itertuples()]
    try:
        sb.table("asistencia").upsert(filas, on_conflict="sesion_id,inscripcion_id").execute()
        st.success("Asistencia guardada.")
    except Exception as e:
        st.error(f"No se pudo guardar: {e}")

with st.expander("📈 Porcentaje de asistencia del curso"):
    ids = [i["id"] for i in insc]
    pct = sb.table("v_asistencia_inscripcion").select("*").in_("inscripcion_id", ids).execute().data
    nombres = {i["id"]: nombre_completo(i["estudiante"]) for i in insc}
    if pct:
        st.dataframe(pd.DataFrame([{
            "Estudiante": nombres[p["inscripcion_id"]],
            "Sesiones registradas": p["sesiones_registradas"],
            "Presentes": p["presentes"],
            "% asistencia": p["porcentaje_asistencia"],
        } for p in pct]), hide_index=True, use_container_width=True)
