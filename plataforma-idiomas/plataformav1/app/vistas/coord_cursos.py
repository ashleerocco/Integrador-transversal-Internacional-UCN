"""Cursos: convocatorias, ofertas y docentes (coordinación).

Abrir una convocatoria basta para que sus ofertas aparezcan en el inicio público,
en el formulario y en el Resumen (vistas `ofertas_publicas` y `v_inscritos_vs_minimo`);
no se copian datos a mano.
"""
from datetime import date, time

import pandas as pd
import streamlit as st

from utils import sheets
from utils.catalogos import nombres, opciones
from utils.datos import DIAS, clp, horario, tabla
from utils.errores import mensaje_error
from utils.estilos import encabezado
from utils.excel import boton_excel, renombrar
from utils.supabase_client import exigir_rol, get_client
from utils.validaciones import documento_valido, normalizar_documento

exigir_rol("coordinacion")
sb = get_client()
encabezado("Cursos", "Convocatorias, ofertas de cursos y docentes")

ESTADOS_CONV = {"borrador": "Borrador", "abierta": "Abierta", "cerrada": "Cerrada"}
ESTADOS_OFERTA = {"abierta": "Abierta", "confirmada": "Confirmada", "no_se_dicta": "No se dicta", "finalizada": "Finalizada"}
PRECIOS_REF = {"ucn": 190000, "egresado_funcionario": 210000, "externo": 220000}


def enviar_acceso(rut: str):
    """Invita al docente (o le reenvía el acceso) con la Edge Function «invitar-docente».

    La invitación la envía Supabase con la service role key DENTRO de la función;
    la app solo manda la sesión de la coordinación, que la función verifica.
    Devuelve (tipo_de_mensaje, texto) para mostrarlo con st.success / st.error.
    """
    try:
        datos = sb.functions.invoke("invitar-docente", invoke_options={"body": {"rut": rut}, "responseType": "json"})
        if datos.get("modo") == "recuperacion":
            return "success", f"{datos['correo']} ya tenía cuenta: se le envió un correo para crear una nueva contraseña."
        return "success", (f"Invitación enviada a {datos.get('correo')}. Debe usar el código del correo en "
                           "«¿Primera vez o olvidaste tu contraseña?» de la pantalla de inicio.")
    except Exception as e:  # FunctionsHttpError trae en .message el «error» que devuelve la función
        return "error", f"No se pudo enviar el acceso. {getattr(e, 'message', '')}".strip()


def refrescar(pestanas=("convocatorias_ofertas",)):
    sheets.tras_escritura(sb, list(pestanas))
    st.rerun()


tab_conv, tab_ofertas, tab_doc = st.tabs(["Convocatorias", "Ofertas de cursos", "Docentes"])

