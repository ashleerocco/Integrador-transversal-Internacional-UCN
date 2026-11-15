"""Certificados: Solicitado → Pendiente → Firmado → Entregado.

Solo aparecen alumnos pagados con las 3 notas y nota final (vista v_certificable).
Las fechas se fijan en la BD (trigger) al cambiar de estado; volver atrás exige confirmación.
"""
import pandas as pd
import streamlit as st

from utils import drive, sheets
from utils.datos import ofertas_opciones, tabla
from utils.errores import mensaje_error
from utils.estilos import encabezado
from utils.excel import boton_excel, renombrar
from utils.supabase_client import exigir_rol, get_client
from utils.validaciones import validar_archivo

exigir_rol("coordinacion")
sb = get_client()
encabezado("Certificados", "Seguimiento desde la solicitud hasta la entrega")

ESTADOS = ["solicitado", "pendiente", "firmado", "entregado"]
NOMBRE = {None: "Sin solicitar", "solicitado": "Solicitado", "pendiente": "Pendiente", "firmado": "Firmado",
          "entregado": "Entregado"}

df = tabla(sb, "v_certificable", orden="curso")
if df.empty:
    st.info("Aún no hay alumnos con las 3 notas y la nota final ingresadas.")
    st.stop()
df["estado"] = df["estado"].astype(object).apply(lambda v: v if isinstance(v, str) else None)

c1, c2 = st.columns(2)
cursos = c1.multiselect("Curso", sorted(df["curso"].unique()))
estados = c2.multiselect("Estado", list(NOMBRE.values()))
if cursos:
    df = df[df.curso.isin(cursos)]
if estados:
    df = df[df.estado.map(lambda e: NOMBRE.get(e if isinstance(e, str) else None)).isin(estados)]
df = df.reset_index(drop=True)

vista = df.assign(estado=df.estado.map(lambda e: NOMBRE.get(e if isinstance(e, str) else None)))
cols = ["rut", "nombre_completo", "curso", "nota_final", "asistencia", "estado", "fecha_solicitada", "fecha_pendiente",
        "fecha_firma", "fecha_entrega", "drive_url"]
sel = st.dataframe(renombrar(vista[cols]), hide_index=True, width="stretch", on_select="rerun",
                   selection_mode="multi-row", key="t_cert",
                   column_config={"Archivo": st.column_config.LinkColumn("Archivo", display_text="PDF")})
boton_excel(vista[cols], "certificados", "xl_cert")


def cambiar(rut, oferta_id, estado, file_id=None, url=None, retro=False):
    sb.rpc("cambiar_estado_certificado", {"p_rut": rut, "p_oferta_id": int(oferta_id), "p_estado": estado,
                                          "p_drive_file_id": file_id, "p_drive_url": url,
                                          "p_confirmar_retroceso": retro}).execute()


filas = sel.selection.rows if sel and sel.selection else []
sin_solicitar = [i for i in filas if not isinstance(df.loc[i, "estado"], str)]
if sin_solicitar and st.button(f"Marcar {len(sin_solicitar)} como «Solicitado»", type="primary"):
    try:
        for i in sin_solicitar:
            cambiar(df.loc[i, "rut"], df.loc[i, "oferta_id"], "solicitado")
        sheets.tras_escritura(sb, ["certificados"])
        st.rerun()
    except Exception as e:
        st.error(mensaje_error(e, "actualizar los certificados"))

# ---------------------------------------------------------------- un alumno
st.divider()
idx = st.selectbox("Gestionar certificado de", df.index.tolist(),
                   format_func=lambda i: f"{df.loc[i, 'nombre_completo']} — {df.loc[i, 'curso']}")
c = df.loc[idx].to_dict()
actual = c["estado"] if isinstance(c["estado"], str) else None
n_actual = ESTADOS.index(actual) + 1 if actual else 0
st.markdown(" → ".join(f"**{NOMBRE[e]}**" if e == actual else NOMBRE[e] for e in ESTADOS))
st.progress(n_actual / 4)

if actual != "entregado" and n_actual >= 2:
    pdf = st.file_uploader("PDF del certificado firmado (obligatorio para «Entregado»)", type=["pdf"], key=f"pdf_{idx}")
else:
    pdf = None

c1, c2 = st.columns(2)
if n_actual < 4:
    siguiente = ESTADOS[n_actual]
    if c1.button(f"Avanzar a «{NOMBRE[siguiente]}»", type="primary"):
        try:
            file_id = url = None
            if siguiente == "entregado":
                if c.get("drive_file_id") is None and pdf is None:
                    st.error("Sube el PDF del certificado antes de marcarlo «Entregado».")
                    st.stop()
                if pdf is not None:
                    if err := validar_archivo(pdf, "el certificado"):
                        st.error(err)
                        st.stop()
                    res = drive.subir(pdf.getvalue(), drive.nombre_archivo(c["rut"], "certificado", "pdf"), "pdf",
                                      [drive.CARPETA_CERTIFICADOS, c["curso"]])
                    file_id, url = res["drive_file_id"], res["drive_url"]
            cambiar(c["rut"], c["oferta_id"], siguiente, file_id, url)
            sheets.tras_escritura(sb, ["certificados"])
            st.rerun()
        except RuntimeError:
            st.error("Drive no está disponible en este momento. El estado no cambió; inténtalo de nuevo.")
        except Exception as e:
            st.error(mensaje_error(e, "cambiar el estado"))

if pdf is not None and n_actual >= 2 and c2.button("Solo subir el PDF (sin cambiar estado)"):
    if err := validar_archivo(pdf, "el certificado"):
        st.error(err)
    else:
        try:
            res = drive.subir(pdf.getvalue(), drive.nombre_archivo(c["rut"], "certificado", "pdf"), "pdf",
                              [drive.CARPETA_CERTIFICADOS, c["curso"]])
            cambiar(c["rut"], c["oferta_id"], actual, res["drive_file_id"], res["drive_url"])
            st.success("PDF guardado.")
        except Exception as e:
            st.error(mensaje_error(e, "subir el certificado"))

if n_actual >= 2:
    with st.expander("Corregir: volver a un estado anterior"):
        anterior = st.selectbox("Volver a", ESTADOS[: n_actual - 1], format_func=NOMBRE.get)
        conf = st.checkbox(f"Confirmo que quiero volver de «{NOMBRE[actual]}» a «{NOMBRE[anterior]}» "
                           "(se borrarán las fechas posteriores)")
        if st.button("Aplicar corrección", disabled=not conf):
            try:
                cambiar(c["rut"], c["oferta_id"], anterior, retro=True)
                sheets.tras_escritura(sb, ["certificados"])
                st.rerun()
            except Exception as e:
                st.error(mensaje_error(e, "corregir el estado"))
