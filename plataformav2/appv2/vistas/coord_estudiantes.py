"""Estudiantes: todos, pagados, registro (formulario compartido) y edición."""
import pandas as pd
import streamlit as st

from utils import drive, sheets
from utils.catalogos import PAISES, opciones
from utils.datos import tabla
from utils.errores import mensaje_error
from utils.estilos import encabezado
from utils.excel import boton_excel, renombrar
from utils.formulario_inscripcion import render_formulario_inscripcion
from utils.supabase_client import exigir_rol, get_client
from utils.validaciones import correo_valido, extension, telefono_valido, validar_archivo

exigir_rol("coordinacion")
sb = get_client()
encabezado("Estudiantes", "Ficha única por RUT: se ingresa una vez y se reutiliza en cada curso")

if st.session_state.get("fc_mensaje"):
    st.success(st.session_state.pop("fc_mensaje"))

t_todos, t_pagados, t_nuevo, t_editar = st.tabs(
    ["👥 Todos los estudiantes", "💳 Estudiantes pagados", "➕ Registrar estudiante", "✏️ Editar datos"])
ofertas = tabla(sb, "v_oferta", "oferta_id, etiqueta", orden="oferta_id", desc=True)
ofertas_map = dict(zip(ofertas.etiqueta, ofertas.oferta_id)) if not ofertas.empty else {}


def filtros(df: pd.DataFrame, clave: str, col_curso: str | None = None) -> pd.DataFrame:
    c1, c2, c3, c4 = st.columns(4)
    f_v = c1.multiselect("Vínculo UCN", sorted(df["vinculo_nombre"].dropna().unique()), key=f"{clave}_v")
    f_g = c2.multiselect("Género", sorted(df["genero"].dropna().unique()), key=f"{clave}_g")
    f_c = c3.multiselect("Campus", sorted(df["campus_nombre"].replace("", "Sin campus").fillna("Sin campus").unique()),
                         key=f"{clave}_c")
    f_o = c4.multiselect("Curso", list(ofertas_map), key=f"{clave}_o")
    if f_v:
        df = df[df.vinculo_nombre.isin(f_v)]
    if f_g:
        df = df[df.genero.isin(f_g)]
    if f_c:
        df = df[df.campus_nombre.replace("", "Sin campus").fillna("Sin campus").isin(f_c)]
    if f_o:
        ids = {ofertas_map[o] for o in f_o}
        if col_curso == "oferta_id":
            df = df[df.oferta_id.isin(ids)]
        else:
            df = df[df.ofertas.apply(lambda xs: bool(set(xs or []) & ids))]
    return df


# ======================================================================= Todos
with t_todos:
    est = tabla(sb, "v_estudiante", orden="creado_en", desc=True)
    if est.empty:
        st.info("Aún no hay estudiantes registrados.")
    else:
        buscar = st.text_input("Buscar por nombre, RUT o correo", key="buscar")
        df = filtros(est, "todos")
        if buscar:
            b = buscar.strip().lower()
            df = df[df[["nombre_completo", "rut", "correo", "nombre_social"]].fillna("").apply(
                lambda c: c.str.lower().str.contains(b, regex=False)).any(axis=1)]
        st.caption(f"{len(df)} estudiante(s)")
        cols = ["rut", "nombre_completo", "nombre_social", "correo", "telefono", "vinculo_nombre", "genero",
                "campus_nombre", "carrera", "nacionalidad", "edad", "cursos"]
        st.dataframe(renombrar(df[cols]), hide_index=True, width="stretch")
        boton_excel(df[cols + ["sexo", "fecha_nacimiento", "pronombres", "vinculo_detalle_nombre",
                               "salud_tiene_condicion", "salud_requerimiento", "cedula_url", "licencia_url"]],
                    "estudiantes", "xl_est")

        with st.expander("📎 Documentos adjuntos de un estudiante"):
            rut = st.selectbox("Estudiante", df["rut"].tolist(), index=None,
                               format_func=lambda r: f"{df.loc[df.rut == r, 'nombre_completo'].iloc[0]} ({r})")
            if rut:
                docs = tabla(sb, "documento_estudiante", rut_estudiante=rut)
                for d in docs.to_dict("records"):
                    etq = "Documento de identidad" if d["tipo"] == "cedula" else "Licencia E. Media / título"
                    if d.get("drive_file_id"):
                        c1, c2 = st.columns(2)
                        c1.link_button(f"Abrir {etq} en Drive", d["drive_url"])
                        clave_dl = f"bytes_{rut}_{d['tipo']}"
                        if drive.configurado() and clave_dl not in st.session_state:
                            if c2.button(f"Preparar descarga de {etq}", key=f"dl_{d['tipo']}"):
                                st.session_state[clave_dl] = drive.descargar(d["drive_file_id"])
                                st.rerun()
                        elif clave_dl in st.session_state:
                            c2.download_button("⬇️ Guardar archivo", st.session_state[clave_dl],
                                               file_name=d.get("nombre_archivo") or f"{rut}_{d['tipo']}",
                                               key=f"dl2_{d['tipo']}", on_click="ignore")
                    else:
                        st.caption(f"{etq}: pendiente de subir.")
                if docs.empty:
                    st.caption("Sin documentos registrados.")