# =========================================================================== Convocatorias
with tab_conv:
    convs = tabla(sb, "convocatoria", orden="fecha_apertura", desc=True)
    if not convs.empty:
        vista = convs[["id", "nombre", "periodo", "estado", "fecha_apertura", "fecha_cierre", "fecha_confirmacion",
                       "fecha_inicio_curso", "fecha_fin_curso"]].copy()
        vista["estado"] = vista["estado"].map(ESTADOS_CONV)
        st.dataframe(renombrar(vista), hide_index=True, width="stretch")
        boton_excel(vista, "convocatorias", "xl_conv")

    lista = {"➕ Nueva convocatoria": None} | {f"{r.nombre} ({r.periodo})": r.id for r in convs.itertuples()} \
        if not convs.empty else {"➕ Nueva convocatoria": None}
    sel = st.selectbox("Crear o editar", list(lista), key="conv_sel")
    actual = convs[convs.id == lista[sel]].iloc[0].to_dict() if lista[sel] else {}

    with st.form("form_conv"):
        c1, c2 = st.columns([2, 1])
        nombre = c1.text_input("Nombre *", actual.get("nombre", f"Cursos Idiomas PIE-UCN 1-{date.today().year}"))
        periodo = c2.text_input("Período * (ej. 1-2026)", actual.get("periodo", f"1-{date.today().year}"))
        d = lambda c, defecto=None: date.fromisoformat(actual[c]) if actual.get(c) else defecto  # noqa: E731
        c1, c2, c3 = st.columns(3)
        f_ap = c1.date_input("Apertura de inscripciones *", d("fecha_apertura", date.today()), format="DD/MM/YYYY")
        f_ci = c2.date_input("Cierre de inscripciones *", d("fecha_cierre", date.today()), format="DD/MM/YYYY")
        f_conf = c3.date_input("Confirmación de cursos (e-mail)", d("fecha_confirmacion"), format="DD/MM/YYYY")
        c1, c2 = st.columns(2)
        f_ini = c1.date_input("Inicio de clases", d("fecha_inicio_curso"), format="DD/MM/YYYY")
        f_fin = c2.date_input("Fin de clases", d("fecha_fin_curso"), format="DD/MM/YYYY")
        estado = st.selectbox("Estado", list(ESTADOS_CONV), format_func=ESTADOS_CONV.get,
                              index=list(ESTADOS_CONV).index(actual.get("estado", "borrador")),
                              help="Al ABRIR, sus ofertas aparecen en el inicio público y en el Resumen. Al CERRAR, dejan de mostrarse.")
        guardar = st.form_submit_button("Guardar convocatoria", type="primary")

    if guardar:
        errores = []
        if not nombre.strip() or not periodo.strip():
            errores.append("Completa nombre y período.")
        if f_ci < f_ap:
            errores.append("El cierre debe ser igual o posterior a la apertura.")
        if f_ini and f_fin and f_fin < f_ini:
            errores.append("El fin de clases debe ser posterior al inicio.")
        if errores:
            st.error("\n".join(f"- {e}" for e in errores))
        else:
            fila = {"nombre": nombre.strip(), "periodo": periodo.strip(), "fecha_apertura": f_ap.isoformat(),
                    "fecha_cierre": f_ci.isoformat(), "fecha_confirmacion": f_conf.isoformat() if f_conf else None,
                    "fecha_inicio_curso": f_ini.isoformat() if f_ini else None,
                    "fecha_fin_curso": f_fin.isoformat() if f_fin else None, "estado": estado}
            try:
                if lista[sel]:
                    sb.table("convocatoria").update(fila).eq("id", lista[sel]).execute()
                else:
                    sb.table("convocatoria").insert(fila).execute()
                st.toast("Convocatoria guardada")
                refrescar()
            except Exception as e:
                st.error(mensaje_error(e, "guardar la convocatoria"))

    # Al cerrar: marcar cada oferta "confirmada" o "no se dicta"
    if actual and actual.get("estado") == "cerrada":
        st.subheader("Cierre: confirmar o descartar cursos")
        v = pd.DataFrame(sb.table("v_inscritos_vs_minimo").select("*").eq("periodo", actual["periodo"])
                         .eq("convocatoria", actual["nombre"]).execute().data)
        if v.empty:
            st.info("Esta convocatoria no tiene ofertas.")
        else:
            v["sugerencia"] = v["alcanza_minimo"].map({True: "confirmada", False: "no_se_dicta"})
            st.dataframe(renombrar(v[["oferta_id", "curso", "inscritos", "cupo_minimo", "estado_oferta", "sugerencia"]]),
                         hide_index=True, width="stretch")
            c1, c2, c3 = st.columns([2, 1, 1])
            of_sel = c1.selectbox("Oferta", v["curso"].tolist(), key="cierre_of")
            fila = v[v.curso == of_sel].iloc[0]
            if c2.button("✅ Confirmada", key="cierre_ok"):
                sb.table("oferta").update({"estado": "confirmada"}).eq("id", int(fila.oferta_id)).execute()
                refrescar()
            if c3.button("⛔ No se dicta", key="cierre_no"):
                sb.table("oferta").update({"estado": "no_se_dicta"}).eq("id", int(fila.oferta_id)).execute()
                refrescar()
            if st.button("Aplicar la sugerencia a todas (según el mínimo)"):
                for r in v.itertuples():
                    sb.table("oferta").update({"estado": r.sugerencia}).eq("id", int(r.oferta_id)).execute()
                refrescar()

