"""Pagos (columnas de la planilla "Pagos Cursos de Idiomas"). Alimenta "Estudiantes pagados" por trigger."""
from datetime import date

import pandas as pd
import streamlit as st

from utils import drive, sheets
from utils.catalogos import catalogos, opciones
from utils.datos import clp, tabla
from utils.errores import mensaje_error
from utils.estilos import encabezado
from utils.excel import a_excel, renombrar
from utils.supabase_client import exigir_rol, get_client
from utils.validaciones import extension, normalizar_documento, validar_archivo

exigir_rol("coordinacion")
sb = get_client()
encabezado("Pagos", "Registro de pagos por curso. Al guardar, el alumno entra a «Estudiantes pagados».")

COLS_PLANILLA = ["n", "nombre", "banco", "rut", "fecha", "monto", "n_transaccion", "n_boleta", "forma_pago_nombre",
                 "n_cuota", "curso", "estado", "comprobante_drive_url"]
MESES = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
         9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}

# ======================================================================= Registrar pago
with st.expander("➕ Registrar pago", expanded=True):
    c1, c2 = st.columns([1, 2])
    tipo = c1.radio("Documento", ["RUT", "Pasaporte"], horizontal=True, key="pg_tipo")
    rut = normalizar_documento(c2.text_input("RUT o pasaporte del estudiante *", key="pg_rut"), tipo)
    est = sb.table("estudiante").select("rut, nombres, apellido_paterno, apellido_materno").eq("rut", rut).execute().data if rut else []
    if rut and not est:
        st.warning("No hay un estudiante con ese documento. Primero acepta su solicitud o regístralo en Estudiantes.")
    if est:
        e = est[0]
        st.markdown(f"**Nombre:** {e['nombres']} {e['apellido_paterno']} {e['apellido_materno'] or ''}")
        insc = (sb.table("inscripcion").select("oferta_id, forma_pago, monto_total")
                .eq("rut_estudiante", rut).eq("estado", "inscrito").execute().data)
        if insc:
            vo = {o["oferta_id"]: o for o in sb.table("v_oferta").select("oferta_id, etiqueta, periodo")
                  .in_("oferta_id", [i["oferta_id"] for i in insc]).execute().data}
            for i in insc:
                i["v_oferta"] = vo[i["oferta_id"]]
        if not insc:
            st.warning("El estudiante no tiene inscripciones vigentes.")
        else:
            ins_op = {i["v_oferta"]["etiqueta"]: i for i in insc}
            fp_op = opciones(sb, "forma_pago")
            pagado = tabla(sb, "estudiante_pagado", rut=rut)
            with st.form("nuevo_pago", clear_on_submit=True):
                curso = st.selectbox("Curso / oferta *", list(ins_op))
                i_sel = ins_op[curso]
                ya = pagado[pagado.oferta_id == i_sel["oferta_id"]] if not pagado.empty else pagado
                st.caption(f"Valor del curso: {clp(i_sel['monto_total'])} · Pagado: "
                           f"{clp(ya['monto_pagado'].iloc[0]) if not ya.empty else clp(0)}")
                c1, c2, c3 = st.columns(3)
                fecha = c1.date_input("Fecha *", date.today(), format="DD/MM/YYYY")
                monto = c2.number_input("Monto (CLP) *", min_value=0, step=1000)
                banco = c3.text_input("Banco", placeholder="Santander, Estado, Mercado Pago…")
                c1, c2, c3 = st.columns(3)
                n_tx = c1.text_input("N° de transacción")
                n_bol = c2.text_input("N° de boleta / código", placeholder="C9-1146")
                fp_def = list(fp_op.values()).index(i_sel["forma_pago"]) if i_sel.get("forma_pago") in fp_op.values() else 0
                forma = c3.selectbox("Forma de pago", list(fp_op), index=fp_def)
                c1, c2 = st.columns([1, 2])
                cuota = c1.number_input("N° de cuota", 1, 12, 1)
                obs = c2.text_input("Observación")
                comp = st.file_uploader("Comprobante (JPG, PNG o PDF, máx. 10 MB)", type=["jpg", "jpeg", "png", "pdf"])
                guardar = st.form_submit_button("Guardar pago", type="primary")
            if guardar:
                err = validar_archivo(comp, "el comprobante") if comp is not None else None
                if monto <= 0:
                    st.error("El monto debe ser mayor a 0.")
                elif err:
                    st.error(err)
                else:
                    try:
                        fila = {"rut_estudiante": rut, "oferta_id": i_sel["oferta_id"], "fecha": fecha.isoformat(),
                                "monto": int(monto), "banco": banco.strip() or None, "n_transaccion": n_tx.strip() or None,
                                "n_boleta": n_bol.strip() or None, "forma_pago": fp_op[forma], "n_cuota": int(cuota),
                                "observacion": obs.strip() or None,
                                "registrado_por": st.session_state.perfil["id"]}
                        pid = sb.table("pago").insert(fila).execute().data[0]["id"]
                        if comp is not None:
                            ext = extension(comp)
                            res = drive.subir_o_encolar(
                                comp.getvalue(), drive.nombre_archivo(rut, f"comprobante{int(cuota)}", ext), ext,
                                [drive.CARPETA_PAGOS, i_sel["v_oferta"]["periodo"]], {"tabla": "pago", "clave": {"id": pid}})
                            sb.table("pago").update({"comprobante_drive_file_id": res["drive_file_id"],
                                                     "comprobante_drive_url": res["drive_url"],
                                                     "comprobante_estado": res["estado"]}).eq("id", pid).execute()
                        sheets.tras_escritura(sb, ["pagos", "estudiantes_pagados", "convocatorias_ofertas"])
                        st.success("Pago registrado. El alumno ya está en «Estudiantes pagados» de este curso.")
                    except Exception as ex:
                        st.error(mensaje_error(ex, "guardar el pago"))

