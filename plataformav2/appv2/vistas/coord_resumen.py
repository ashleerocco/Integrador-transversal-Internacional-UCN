"""Resumen (reciclado de v1 + vínculos, pagos, asistencia, certificados, sync y respaldo)."""
from datetime import date

import pandas as pd
import streamlit as st

from utils import drive, sheets
from utils.datos import clp, tabla
from utils.estilos import VIOLETA, encabezado
from utils.excel import a_excel, boton_excel, renombrar
from utils.supabase_client import exigir_rol, get_client

exigir_rol("coordinacion")
sb = get_client()
encabezado("Resumen general")

est = tabla(sb, "v_estudiante", "rut, vinculo_nombre, genero, campus_nombre")
pagados = tabla(sb, "estudiante_pagado", "rut, oferta_id, monto_pagado, monto_total, estado_pago")
pagos = tabla(sb, "v_pago", "monto, mes, idioma_nombre, estado")
pend = sb.table("solicitud").select("id", count="exact").eq("estado", "pendiente").limit(1).execute().count or 0
confirmados = pagos[pagos.estado == "confirmado"] if not pagos.empty else pagos

c1, c2, c3, c4 = st.columns(4)
c1.metric("Estudiantes registrados", len(est))
c2.metric("Solicitudes pendientes", pend)
c3.metric("Estudiantes pagados (curso)", len(pagados))
c4.metric("Recaudado", clp(confirmados["monto"].sum() if not confirmados.empty else 0))

# ---------------------------------------------------------------- inscritos vs mínimo (v1)
st.subheader("Inscritos frente al mínimo para abrir el curso")
v = tabla(sb, "v_inscritos_vs_minimo", orden="oferta_id")
if v.empty:
    st.info("No hay convocatorias abiertas o cerradas con ofertas.")
else:
    conv = st.multiselect("Convocatoria", sorted(v["convocatoria"].unique()),
                          default=sorted(v.loc[v.estado_convocatoria == "abierta", "convocatoria"].unique()))
    vv = v[v.convocatoria.isin(conv)] if conv else v
    cols = ["curso", "estado_oferta", "inscritos", "solicitudes_pendientes", "pagados", "cupo_minimo", "cupo_maximo",
            "faltan", "alcanza_minimo"]
    st.dataframe(renombrar(vv[cols]), hide_index=True, width="stretch",
                 column_config={"Alcanza minimo": st.column_config.CheckboxColumn("Alcanza mínimo")})
    boton_excel(vv[cols], "inscritos_vs_minimo", "xl_ivm")
    st.bar_chart(vv.set_index("curso")[["inscritos", "cupo_minimo"]], color=[VIOLETA, "#FFAD0C"], stack=False)

# ---------------------------------------------------------------- vínculo / género / campus
st.subheader("Estudiantes por vínculo UCN")
if est.empty:
    st.info("Aún no hay estudiantes.")
else:
    c1, c2 = st.columns(2)
    c1.bar_chart(est["vinculo_nombre"].value_counts(), color=VIOLETA, horizontal=True)
    c2.bar_chart(est["genero"].fillna("Sin dato").value_counts(), color="#DB4ED2", horizontal=True)

# ---------------------------------------------------------------- pagos
st.subheader("Pagos")
if confirmados.empty:
    st.info("Aún no hay pagos registrados.")
else:
    por_mes = confirmados.pivot_table(index="mes", columns="idioma_nombre", values="monto", aggfunc="sum").fillna(0)
    st.bar_chart(por_mes)
    if not pagados.empty:
        c1, c2 = st.columns(2)
        c1.metric("Pago total", int((pagados.estado_pago == "total").sum()))
        c2.metric("Pago parcial", int((pagados.estado_pago == "parcial").sum()))

# ---------------------------------------------------------------- asistencia
st.subheader("Asistencia promedio por curso")
asis = tabla(sb, "v_asistencia_resumen", "oferta_id, porcentaje")
ofs = tabla(sb, "v_oferta", "oferta_id, etiqueta")
if asis.empty or asis["porcentaje"].isna().all():
    st.info("Aún no hay asistencia registrada.")
else:
    a = asis.dropna().groupby("oferta_id")["porcentaje"].mean().round(1).reset_index().merge(ofs, on="oferta_id")
    st.bar_chart(a.set_index("etiqueta")["porcentaje"], color="#00DBAD", horizontal=True)

# ---------------------------------------------------------------- certificados
st.subheader("Estado de certificados")
certs = tabla(sb, "certificado", "estado")
if certs.empty:
    st.info("Aún no hay certificados en proceso.")
else:
    orden = ["solicitado", "pendiente", "firmado", "entregado"]
    cuenta = certs["estado"].value_counts().reindex(orden, fill_value=0)
    cols = st.columns(4)
    for col, (estado, n) in zip(cols, cuenta.items()):
        col.metric(estado.capitalize(), int(n))

# ---------------------------------------------------------------- sync, Drive pendiente y respaldo
st.divider()
st.subheader("Respaldo y sincronización")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**Google Sheets (espejo)**")
    if not sheets.configurado():
        st.caption("Sin configurar (falta SHEETS_ID o la cuenta de servicio).")
    errores = sheets.pestanas_con_error(sb)
    if errores:
        st.warning("Pestañas con error pendiente: " + ", ".join(errores))
    if st.button("🔄 Sincronizar ahora", disabled=not sheets.configurado()):
        with st.spinner("Sincronizando…"):
            res = sheets.sincronizar_ahora(sb)
        malos = [p for p, r in res.items() if r != "ok"]
        (st.error if malos else st.success)(
            f"Fallaron: {', '.join(malos)} (quedó registrado en sync_log)" if malos else "Hoja actualizada.")
with c2:
    st.markdown("**Archivos pendientes de subir a Drive**")
    n = drive.pendientes()
    st.caption(f"{n} archivo(s) en cola.")
    if st.button("⬆️ Reintentar subidas", disabled=n == 0):
        ok, mal = drive.reintentar_pendientes(sb)
        st.success(f"Subidos: {ok}. Fallidos: {mal}.")
with c3:
    st.markdown("**Respaldo completo (Excel)**")
    if st.button("Preparar respaldo"):
        with st.spinner("Generando…"):
            libro = {p: sheets.leer(sb, p) for p in sheets.ESPEJO}
            st.session_state.respaldo = a_excel(libro)
    if st.session_state.get("respaldo"):
        st.download_button("⬇️ Descargar respaldo", st.session_state.respaldo,
                           file_name=f"respaldo_idiomas_{date.today():%Y%m%d}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
