import streamlit as st
import pandas as pd
from datetime import date
from utils.supabase_client import get_client
from utils.estilos import encabezado
from utils.datos import inscripciones_etiquetadas, nombre_completo, etiqueta_curso

sb = get_client()
encabezado("Pagos")  # RF-07

with st.expander("➕ Registrar pago"):
    opciones = inscripciones_etiquetadas(sb)
    if not opciones:
        st.info("No hay inscripciones registradas.")
    else:
        with st.form("nuevo_pago", clear_on_submit=True):
            insc = st.selectbox("Inscripción", list(opciones))
            monto = st.number_input("Monto (CLP)", min_value=0, step=1000)
            estado = st.selectbox("Estado", ["pendiente", "pagado", "devuelto"])
            fecha = st.date_input("Fecha de pago", value=date.today())
            obs = st.text_input("Observación (opcional)")
            guardar = st.form_submit_button("Guardar pago")
        if guardar:
            try:
                sb.table("pago").insert({
                    "inscripcion_id": opciones[insc],
                    "monto": int(monto),
                    "estado": estado,
                    "fecha_pago": fecha.isoformat() if estado == "pagado" else None,
                    "observacion": obs or None,
                }).execute()
                st.success("Pago registrado.")
            except Exception as e:
                st.error(f"No se pudo guardar: {e}")

pagos = sb.table("pago").select(
    "id, monto, fecha_pago, estado, "
    "inscripcion(estudiante(nombres, apellido_paterno), oferta_curso(periodo, curso(nombre)))"
).order("id", desc=True).execute().data

filas = [{
    "ID": p["id"],
    "Estudiante": nombre_completo(p["inscripcion"]["estudiante"]),
    "Curso": etiqueta_curso(p["inscripcion"]["oferta_curso"]),
    "Monto": p["monto"],
    "Fecha": p["fecha_pago"],
    "Estado": p["estado"],
} for p in pagos]

if filas:
    df = pd.DataFrame(filas)
    filtro = st.multiselect("Filtrar por estado", ["pendiente", "pagado", "devuelto"])
    if filtro:
        df = df[df["Estado"].isin(filtro)]
    st.dataframe(df, hide_index=True, use_container_width=True)

    st.subheader("Cambiar estado de un pago")
    c1, c2, c3 = st.columns([2, 2, 1])
    pid = c1.selectbox("Pago (ID)", [f["ID"] for f in filas])
    nuevo = c2.selectbox("Nuevo estado", ["pendiente", "pagado", "devuelto"])
    if c3.button("Actualizar"):
        cambios = {"estado": nuevo}
        if nuevo == "pagado":
            cambios["fecha_pago"] = date.today().isoformat()
        sb.table("pago").update(cambios).eq("id", pid).execute()
        st.rerun()
else:
    st.info("Aún no hay pagos registrados.")