# =========================================================================== Ofertas
with tab_ofertas:
    convs = tabla(sb, "convocatoria", "id, nombre, periodo, estado", orden="fecha_apertura", desc=True)
    if convs.empty:
        st.info("Primero crea una convocatoria.")
    else:
        ofs = tabla(sb, "v_oferta", orden="oferta_id", desc=True)
        valores = tabla(sb, "oferta_valor")
        if not ofs.empty:
            filtro = st.multiselect("Filtrar por convocatoria", convs["nombre"].tolist(), key="of_filtro")
            vista = ofs[ofs.convocatoria.isin(filtro)] if filtro else ofs
            vista = vista.assign(horario=vista.apply(lambda r: horario(r.to_dict()), axis=1),
                                 estado=vista["estado"].map(ESTADOS_OFERTA))
            cols = ["oferta_id", "convocatoria", "idioma_nombre", "nivel", "modalidad", "sede_nombre", "horario",
                    "docente", "cupo_minimo", "cupo_maximo", "valor_universal", "estado"]
            st.dataframe(renombrar(vista[cols]), hide_index=True, width="stretch")
            boton_excel(vista[cols], "ofertas", "xl_ofertas")

        lista = {"➕ Nueva oferta": None} | ({r.etiqueta: r.oferta_id for r in ofs.itertuples()} if not ofs.empty else {})
        sel = st.selectbox("Crear o editar", list(lista), key="of_sel")
        act = ofs[ofs.oferta_id == lista[sel]].iloc[0].to_dict() if lista[sel] else {}
        vals_act = {r.categoria_precio: r.valor for r in valores.itertuples()
                    if lista[sel] and r.oferta_id == lista[sel]} if not valores.empty else {}

        docentes = tabla(sb, "docente", "rut, nombres, apellidos, activo", orden="apellidos")
        doc_op = {"(sin asignar)": None} | ({f"{r.nombres} {r.apellidos}": r.rut for r in docentes.itertuples() if r.activo}
                                             if not docentes.empty else {})
        conv_op = {f"{r.nombre} ({r.periodo})": r.id for r in convs.itertuples()}
        idi_op, sede_op = opciones(sb, "idioma"), opciones(sb, "sede") or {"Antofagasta": "antofagasta",
                                                                           "Coquimbo": "coquimbo", "Virtual": "virtual"}
        cat_nom = nombres(sb, "categoria_precio")
        idx = lambda op, val: list(op.values()).index(val) if val in op.values() else 0  # noqa: E731

        with st.form("form_oferta"):
            c1, c2, c3 = st.columns(3)
            conv_n = c1.selectbox("Convocatoria *", list(conv_op), index=idx(conv_op, act.get("convocatoria_id")))
            idi_n = c2.selectbox("Idioma *", list(idi_op), index=idx(idi_op, act.get("idioma")))
            nivel = c3.text_input("Nivel *", act.get("nivel", ""), placeholder="Básico A1, Intermedio B1.1, A1.1, Preparación TOEFL")
            c1, c2, c3 = st.columns(3)
            modalidad = c1.selectbox("Modalidad *", ["Presencial", "Virtual"],
                                     index=["Presencial", "Virtual"].index(act.get("modalidad", "Presencial")))
            sede_n = c2.selectbox("Sede *", list(sede_op), index=idx(sede_op, act.get("sede")))
            doc_n = c3.selectbox("Docente", list(doc_op), index=idx(doc_op, act.get("rut_docente")))
            c1, c2, c3 = st.columns([2, 1, 1])
            dias = c1.multiselect("Días", list(DIAS), default=list(act.get("dias") or []), format_func=DIAS.get)
            h_ini = c2.time_input("Hora inicio", time.fromisoformat(act["hora_inicio"]) if act.get("hora_inicio") else time(19, 45))
            h_fin = c3.time_input("Hora término", time.fromisoformat(act["hora_fin"]) if act.get("hora_fin") else time(21, 15))
            horario_txt = st.text_input("Horario en texto (opcional, reemplaza días/horas en el formulario)",
                                        act.get("horario_texto") or "", placeholder="a convenir lunes, jueves y viernes")
            c1, c2, c3 = st.columns(3)
            cmin = c1.number_input("Cupo mínimo *", 1, 100, int(act.get("cupo_minimo", 5)))
            cmax = c2.number_input("Cupo máximo *", 1, 100, int(act.get("cupo_maximo", 10)))
            estado = c3.selectbox("Estado", list(ESTADOS_OFERTA), format_func=ESTADOS_OFERTA.get,
                                  index=list(ESTADOS_OFERTA).index(act.get("estado", "abierta")))
            st.markdown("**Valores (CLP)** — si fijas un valor único, aplica a todos los vínculos (p. ej. cursos virtuales $190.000, TOEFL $260.000).")
            unico = st.checkbox("Valor único para todos", value=act.get("valor_universal") is not None and not pd.isna(act.get("valor_universal")))
            c0, c1, c2, c3 = st.columns(4)
            v_uni = c0.number_input("Valor único", 0, 5_000_000, int(act["valor_universal"]) if unico and act.get("valor_universal") else 190000, 5000)
            v_cat = {}
            for col, cat in zip((c1, c2, c3), PRECIOS_REF):
                v_cat[cat] = col.number_input(cat_nom.get(cat, cat)[:40], 0, 5_000_000, int(vals_act.get(cat, PRECIOS_REF[cat])), 5000)
            guardar = st.form_submit_button("Guardar oferta", type="primary")

        if guardar:
            if not nivel.strip():
                st.error("Indica el nivel.")
            elif cmax < cmin:
                st.error("El cupo máximo debe ser mayor o igual al mínimo.")
            elif not horario_txt.strip() and h_fin <= h_ini:
                st.error("La hora de término debe ser posterior a la de inicio.")
            else:
                fila = {"convocatoria_id": conv_op[conv_n], "idioma": idi_op[idi_n], "nivel": nivel.strip(),
                        "modalidad": modalidad, "sede": sede_op[sede_n], "rut_docente": doc_op[doc_n],
                        "dias": sorted(dias), "hora_inicio": h_ini.isoformat(), "hora_fin": h_fin.isoformat(),
                        "horario_texto": horario_txt.strip() or None, "cupo_minimo": int(cmin), "cupo_maximo": int(cmax),
                        "estado": estado, "valor_universal": int(v_uni) if unico else None}
                try:
                    if lista[sel]:
                        oid = lista[sel]
                        sb.table("oferta").update(fila).eq("id", oid).execute()
                    else:
                        oid = sb.table("oferta").insert(fila).execute().data[0]["id"]
                    sb.table("oferta_valor").upsert([{"oferta_id": oid, "categoria_precio": c, "valor": int(v)}
                                                     for c, v in v_cat.items()]).execute()
                    st.toast("Oferta guardada")
                    refrescar()
                except Exception as e:
                    st.error(mensaje_error(e, "guardar la oferta"))

