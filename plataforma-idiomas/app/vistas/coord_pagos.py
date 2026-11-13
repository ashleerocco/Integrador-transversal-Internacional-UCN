import streamlit as st
import pandas as pd
from datetime import date
import uuid
from utils.supabase_client import get_client
from utils.estilos import encabezado
from utils.datos import inscripciones_etiquetadas, nombre_completo, etiqueta_curso
from utils.exportar import boton_descarga

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
            banco = st.text_input("Banco (opcional)")
            obs = st.text_input("Observación (opcional)")
            comprobante = st.file_uploader(
                "Comprobante de pago (PDF, JPG, JPEG o PNG; máximo 5 MB)",
                type=["pdf", "jpg", "jpeg", "png"],
            )
            guardar = st.form_submit_button("Guardar pago")
        if guardar:
            errores = []
            if comprobante:
                extension = comprobante.name.rsplit(".", 1)[-1].lower() if "." in comprobante.name else ""
                tipos_mime = {"pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}
                if extension not in tipos_mime or (comprobante.type and comprobante.type != tipos_mime.get(extension)):
                    errores.append("El comprobante debe ser un archivo PDF, JPG, JPEG o PNG válido.")
                if comprobante.size > 5 * 1024 * 1024:
                    errores.append("El comprobante supera el tamaño máximo de 5 MB.")
            if errores:
                for error in errores:
                    st.error(error)
            else:
                ruta_comprobante = None
                if comprobante:
                    extension = comprobante.name.rsplit(".", 1)[-1].lower()
                    ruta_comprobante = f"pagos/{uuid.uuid4().hex}/comprobante.{extension}"
            try:
                if not errores:
                    if comprobante:
                        sb.storage.from_("comprobantes_pago").upload(
                            ruta_comprobante, comprobante.getvalue(),
                            {"content-type": comprobante.type, "upsert": "false"},
                        )
                    sb.table("pago").insert({
                        "inscripcion_id": opciones[insc],
                        "monto": int(monto),
                        "estado": estado,
                        "fecha_pago": fecha.isoformat() if estado == "pagado" else None,
                        "banco": banco.strip() or None,
                        "observacion": obs or None,
                        "comprobante_path": ruta_comprobante,
                    }).execute()
                    st.success("Pago registrado con su comprobante." if comprobante else "Pago registrado.")
            except Exception:
                if comprobante and ruta_comprobante:
                    try:
                        sb.storage.from_("comprobantes_pago").remove([ruta_comprobante])
                    except Exception:
                        pass
                st.error("No se pudo guardar el pago o su comprobante. Inténtalo nuevamente.")

pagos = sb.table("pago").select(
    "id, monto, fecha_pago, estado, banco, comprobante_path, "
    "inscripcion(estudiante(nombres, apellido_paterno), oferta_curso(periodo, curso(nombre)))"
).order("id", desc=True).execute().data

filas = [{
    "ID": p["id"],
    "Estudiante": nombre_completo(p["inscripcion"]["estudiante"]),
    "Curso": etiqueta_curso(p["inscripcion"]["oferta_curso"]),
    "Monto": p["monto"],
    "Fecha": p["fecha_pago"],
    "Estado": p["estado"],
    "Banco": p.get("banco"),
    "Comprobante": "✅" if p.get("comprobante_path") else "❌",
} for p in pagos]

if filas:
    df = pd.DataFrame(filas)
    filtro = st.multiselect("Filtrar por estado", ["pendiente", "pagado", "devuelto"])
    if filtro:
        df = df[df["Estado"].isin(filtro)]
    boton_descarga(df, "pagos", "Pagos", key="export_pagos")
    st.dataframe(df, hide_index=True, use_container_width=True)

    ids_visibles = set(df["ID"].tolist())
    pagos_con_comprobante = [p for p in pagos if p["id"] in ids_visibles and p.get("comprobante_path")]
    if pagos_con_comprobante:
        st.subheader("Comprobantes adjuntos")
        opciones_comprobantes = {
            f"Pago {p['id']} · {nombre_completo(p['inscripcion']['estudiante'])} · {etiqueta_curso(p['inscripcion']['oferta_curso'])}": p
            for p in pagos_con_comprobante
        }
        comprobante_seleccionado = st.selectbox(
            "Selecciona un comprobante para ver o descargar",
            list(opciones_comprobantes), key="pago_comprobante_seleccionado",
        )
        pago_seleccionado = opciones_comprobantes[comprobante_seleccionado]
        if st.button("Generar acceso temporal (60 segundos)", key=f"crear_url_pago_{pago_seleccionado['id']}"):
            try:
                respuesta = sb.storage.from_("comprobantes_pago").create_signed_url(
                    pago_seleccionado["comprobante_path"], 60,
                )
                url = respuesta.get("signedURL") or respuesta.get("signedUrl")
                if url:
                    st.session_state["url_comprobante_pago"] = (pago_seleccionado["id"], url)
                else:
                    st.error("No se pudo generar el acceso temporal al comprobante.")
            except Exception:
                st.error("No se pudo abrir el comprobante. Inténtalo nuevamente.")
        acceso = st.session_state.get("url_comprobante_pago")
        if acceso and acceso[0] == pago_seleccionado["id"]:
            st.link_button("Ver / descargar comprobante", acceso[1])
    elif not df.empty:
        st.info("Los pagos visibles no tienen comprobantes adjuntos.")

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
