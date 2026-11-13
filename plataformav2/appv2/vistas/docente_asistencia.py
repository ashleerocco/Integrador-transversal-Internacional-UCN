"""Asistencia (lógica y pantalla de v1). Nuevo: solo alumnos de «Estudiantes pagados»,
código S (sesión suspendida) y calendario automático según el horario del curso."""
import pandas as pd
import streamlit as st

from utils import sheets
from utils.datos import ofertas_opciones, tabla
from utils.errores import mensaje_error
from utils.estilos import encabezado
from utils.excel import boton_excel, renombrar
from utils.supabase_client import exigir_rol, get_client

exigir_rol("coordinacion", "docente")
sb = get_client()
encabezado("Asistencia")

CODIGOS = ["P", "A", "J", "S"]
AYUDA = "P = Presente, A = Ausente, J = Justificado, S = Sesión suspendida (no cuenta para el %)"

# La coordinación ve todos; el docente solo sus cursos (RLS por su RUT)
op = ofertas_opciones(sb)
if not op:
    st.info("No tienes cursos asignados.")
    st.stop()
oferta_id = op[st.selectbox("Curso", list(op))]

alumnos = sb.rpc("alumnos_de_oferta", {"p_oferta_id": oferta_id}).execute().data
sesiones = tabla(sb, "sesion", oferta_id=oferta_id, orden="fecha")

with st.expander("🗓️ Calendario de sesiones"):
    c1, c2 = st.columns(2)
    if c1.button("Generar calendario según el horario", help="Crea una sesión por cada día del horario entre el "
                                                             "inicio y el fin de clases de la convocatoria."):
        try:
            n = sb.rpc("generar_sesiones", {"p_oferta_id": oferta_id}).execute().data
            st.success(f"{n} sesión(es) nuevas.")
            st.rerun()
        except Exception as e:
            st.error(mensaje_error(e, "generar el calendario"))
    with c2:
        f = st.date_input("Agregar una sesión puntual", value=None, format="DD/MM/YYYY")
        if f and st.button("Agregar sesión"):
            try:
                sb.table("sesion").upsert({"oferta_id": oferta_id, "fecha": f.isoformat()}).execute()
                sb.rpc("generar_sesiones", {"p_oferta_id": oferta_id}).execute()  # renumera
                st.rerun()
            except Exception as e:
                st.error(mensaje_error(e, "agregar la sesión"))

if not alumnos:
    st.info("Este curso aún no tiene alumnos en «Estudiantes pagados». Aparecerán cuando la coordinación registre su pago.")
    st.stop()
if sesiones.empty:
    st.info("Este curso aún no tiene sesiones. Genera el calendario arriba.")
    st.stop()

ses_op = {f"Sesión {int(s.numero) if pd.notna(s.numero) else '-'} · {pd.to_datetime(s.fecha):%d/%m/%Y}"
          + (" (suspendida)" if s.suspendida else ""): s.fecha for s in sesiones.itertuples()}
fecha = ses_op[st.selectbox("Sesión", list(ses_op))]
ses = sesiones[sesiones.fecha == fecha].iloc[0]

c1, c2 = st.columns([3, 1])
if ses.suspendida:
    c1.warning(f"Sesión suspendida{': ' + ses.motivo if ses.motivo else ''}. Todos quedan con S.")
    if c2.button("Reactivar sesión"):
        sb.rpc("suspender_sesion", {"p_oferta_id": oferta_id, "p_fecha": fecha, "p_suspendida": False}).execute()
        st.rerun()
else:
    with c2.popover("Suspender sesión"):
        motivo = st.text_input("Motivo (feriado, suspensión…)")
        if st.button("Confirmar suspensión"):
            sb.rpc("suspender_sesion", {"p_oferta_id": oferta_id, "p_fecha": fecha, "p_suspendida": True,
                                        "p_motivo": motivo or None}).execute()
            sheets.tras_escritura(sb, ["asistencia"])
            st.rerun()

previas = tabla(sb, "asistencia", "rut_estudiante, estado", oferta_id=oferta_id, fecha=fecha)
mapa = dict(zip(previas.rut_estudiante, previas.estado)) if not previas.empty else {}
df = pd.DataFrame([{
    "rut": a["rut"],
    "Estudiante": a["nombre_completo"] + (f" ({a['nombre_social']})" if a.get("nombre_social") else ""),
    "Estado": mapa.get(a["rut"], "S" if ses.suspendida else "P"),
} for a in alumnos])

editado = st.data_editor(
    df, hide_index=True, width="stretch", disabled=["rut", "Estudiante"],
    column_config={"rut": None,
                   "Estado": st.column_config.SelectboxColumn("Estado", options=CODIGOS, required=True, help=AYUDA)},
    key=f"asis_{oferta_id}_{fecha}",
)
st.caption(AYUDA)

if st.button("Guardar asistencia", type="primary"):
    filas = [{"rut_estudiante": r.rut, "oferta_id": oferta_id, "fecha": fecha, "estado": r.Estado}
             for r in editado.itertuples()]
    try:
        sb.table("asistencia").upsert(filas, on_conflict="rut_estudiante,oferta_id,fecha").execute()
        sheets.tras_escritura(sb, ["asistencia"])
        st.success("Asistencia guardada.")
    except Exception as e:
        st.error(mensaje_error(e, "guardar la asistencia"))

with st.expander("📈 Porcentaje de asistencia y planilla del curso"):
    pct = tabla(sb, "v_asistencia_resumen", oferta_id=oferta_id)
    nombres = {a["rut"]: a["nombre_completo"] for a in alumnos}
    if not pct.empty:
        pct["Estudiante"] = pct["rut_estudiante"].map(nombres)
        res = pct[["Estudiante", "sesiones_registradas", "presentes", "ausentes", "justificadas", "suspendidas", "porcentaje"]]
        st.dataframe(renombrar(res), hide_index=True, width="stretch")
    todo = tabla(sb, "asistencia", "rut_estudiante, fecha, estado", oferta_id=oferta_id)
    if not todo.empty:
        todo["Estudiante"] = todo["rut_estudiante"].map(nombres)
        matriz = todo.pivot_table(index="Estudiante", columns="fecha", values="estado", aggfunc="first")
        matriz = matriz[sorted(matriz.columns)]
        matriz.columns = [pd.to_datetime(c).strftime("%d/%m") for c in matriz.columns]
        matriz = matriz.reset_index()
        st.dataframe(matriz, hide_index=True, width="stretch")
        boton_excel(matriz, "asistencia_curso", "xl_asis")