# =========================================================================== Docentes
def mostrar(msg):
    if msg:
        getattr(st, msg[0])(msg[1])


def cambiar_activo(rut: str, nombre: str, activo: bool):
    """Activar/desactivar: desactivado pierde el acceso al instante (RLS revisa docente.activo)."""
    try:
        sb.table("docente").update({"activo": activo}).eq("rut", rut).execute()
        texto = f"{nombre} quedó {'activo' if activo else 'inactivo'}."
        if not activo:
            texto += " Ya no puede ingresar a la plataforma; sus datos y registros se conservan."
        st.session_state.msg_docentes = ("success", texto)
        refrescar(["docentes"])
    except Exception as e:
        st.error(mensaje_error(e, "cambiar el estado del docente"))


with tab_doc:
    mostrar(st.session_state.pop("msg_docentes", None))
    docentes = tabla(sb, "docente", orden="apellidos")
    cols = ["rut", "nombres", "apellidos", "correo", "telefono"]
    activos = docentes[docentes.activo] if not docentes.empty else docentes
    inactivos = docentes[~docentes.activo] if not docentes.empty else docentes
    ofertas_doc = tabla(sb, "oferta", "rut_docente") if not docentes.empty else pd.DataFrame()
    cursos_por_docente = ofertas_doc.rut_docente.value_counts() if not ofertas_doc.empty else pd.Series(dtype=int)

    st.markdown(f"**Docentes activos** ({len(activos)})")
    if activos.empty:
        st.caption("No hay docentes activos.")
    else:
        st.dataframe(renombrar(activos[cols]), hide_index=True, width="stretch")
        boton_excel(activos[cols], "docentes_activos", "xl_docentes")

    with st.form("form_docente", clear_on_submit=True):
        st.markdown("**Agregar o actualizar docente** (el RUT es su identificador)")
        c1, c2 = st.columns([1, 2])
        tipo = c1.radio("Documento", ["RUT", "Pasaporte"], horizontal=True)
        doc = c2.text_input("RUT o pasaporte *")
        c1, c2 = st.columns(2)
        nom = c1.text_input("Nombres *")
        ape = c2.text_input("Apellidos *")
        c1, c2 = st.columns(2)
        correo = c1.text_input("Correo (el mismo de su usuario de la plataforma)")
        tel = c2.text_input("Teléfono")
        c1, c2 = st.columns(2)
        activo = c1.checkbox("Activo", True, help="Desmarcar quita el acceso del docente a la plataforma.")
        invitar = c2.checkbox("Enviar acceso por correo al guardar", True,
                              help="El docente recibe un correo para crear su contraseña.")
        ok = st.form_submit_button("Guardar docente", type="primary")
    if ok:
        rut = normalizar_documento(doc, tipo)
        if not (nom.strip() and ape.strip()) or not documento_valido(rut, tipo):
            st.error("Completa nombres y apellidos e ingresa un RUT/pasaporte válido.")
        else:
            try:
                sb.table("docente").upsert({"rut": rut, "tipo_documento": tipo, "nombres": nom.strip(),
                                            "apellidos": ape.strip(), "correo": correo.strip().lower() or None,
                                            "telefono": tel.strip() or None, "activo": activo}).execute()
                msg = ("success", "Docente guardado.")
                if invitar and activo and correo.strip():
                    msg = enviar_acceso(rut)  # antes de recargar la página (si no, nunca se enviaba)
                st.session_state.msg_docentes = msg
                refrescar(["docentes"])
            except Exception as e:
                st.error(mensaje_error(e, "guardar el docente"))

    # Acceso de los docentes activos: enviar (o reenviar) el acceso, o desactivar la cuenta
    if not activos.empty:
        st.markdown("**Acceso a la plataforma**")
        op_act = {f"{r.nombres} {r.apellidos} · {r.correo if pd.notna(r.correo) and r.correo else '(sin correo)'}": r.rut for r in activos.itertuples()}
        c1, c2, c3 = st.columns([3, 1, 1], vertical_alignment="bottom")
        sel_act = c1.selectbox("Docente", list(op_act), key="acceso_docente")
        rut_act = op_act[sel_act]
        nombre_act = sel_act.split(" · ")[0]
        sin_correo = sel_act.endswith("(sin correo)")
        if c2.button("Enviar acceso", icon=":material/mail:", width="stretch", disabled=sin_correo,
                     help="Registra su correo para poder enviarle el acceso." if sin_correo else None):
            mostrar(enviar_acceso(rut_act))
        with c3.popover("Desactivar", icon=":material/person_off:", width="stretch"):
            st.markdown(f"¿Desactivar a **{nombre_act}**?")
            n_cursos = int(cursos_por_docente.get(rut_act, 0))
            aviso = ("Pierde de inmediato el acceso a la plataforma. Sus datos, asistencias y notas se conservan "
                     "y pasa a «Docentes inactivos».")
            if n_cursos:
                aviso += f" Tiene {n_cursos} curso(s) asignado(s): reasígnalos en «Ofertas de cursos»."
            st.caption(aviso)
            if st.button("Sí, desactivar", type="primary", key="confirmar_desactivar", width="stretch"):
                cambiar_activo(rut_act, nombre_act, False)

    # Docentes inactivos: sin acceso; se pueden volver a activar
    st.divider()
    st.markdown(f"**Docentes inactivos** ({len(inactivos)})")
    if inactivos.empty:
        st.caption("No hay docentes inactivos.")
    else:
        st.caption("No pueden ingresar a la plataforma. Sus datos y lo que registraron se conservan.")
        st.dataframe(renombrar(inactivos[cols]), hide_index=True, width="stretch")
        boton_excel(inactivos[cols], "docentes_inactivos", "xl_docentes_inactivos")
        op_ina = {f"{r.nombres} {r.apellidos} · {r.correo if pd.notna(r.correo) and r.correo else '(sin correo)'}": r.rut for r in inactivos.itertuples()}
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        sel_ina = c1.selectbox("Docente inactivo", list(op_ina), key="reactivar_docente")
        if c2.button("Reactivar", icon=":material/person_check:", width="stretch",
                     help="Vuelve a tener acceso con su misma cuenta y contraseña."):
            cambiar_activo(op_ina[sel_ina], sel_ina.split(" · ")[0], True)