# ======================================================================= Pagados
with t_pagados:
    pag = tabla(sb, "v_estudiante_pagado", orden="curso")
    if pag.empty:
        st.info("Nadie ha pagado todavía. Un estudiante aparece aquí al registrar su primer pago en «Pagos».")
    else:
        df = filtros(pag, "pag", col_curso="oferta_id")
        st.caption(f"{len(df)} estudiante(s) pagado(s)")
        cols = ["rut", "nombre_completo", "curso", "vinculo_nombre", "genero", "campus_nombre", "monto_total",
                "monto_pagado", "saldo", "estado_pago", "fecha_primer_pago"]
        st.dataframe(renombrar(df[cols]), hide_index=True, width="stretch")
        boton_excel(df[cols], "estudiantes_pagados", "xl_pag")

# ======================================================================= Registrar
with t_nuevo:
    st.caption("Mismo formulario que el público. Se guarda directo como estudiante aceptado e inscrito.")
    render_formulario_inscripcion(sb, modo="coordinacion")

# ======================================================================= Editar
with t_editar:
    est = tabla(sb, "estudiante", orden="apellido_paterno")
    if est.empty:
        st.info("Aún no hay estudiantes.")
    else:
        rut = st.selectbox("Estudiante", est["rut"].tolist(), index=None, key="ed_rut",
                           format_func=lambda r: "{} {} ({})".format(*est.loc[est.rut == r, ["nombres", "apellido_paterno"]].iloc[0], r))
        if rut:
            e = est[est.rut == rut].iloc[0].to_dict()
            vinc, det, camp = opciones(sb, "vinculo_ucn"), opciones(sb, "vinculo_detalle"), opciones(sb, "campus")
            idx = lambda op, v: list(op.values()).index(v) if v in op.values() else None  # noqa: E731
            with st.form("editar"):
                c1, c2 = st.columns(2)
                correo = c1.text_input("Correo", e["correo"])
                tel = c2.text_input("Teléfono", e.get("telefono") or "")
                c1, c2 = st.columns(2)
                social = c1.text_input("Nombre social", e.get("nombre_social") or "")
                pron = c2.text_input("Pronombres", e.get("pronombres") or "")
                carrera = st.text_input("Carrera / unidad / profesión", e.get("carrera") or "")
                c1, c2, c3 = st.columns(3)
                v_n = c1.selectbox("Vínculo", list(vinc), index=idx(vinc, e["vinculo"]))
                d_n = c2.selectbox("Detalle (si es «Otros»)", list(det), index=idx(det, e.get("vinculo_detalle")))
                c_n = c3.selectbox("Campus", list(camp), index=idx(camp, e.get("campus")))
                nac = st.selectbox("Nacionalidad", PAISES, index=PAISES.index(e["nacionalidad"]) if e["nacionalidad"] in PAISES else len(PAISES) - 1)
                st.markdown("**Reemplazar documentos (opcional)**")
                c1, c2 = st.columns(2)
                ced = c1.file_uploader("Documento de identidad", type=["jpg", "jpeg", "png", "pdf"])
                lic = c2.file_uploader("Licencia E. Media / título", type=["jpg", "jpeg", "png", "pdf"])
                ok = st.form_submit_button("Guardar cambios", type="primary")
            if ok:
                errores = []
                if not correo_valido(correo):
                    errores.append("Correo no válido.")
                if tel and not telefono_valido(tel):
                    errores.append("Teléfono no válido.")
                if not v_n:
                    errores.append("Indica el vínculo.")
                elif vinc.get(v_n) == "otros" and not d_n:
                    errores.append("Especifica el detalle del vínculo «Otros».")
                for arch, etq in ((ced, "el documento de identidad"), (lic, "la licencia")):
                    if arch is not None and (err := validar_archivo(arch, etq)):
                        errores.append(err)
                if errores:
                    st.error("\n".join(f"- {x}" for x in errores))
                else:
                    try:
                        sb.table("estudiante").update({
                            "correo": correo.strip().lower(), "telefono": tel.strip() or None,
                            "nombre_social": social.strip() or None, "pronombres": pron.strip() or None,
                            "carrera": carrera.strip() or None, "vinculo": vinc[v_n],
                            "vinculo_detalle": det.get(d_n) if vinc[v_n] == "otros" else None,
                            "campus": camp.get(c_n), "nacionalidad": nac}).eq("rut", rut).execute()
                        for arch, tipo in ((ced, "cedula"), (lic, "licencia")):
                            if arch is None:
                                continue
                            ext = extension(arch)
                            res = drive.subir_o_encolar(arch.getvalue(), drive.nombre_archivo(rut, tipo, ext), ext,
                                                        [drive.CARPETA_DOCS, rut],
                                                        {"tabla": "documento_estudiante", "clave": {"rut_estudiante": rut, "tipo": tipo}})
                            sb.table("documento_estudiante").upsert({
                                "rut_estudiante": rut, "tipo": tipo, "drive_file_id": res["drive_file_id"],
                                "drive_url": res["drive_url"], "nombre_archivo": drive.nombre_archivo(rut, tipo, ext),
                                "estado_archivo": res["estado"]}).execute()
                        sheets.tras_escritura(sb, ["estudiantes", "estudiantes_pagados"])
                        st.success("Datos actualizados.")
                    except Exception as ex:
                        st.error(mensaje_error(ex, "actualizar el estudiante"))