# ======================================================================= Planilla por proyecto/idioma
pagos = tabla(sb, "v_pago", orden="fecha")
if pagos.empty:
    st.info("Aún no hay pagos registrados.")
    st.stop()

ver_anulados = st.toggle("Mostrar pagos anulados", False)
if not ver_anulados:
    pagos = pagos[pagos.estado == "confirmado"]
idiomas = [i for i in [x["nombre"] for x in catalogos(sb).get("idioma") or []] if i in set(pagos.idioma_nombre)]

hojas = {}
tabs = st.tabs(idiomas) if idiomas else []
for tab, idioma in zip(tabs, idiomas):
    with tab:
        p = pagos[pagos.idioma_nombre == idioma].copy()
        codigo = p["codigo_proyecto"].iloc[0]
        marca = " ⚠️ por confirmar" if p["codigo_proyecto_por_confirmar"].iloc[0] else ""
        st.caption(f"Proyecto: **{codigo}**{marca}")
        bloques = []
        for mes, g in p.groupby("mes"):
            anio, m = map(int, mes.split("-"))
            st.markdown(f"**{MESES[m].capitalize()} {anio}** — Total: **{clp(g.loc[g.estado == 'confirmado', 'monto'].sum())}**")
            st.dataframe(renombrar(g[COLS_PLANILLA]), hide_index=True, width="stretch",
                         column_config={"Comprobante": st.column_config.LinkColumn("Comprobante", display_text="Ver")})
            bloques.append(g[COLS_PLANILLA])
            bloques.append(pd.DataFrame([{"n": f"Mes: {MESES[m]}", "nombre": "Total",
                                          "monto": g.loc[g.estado == "confirmado", "monto"].sum()}]))
        hojas[f"{codigo} {idioma}"] = pd.concat(bloques, ignore_index=True)

st.download_button("⬇️ Descargar planilla Excel (una hoja por proyecto)", a_excel(hojas),
                   file_name=f"pagos_cursos_idiomas_{date.today():%Y%m%d}.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ======================================================================= Anular
with st.expander("Anular un pago (se recalcula «Estudiantes pagados»)"):
    activos = pagos[pagos.estado == "confirmado"]
    if activos.empty:
        st.caption("No hay pagos confirmados.")
    else:
        pid = st.selectbox("Pago", activos["id"].tolist(), format_func=lambda i: "{} · {} · {}".format(
            *activos.loc[activos.id == i, ["nombre", "fecha", "monto"]].iloc[0]))
        motivo = st.text_input("Motivo de la anulación *")
        if st.button("Anular pago"):
            try:
                sb.rpc("anular_pago", {"p_id": int(pid), "p_motivo": motivo}).execute()
                sheets.tras_escritura(sb, ["pagos", "estudiantes_pagados"])
                st.rerun()
            except Exception as ex:
                st.error(mensaje_error(ex, "anular el pago"))
