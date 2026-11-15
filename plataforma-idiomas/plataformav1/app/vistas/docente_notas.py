import streamlit as st
import pandas as pd
from utils.supabase_client import get_client
from utils.estilos import encabezado
from utils.datos import nombre_completo
from utils.exportar import boton_descarga

sb = get_client()
perfil = st.session_state.perfil
encabezado("Notas")  # RF-05

q = sb.table("oferta_curso").select("id, periodo, estado, curso(nombre)")
if perfil["rol"] == "docente":
    q = q.eq("docente_id", perfil["docente_id"])
ofertas = q.order("periodo", desc=True).execute().data

if not ofertas:
    st.info("No hay cursos asignados.")
    st.stop()

op = {f"{o['curso']['nombre']} · {o['periodo']} ({o['estado']})": o["id"] for o in ofertas}
oferta_id = op[st.selectbox("Curso", list(op))]

insc = sb.table("inscripcion").select(
    "id, nota_final, estudiante(nombres, apellido_paterno, apellido_materno)"
).eq("oferta_id", oferta_id).in_("estado", ["inscrito", "aprobado", "reprobado"]).execute().data

if not insc:
    st.info("No hay estudiantes inscritos en este curso.")
    st.stop()

notas = sb.table("nota").select("inscripcion_id, numero, nota").in_(
    "inscripcion_id", [i["id"] for i in insc]).execute().data
mapa = {(n["inscripcion_id"], n["numero"]): n["nota"] for n in notas}

df = pd.DataFrame([{
    "inscripcion_id": i["id"],
    "Estudiante": nombre_completo(i["estudiante"]),
    "Nota 1": mapa.get((i["id"], 1)),
    "Nota 2": mapa.get((i["id"], 2)),
    "Nota 3": mapa.get((i["id"], 3)),
    "Nota final": i.get("nota_final"),
} for i in insc])

cfg = {"inscripcion_id": None}
for c in ("Nota 1", "Nota 2", "Nota 3"):
    cfg[c] = st.column_config.NumberColumn(c, min_value=1.0, max_value=7.0, step=0.1, format="%.1f")
cfg["Nota final"] = st.column_config.NumberColumn(
    "Nota final", min_value=1.0, max_value=7.0, step=0.1, format="%.1f",
)

editado = st.data_editor(
    df, hide_index=True, use_container_width=True,
    disabled=["inscripcion_id", "Estudiante"], column_config=cfg,
    key=f"notas_{oferta_id}",
)
boton_descarga(editado.drop(columns=["inscripcion_id"]), "notas_curso", "Notas", key=f"export_notas_{oferta_id}")

if st.button("Guardar notas", type="primary"):
    filas = []
    finales = []
    for r in editado.to_dict("records"):
        for k in (1, 2, 3):
            valor = r[f"Nota {k}"]
            if pd.notna(valor):
                filas.append({"inscripcion_id": int(r["inscripcion_id"]),
                              "numero": k, "nota": round(float(valor), 1)})
        nota_final = r["Nota final"]
        finales.append({
            "inscripcion_id": int(r["inscripcion_id"]),
            "nota_final": round(float(nota_final), 1) if pd.notna(nota_final) else None,
        })
    try:
        if filas:
            sb.table("nota").upsert(filas, on_conflict="inscripcion_id,numero").execute()
        for fila in finales:
            sb.table("inscripcion").update({"nota_final": fila["nota_final"]}).eq(
                "id", fila["inscripcion_id"],
            ).execute()
        st.success("Notas y notas finales guardadas.")
    except Exception:
        st.error("No se pudieron guardar las notas. Inténtalo nuevamente.")
