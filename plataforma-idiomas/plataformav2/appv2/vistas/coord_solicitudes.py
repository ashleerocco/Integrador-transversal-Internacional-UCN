"""Solicitudes del formulario público (adaptado de v1: el archivo antiguo no tenía extensión .py)."""
import pandas as pd
import streamlit as st

from utils import drive, sheets
from utils.catalogos import nombres
from utils.datos import ofertas_opciones, tabla
from utils.errores import mensaje_error
from utils.estilos import encabezado
from utils.excel import boton_excel, renombrar
from utils.supabase_client import exigir_rol, get_client

exigir_rol("coordinacion")
sb = get_client()
encabezado("Solicitudes de inscripción", "Pre-inscripciones recibidas desde el formulario público")

if drive.pendientes():
    st.warning(f"Hay {drive.pendientes()} documento(s) en cola para subir a Drive.")
    if st.button("Reintentar subidas ahora"):
        ok, mal = drive.reintentar_pendientes(sb)
        st.toast(f"Subidos {ok}, fallidos {mal}")

ESTADOS = {"pendiente": "Pendientes", "aceptada": "Aceptadas", "rechazada": "Rechazadas"}
estado = st.radio("Mostrar", list(ESTADOS), format_func=ESTADOS.get, horizontal=True)
df = tabla(sb, "v_solicitud", estado=estado, orden="creado_en", desc=True)

if df.empty:
    st.info("No hay solicitudes en este estado.")
    st.stop()

c1, c2, c3 = st.columns(3)
f_idioma = c1.multiselect("Idioma", sorted(df["idioma_nombre"].unique()))
f_oferta = c2.multiselect("Curso", sorted(df["curso"].fillna("Otro (a convenir)").unique()))
f_vinc = c3.multiselect("Vínculo", sorted(df["vinculo_nombre"].unique()))
if f_idioma:
    df = df[df.idioma_nombre.isin(f_idioma)]
if f_oferta:
    df = df[df.curso.fillna("Otro (a convenir)").isin(f_oferta)]
if f_vinc:
    df = df[df.vinculo_nombre.isin(f_vinc)]
df = df.reset_index(drop=True)

cols = ["codigo", "creado_en", "nombre_completo", "rut", "correo", "idioma_nombre", "curso", "otro_idioma_nivel",
        "vinculo_nombre", "forma_pago_nombre"]
st.caption(f"{len(df)} solicitud(es). Marca filas para aceptar en lote.")
sel = st.dataframe(renombrar(df[cols]), hide_index=True, width="stretch",
                   on_select="rerun", selection_mode="multi-row", key="tabla_sol")
boton_excel(df[cols + ["telefono", "campus_nombre", "carrera", "nacionalidad", "cedula_drive_url", "licencia_drive_url",
                       "motivo_rechazo"]], "solicitudes", "xl_sol")


def aceptar(id_: int, oferta_id=None) -> str | None:
    try:
        sb.rpc("aceptar_solicitud", {"p_id": int(id_), "p_oferta_id": oferta_id}).execute()
        return None
    except Exception as e:
        return mensaje_error(e, "aceptar la solicitud")


filas = sel.selection.rows if sel and sel.selection else []
if estado == "pendiente" and filas:
    if st.button(f"✅ Aceptar {len(filas)} seleccionada(s)", type="primary"):
        errores = []
        for i in filas:
            err = aceptar(df.loc[i, "id"])
            if err:
                errores.append(f"{df.loc[i, 'codigo']}: {err}")
        sheets.tras_escritura(sb, ["solicitudes", "estudiantes", "convocatorias_ofertas"])
        if errores:
            st.error("Algunas no se aceptaron:\n" + "\n".join(f"- {e}" for e in errores))
        else:
            st.rerun()

# ---------------------------------------------------------------- detalle
st.divider()
codigo = st.selectbox("Ver detalle de la solicitud", df["codigo"].tolist(),
                      format_func=lambda c: f"{c} — {df.loc[df.codigo == c, 'nombre_completo'].iloc[0]}")
s = df[df.codigo == codigo].iloc[0].to_dict()
det = nombres(sb, "vinculo_detalle")

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"""
**Nombre registral:** {s['nombre_completo']}
**Nombre social / pronombres:** {s.get('nombre_social') or '—'} · {s['pronombres']}
**{s['tipo_documento']}:** {s['rut']}
**Fecha de nacimiento:** {pd.to_datetime(s['fecha_nacimiento']).strftime('%d/%m/%Y')}
**Sexo / género:** {s['sexo']} · {s['genero']}
**Nacionalidad:** {s['nacionalidad']}
**Correo / teléfono:** {s['correo']} · {s.get('telefono') or '—'}
""")
with c2:
    st.markdown(f"""
**Curso:** {s.get('curso') or 'Otro (a convenir): ' + str(s.get('otro_idioma_nivel'))}
**Modalidad:** {s['modalidad']}
**Vínculo:** {s['vinculo_nombre']}{' — ' + det.get(s['vinculo_detalle'], '') if s.get('vinculo_detalle') else ''}
**Carrera / unidad / profesión:** {s['carrera']}
**Campus:** {s.get('campus_nombre') or '—'}{': ' + s['campus_otro'] if s.get('campus_otro') else ''}
**Forma de pago:** {s['forma_pago_nombre']}
**Condición de salud:** {'Sí — ' + str(s['salud_requerimiento']) if s['salud_tiene_condicion'] else 'No'}
""")

c1, c2 = st.columns(2)
for col, pref, etq in ((c1, "cedula", "Documento de identidad"), (c2, "licencia", "Licencia E. Media / título")):
    with col:
        if s.get(f"{pref}_drive_url"):
            st.link_button(f"📄 {etq} (Drive)", s[f"{pref}_drive_url"])
        else:
            st.caption(f"{etq}: pendiente de subir a Drive")

if s["estado"] == "rechazada":
    st.info(f"Motivo del rechazo: {s.get('motivo_rechazo')}")
elif s["estado"] == "pendiente":
    oferta_id = None
    if not s.get("oferta_id"):
        ops = ofertas_opciones(sb, solo_activas=True)
        elegido = st.selectbox("Curso al que se inscribirá *", list(ops), index=None)
        oferta_id = ops.get(elegido)
    c1, c2 = st.columns(2)
    if c1.button("✅ Aceptar", type="primary", key="acep_uno"):
        err = aceptar(s["id"], oferta_id)
        if err:
            st.error(err)
        else:
            sheets.tras_escritura(sb, ["solicitudes", "estudiantes", "convocatorias_ofertas"])
            st.rerun()
    with c2.popover("❌ Rechazar"):
        motivo = st.text_area("Motivo *")
        if st.button("Confirmar rechazo"):
            try:
                sb.rpc("rechazar_solicitud", {"p_id": int(s["id"]), "p_motivo": motivo}).execute()
                sheets.tras_escritura(sb, ["solicitudes", "convocatorias_ofertas"])
                st.rerun()
            except Exception as e:
                st.error(mensaje_error(e, "rechazar la solicitud"))
