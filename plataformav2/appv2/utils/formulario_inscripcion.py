"""Formulario de inscripción ÚNICO (público y coordinación).

Replica el Google Form "Cursos Idiomas PIE-UCN 1-2026" en el mismo orden.
- modo="publico": sin login; guarda en `solicitud` (estado pendiente).
- modo="coordinacion": mismos campos y validaciones; guarda directo como
  estudiante + inscripción (origen = coordinacion) vía `idiomas.inscribir_estudiante`.

No se usa `st.form`: así los selectores dependientes (idioma -> modalidad -> oferta,
vínculo -> campus/detalle, salud -> requerimiento) se actualizan en vivo. Todas las
claves de widget llevan un prefijo + versión para poder limpiar el formulario.
"""
from __future__ import annotations

import secrets as _secrets
from datetime import date, datetime, timezone

import streamlit as st

from utils import drive, sheets
from utils.catalogos import PAISES, catalogos, categoria_precio, config, opciones, vinculo_es_ucn
from utils.datos import clp, horario
from utils.errores import mensaje_error
from utils.estilos import encabezado
from utils.validaciones import (correo_valido, documento_valido, extension, fecha_nacimiento_valida,
                                normalizar_documento, telefono_valido, validar_archivo)

OTRO = "Otro (a convenir)"
MAX_ENVIOS_SESION = 3
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]


def _fecha_larga(f) -> str:
    if not f:
        return "—"
    f = date.fromisoformat(f) if isinstance(f, str) else f
    return f"{f.day} de {MESES[f.month - 1]} de {f.year}"


# ---------------------------------------------------------------------------
# Datos de ofertas/convocatorias (mismo formato en ambos modos)
# ---------------------------------------------------------------------------
def _ofertas(sb, modo: str) -> list[dict]:
    if modo == "publico":
        return sb.rpc("ofertas_publicas").execute().data or []
    data = (sb.table("v_oferta").select("oferta_id, convocatoria_id, idioma, idioma_nombre, nivel, modalidad, sede, "
                                        "sede_nombre, dias, hora_inicio, hora_fin, horario_texto, valor_universal, estado")
            .in_("estado", ["abierta", "confirmada"]).execute().data)
    valores = sb.table("oferta_valor").select("*").execute().data
    for o in data:
        o["valores"] = {v["categoria_precio"]: v["valor"] for v in valores if v["oferta_id"] == o["oferta_id"]}
    return data


def _convocatorias(sb, modo: str) -> dict[int, dict]:
    if modo == "publico":
        data = sb.rpc("convocatorias_publicas").execute().data or []
    else:
        data = sb.table("convocatoria").select("*").execute().data
    return {c["id"]: c for c in data}


def _texto_valor(o: dict, cat_precio: dict[str, str], categoria: str | None = None) -> str:
    if o.get("valor_universal") is not None:
        return clp(o["valor_universal"])
    vals = o.get("valores") or {}
    if categoria and categoria in vals:
        return clp(vals[categoria])
    return " / ".join(f"{cat_precio.get(k, k).split('/')[0]} {clp(v)}" for k, v in vals.items()) or "valor por confirmar"


def _etiqueta_oferta(o: dict, cat_precio, categoria=None) -> str:
    return f"{o['idioma_nombre']} {o['nivel']} · {o['sede_nombre']} · {horario(o)} · {_texto_valor(o, cat_precio, categoria)}"


# ---------------------------------------------------------------------------
def render_formulario_inscripcion(sb, modo: str = "publico") -> None:
    assert modo in ("publico", "coordinacion")
    pref = "fp" if modo == "publico" else "fc"
    ver = st.session_state.setdefault(f"{pref}_version", 0)
    k = lambda nombre: f"{pref}{ver}_{nombre}"  # noqa: E731

    if modo == "publico" and st.session_state.get(f"{pref}_confirmacion"):
        _confirmacion(st.session_state[f"{pref}_confirmacion"], pref)
        return

    try:
        cat = catalogos(sb)
        ofertas = _ofertas(sb, modo)
        convs = _convocatorias(sb, modo)
    except Exception as e:
        st.error(mensaje_error(e, "cargar los cursos disponibles"))
        return

    cat_precio = {c["codigo"]: c["nombre"] for c in cat.get("categoria_precio") or []}
    correo_contacto = config(sb, "correo_contacto", "idiomas.pie@ucn.cl")

    # ------------------------------------------------------------------ A
    if modo == "publico":
        encabezado("Inscríbete en un curso de idiomas", "Completa el formulario; no necesitas crear una cuenta")
        st.info(
            f"**{config(sb, 'cabecera_formulario', '')}**\n\n{config(sb, 'cabecera_detalle', '')}\n\n"
            f"Consultas: {correo_contacto} · Web: {config(sb, 'web', '')} · "
            f"[Agenda una cita informativa virtual]({config(sb, 'calendly_url', '')})"
        )
        st.caption("* Indica que la pregunta es obligatoria")
        # Honeypot anti-spam: invisible para personas, los bots lo llenan
        st.markdown(f"<style>.st-key-{k('web_hp')} {{display:none !important}}</style>", unsafe_allow_html=True)
        st.text_input("Sitio web (no completar)", key=k("web_hp"), label_visibility="collapsed")

    # ------------------------------------------------------------------ B
    st.markdown("#### Contacto y curso")
    correo = st.text_input("1. Correo *", key=k("correo"))
    idiomas_op = opciones(sb, "idioma")
    idioma_nom = st.selectbox("2. Curso de interés (idioma) *", list(idiomas_op), index=None,
                              placeholder="Elige un idioma", key=k("idioma"))
    modalidad = st.radio("3. Modalidad *", ["Presencial", "Virtual"], index=None, horizontal=True, key=k("modalidad"),
                         format_func=lambda m: "Virtual (con docente en vivo)" if m == "Virtual" else m)
    st.caption("Cursos grupales sujetos a confirmación de la cantidad mínima de participantes por nivel.")

    idioma = idiomas_op.get(idioma_nom)
    disponibles = [o for o in ofertas if o["idioma"] == idioma and o["modalidad"] == modalidad]
    mapa_ofertas = {_etiqueta_oferta(o, cat_precio): o for o in disponibles}
    oferta_sel = st.selectbox(
        "4. Curso/nivel y horario *", list(mapa_ofertas) + [OTRO], index=None, key=k("oferta"),
        placeholder="Elige primero idioma y modalidad" if not (idioma and modalidad) else "Selecciona una opción",
        disabled=not (idioma and modalidad),
        help="Las opciones salen de los cursos abiertos en la convocatoria vigente.")
    if idioma and modalidad and not disponibles:
        st.caption("No hay cursos abiertos con ese idioma y modalidad: puedes elegir «Otro (a convenir)».")
    oferta = mapa_ofertas.get(oferta_sel)
    otro_txt = ""
    if oferta_sel == OTRO:
        otro_txt = st.text_input("5. Idioma y nivel que te interesa *", key=k("otro"))

    # ------------------------------------------------------------------ C
    st.markdown("#### Información personal")
    st.caption("Comparte información completa y documentos que acrediten tu identidad y, como mínimo, "
               "estudios de Enseñanza Media o superior.")
    c1, c2, c3 = st.columns(3)
    nombres = c1.text_input("6. Nombres (registral) *", key=k("nombres"))
    ap_pat = c2.text_input("7. Apellido paterno *", key=k("ap_pat"))
    ap_mat = c3.text_input("8. Apellido materno *", key=k("ap_mat"))
    c1, c2 = st.columns(2)
    sexo = c1.radio("9. Sexo (registral) *", ["Hombre", "Mujer", "Prefiero no decirlo"], index=None, key=k("sexo"))
    genero = c2.radio("10. Género *", ["Femenino", "Masculino", "Otro"], index=None, key=k("genero"))
    nombre_social = st.text_input(
        "11. Nombre social (opcional)", key=k("social"),
        help="Si no te identificas con tu nombre registral, ¿hay algún nombre social con el que desees que te llamen?")
    pronombres = st.text_input("12. ¿Con qué pronombres deseas que te llamen? *", key=k("pron"))
    c1, c2 = st.columns([1, 2])
    tipo_doc = c1.radio("13. Tipo de documento *", ["RUT", "Pasaporte"], horizontal=True, key=k("tipo_doc"))
    doc_txt = c2.text_input("RUT o N° de pasaporte *", key=k("doc"),
                            placeholder="12345678-5" if tipo_doc == "RUT" else "Ej: AB1234567")
    fnac = st.date_input("14. Fecha de nacimiento *", value=None, min_value=date(1900, 1, 1),
                         max_value=date.today(), format="DD/MM/YYYY", key=k("fnac"))

    cedula = st.file_uploader(
        "15. Copia simple del documento de identificación * (foto o PDF, máx. 10 MB)",
        type=["jpg", "jpeg", "png", "pdf"], key=k("cedula"),
        help="En la cédula de identidad chilena, borra el N° de documento.")
    st.caption("En la cédula chilena, **borra el N° de documento** antes de adjuntarla.")
    if cedula is not None and cedula.type.startswith("image/") and cedula.size <= 10 * 1024 * 1024:
        st.image(cedula, width=260, caption="Vista previa")
    licencia = st.file_uploader(
        "16. Copia simple de Licencia de Enseñanza Media o Enseñanza Superior (título) * (máx. 10 MB)",
        type=["jpg", "jpeg", "png", "pdf"], key=k("licencia"))
    st.caption(f"Puedes descargar tu licencia o título aquí: {config(sb, 'mineduc_url', '')}")
    if licencia is not None and licencia.type.startswith("image/") and licencia.size <= 10 * 1024 * 1024:
        st.image(licencia, width=260, caption="Vista previa")

    carrera = st.text_input("17. Carrera, Unidad UCN o Profesión *", key=k("carrera"))

    # 18-20: el campus depende del vínculo (20); se muestra en el orden del formulario
    vinc_op = opciones(sb, "vinculo_ucn")
    det_op = opciones(sb, "vinculo_detalle")
    vinc_actual = vinc_op.get(st.session_state.get(k("vinculo")))
    det_actual = det_op.get(st.session_state.get(k("vinc_det")))
    campus_oblig = bool(vinc_actual) and vinculo_es_ucn(sb, vinc_actual, det_actual)
    campus_op = opciones(sb, "campus")
    campus_nom = st.selectbox(f"18. Campus UCN{' *' if campus_oblig else ''}", list(campus_op), index=None,
                              key=k("campus"), placeholder="Selecciona tu campus",
                              help="Obligatorio si tu vínculo es con la UCN.")
    campus = campus_op.get(campus_nom)
    campus_otro = st.text_input("Especifica el campus *", key=k("campus_otro")) if campus == "otro" else ""
    nacionalidad = st.selectbox("19. Nacionalidad *", PAISES, index=0, key=k("nac"))
    nac_otra = st.text_input("Especifica tu nacionalidad *", key=k("nac_otra")) if nacionalidad == "Otro" else ""

    vinculo_nom = st.selectbox("20. Vínculo con UCN *", list(vinc_op), index=None, key=k("vinculo"),
                               placeholder="Selecciona tu vínculo")
    vinculo = vinc_op.get(vinculo_nom)
    detalle = None
    if vinculo == "otros":
        det_nom = st.selectbox("Especifica tu vínculo * (el valor del curso depende de esto)", list(det_op),
                               index=None, key=k("vinc_det"))
        detalle = det_op.get(det_nom)
    if vinculo and oferta and (vinculo != "otros" or detalle):
        st.caption(f"Valor del curso para tu vínculo: **{_texto_valor(oferta, cat_precio, categoria_precio(sb, vinculo, detalle))}**")

    telefono = st.text_input("21. Teléfono", key=k("tel"), placeholder="+56 9 1234 5678")
    salud = st.radio("22. ¿Hay alguna condición de salud física, mental u otra que desees compartir? *",
                     ["Sí", "No"], index=None, horizontal=True, key=k("salud"))
    salud_req = ""
    if salud == "Sí":
        salud_req = st.text_area("¿Existe algún requerimiento? *", key=k("salud_req"))
    st.caption("🔒 Esta información se trata con confidencialidad y solo la ve la coordinación.")

    # ------------------------------------------------------------------ D
    st.markdown("#### Forma de pago y consideraciones")
    conv = convs.get((oferta or {}).get("convocatoria_id")) or (next(iter(convs.values())) if convs else {})
    cuotas = conv.get("fechas_cuotas") or []
    fp_op = opciones(sb, "forma_pago")
    fp_etq = {n: (f"{n} ({', '.join(_fecha_larga(c) for c in cuotas)})" if c == "tres_cuotas" and cuotas else n)
              for n, c in fp_op.items()}
    forma_nom = st.radio("23. Forma de pago *", list(fp_op), index=None, key=k("forma"), format_func=fp_etq.get)
    st.markdown(
        f"""<div style="background:#F5F2F9;border-radius:12px;padding:12px 16px;font-size:.95rem">
        <b>24. Consideraciones</b><br>
        • Mínimo de 5 participantes y máximo 10 participantes por nivel.<br>
        • La confirmación del curso será vía e-mail el <b>{_fecha_larga(conv.get('fecha_confirmacion'))}</b>,
          siempre y cuando se cumpla el cupo mínimo.<br>
        • La primera cuota se paga <b>ANTES</b> de iniciar el curso y <b>solo una vez confirmado</b>, enviando copia
          de la transferencia a {correo_contacto}. Los datos de transferencia se entregan al confirmar el curso.
          Por favor, no transfieras si el curso no está confirmado.<br>
        • Duración: {_fecha_larga(conv.get('fecha_inicio_curso'))} al {_fecha_larga(conv.get('fecha_fin_curso'))}.
        </div>""", unsafe_allow_html=True)
    terminos = st.checkbox("25. He leído los términos y condiciones del curso *", key=k("terminos"))
    consentimiento = st.checkbox(
        "26. Autorizo el tratamiento de mis datos personales, incluidos los documentos adjuntos y la información "
        "de salud, para gestionar mi inscripción en los cursos de idiomas de la UCN *", key=k("consent"))

    etiqueta_boton = "Enviar inscripción" if modo == "publico" else "Guardar estudiante"
    if not st.button(etiqueta_boton, type="primary", key=k("enviar")):
        return

    # ------------------------------------------------------------------ Validación (todos los errores juntos)
    errores = []
    if not correo_valido(correo or ""):
        errores.append("1. Ingresa un correo válido.")
    if not idioma:
        errores.append("2. Elige el idioma.")
    if not modalidad:
        errores.append("3. Elige la modalidad.")
    if not oferta_sel:
        errores.append("4. Elige el curso/nivel y horario.")
    if oferta_sel == OTRO and not otro_txt.strip():
        errores.append("5. Indica el idioma y nivel que te interesa.")
    for n, v, etq in ((6, nombres, "tus nombres"), (7, ap_pat, "el apellido paterno"), (8, ap_mat, "el apellido materno")):
        if not (v or "").strip():
            errores.append(f"{n}. Ingresa {etq}.")
    if not sexo:
        errores.append("9. Indica el sexo registral.")
    if not genero:
        errores.append("10. Indica el género.")
    if not (pronombres or "").strip():
        errores.append("12. Indica tus pronombres.")
    doc = normalizar_documento(doc_txt, tipo_doc)
    if not doc:
        errores.append("13. Ingresa tu RUT o N° de pasaporte.")
    elif not documento_valido(doc, tipo_doc):
        errores.append("13. El RUT no es válido (revisa el dígito verificador)." if tipo_doc == "RUT"
                       else "13. El pasaporte debe tener entre 5 y 20 letras o números.")
    if not fecha_nacimiento_valida(fnac):
        errores.append("14. Ingresa una fecha de nacimiento coherente.")
    for n, arch, etq in ((15, cedula, "el documento de identificación"), (16, licencia, "la licencia o título")):
        err = validar_archivo(arch, etq)
        if err:
            errores.append(f"{n}. {err}")
    if not (carrera or "").strip():
        errores.append("17. Indica tu carrera, unidad UCN o profesión.")
    campus_oblig = bool(vinculo) and vinculo_es_ucn(sb, vinculo, detalle)
    if campus_oblig and not campus:
        errores.append("18. Indica tu campus UCN.")
    if campus == "otro" and not campus_otro.strip():
        errores.append("18. Especifica el campus.")
    if nacionalidad == "Otro" and not nac_otra.strip():
        errores.append("19. Especifica tu nacionalidad.")
    if not vinculo:
        errores.append("20. Indica tu vínculo con la UCN.")
    elif vinculo == "otros" and not detalle:
        errores.append("20. Especifica tu vínculo (el valor del curso depende de esto).")
    if telefono and not telefono_valido(telefono):
        errores.append("21. El teléfono solo admite dígitos, espacios y +, con al menos 8 dígitos.")
    if not salud:
        errores.append("22. Responde la pregunta sobre condición de salud.")
    elif salud == "Sí" and not salud_req.strip():
        errores.append("22. Indica el requerimiento asociado a tu condición de salud.")
    if not forma_nom:
        errores.append("23. Elige la forma de pago.")
    if not terminos:
        errores.append("25. Debes aceptar los términos y condiciones.")
    if not consentimiento:
        errores.append("26. Debes autorizar el tratamiento de tus datos personales.")
    if modo == "publico":
        if st.session_state.get(k("web_hp")):
            errores.append("No se pudo enviar el formulario.")
        if st.session_state.get(f"{pref}_envios", 0) >= MAX_ENVIOS_SESION:
            errores.append("Alcanzaste el máximo de envíos desde esta sesión. Escribe a " + correo_contacto)

    if errores:
        st.error("Revisa los siguientes puntos:\n\n" + "\n".join(f"- {e}" for e in errores))
        return

    # ------------------------------------------------------------------ Guardar
    datos = {
        "correo": correo.strip().lower(), "idioma": idioma, "modalidad": modalidad,
        "oferta_id": oferta["oferta_id"] if oferta else None,
        "otro_idioma_nivel": otro_txt.strip() or None,
        "nombres": nombres.strip(), "apellido_paterno": ap_pat.strip(), "apellido_materno": ap_mat.strip(),
        "sexo": sexo, "genero": genero, "nombre_social": nombre_social.strip() or None,
        "pronombres": pronombres.strip(), "tipo_documento": tipo_doc, "rut": doc,
        "fecha_nacimiento": fnac.isoformat(), "carrera": carrera.strip(),
        "campus": campus, "campus_otro": campus_otro.strip() or None,
        "nacionalidad": nac_otra.strip() if nacionalidad == "Otro" else nacionalidad,
        "vinculo": vinculo, "vinculo_detalle": detalle, "telefono": (telefono or "").strip() or None,
        "salud_tiene_condicion": salud == "Sí", "salud_requerimiento": salud_req.strip() or None,
        "forma_pago": fp_op[forma_nom], "acepta_terminos": True, "consentimiento_datos": True,
        "fecha_consentimiento": datetime.now(timezone.utc).isoformat(),
    }

    with st.spinner("Guardando…"):
        if modo == "publico":
            ok = _guardar_publico(sb, datos, cedula, licencia, pref)
        else:
            ok = _guardar_coordinacion(sb, datos, cedula, licencia)
    if ok:
        st.session_state[f"{pref}_version"] = ver + 1  # limpia el formulario
        if modo == "publico":
            st.session_state[f"{pref}_envios"] = st.session_state.get(f"{pref}_envios", 0) + 1
            st.session_state[f"{pref}_confirmacion"] = {
                **ok, "oferta": oferta_sel if oferta_sel != OTRO else f"Otro: {otro_txt.strip()}",
                "idioma": idioma_nom, "modalidad": modalidad, "forma_pago": forma_nom,
                "nombre": f"{datos['nombres']} {datos['apellido_paterno']}", "correo": datos["correo"],
                "fecha_confirmacion": _fecha_larga(conv.get("fecha_confirmacion")),
            }
        else:
            st.session_state["fc_mensaje"] = ok["mensaje"]
        st.rerun()


def _subir_documentos(datos: dict, cedula, licencia, destino_fn) -> tuple[dict, list[str]]:
    campos, subidos = {}, []
    for pref, arch, tipo in (("cedula", cedula, "cedula"), ("licencia", licencia, "licencia")):
        ext = extension(arch)
        res = drive.subir_o_encolar(arch.getvalue(), drive.nombre_archivo(datos["rut"], tipo, ext), ext,
                                    [drive.CARPETA_DOCS, datos["rut"]], destino_fn(pref))
        campos.update({f"{pref}_drive_file_id": res["drive_file_id"], f"{pref}_drive_url": res["drive_url"],
                       f"{pref}_estado": res["estado"]})
        if res["drive_file_id"]:
            subidos.append(res["drive_file_id"])
    return campos, subidos


def _guardar_publico(sb, datos: dict, cedula, licencia, pref: str):
    codigo = "SOL-" + _secrets.token_hex(4).upper()
    archivos, subidos = _subir_documentos(
        datos, cedula, licencia, lambda p: {"tabla": "solicitud", "clave": {"codigo": codigo}, "prefijo": p})
    fila = {**datos, **archivos, "codigo": codigo}
    fila.pop("fecha_consentimiento")  # la fija la BD
    try:
        sb.table("solicitud").insert(fila, returning="minimal").execute()
    except Exception as e:
        drive.eliminar(subidos)  # no dejar archivos huérfanos si la BD rechazó la solicitud
        st.error(mensaje_error(e, "enviar la inscripción"))
        return None
    return {"codigo": codigo, "pendiente_archivos": any(archivos[f"{p}_estado"] != "subido" for p in ("cedula", "licencia"))}


def _guardar_coordinacion(sb, datos: dict, cedula, licencia):
    archivos, subidos = _subir_documentos(
        datos, cedula, licencia,
        lambda p: {"tabla": "documento_estudiante", "clave": {"rut_estudiante": datos["rut"], "tipo": p}})
    p_datos = {k: v for k, v in {**datos, **archivos}.items()
               if k not in ("idioma", "modalidad", "oferta_id", "otro_idioma_nivel", "forma_pago", "acepta_terminos")}
    try:
        sb.rpc("inscribir_estudiante", {"p_datos": p_datos, "p_oferta_id": datos["oferta_id"],
                                        "p_forma_pago": datos["forma_pago"], "p_origen": "coordinacion"}).execute()
    except Exception as e:
        drive.eliminar(subidos)
        st.error(mensaje_error(e, "guardar el estudiante"))
        return None
    sheets.tras_escritura(sb, ["estudiantes", "convocatorias_ofertas"])
    extra = "" if datos["oferta_id"] else " (sin curso asignado: quedó como «Otro (a convenir)»)"
    pend = any(archivos[f"{p}_estado"] != "subido" for p in ("cedula", "licencia"))
    return {"mensaje": f"Estudiante {datos['nombres']} {datos['apellido_paterno']} guardado e inscrito{extra}."
                       + (" Los documentos quedaron pendientes de subir a Drive." if pend else "")}


def _confirmacion(c: dict, pref: str):
    encabezado("¡Recibimos tu inscripción!", "Guarda tu código de solicitud")
    st.success(f"Tu código de solicitud es **{c['codigo']}**.")
    st.markdown(
        f"""
| | |
|---|---|
| **Nombre** | {c['nombre']} |
| **Correo** | {c['correo']} |
| **Idioma** | {c['idioma']} |
| **Modalidad** | {c['modalidad']} |
| **Curso** | {c['oferta']} |
| **Forma de pago** | {c['forma_pago']} |
""")
    st.info(f"La coordinación revisará tu solicitud. La confirmación del curso llegará a tu correo el "
            f"{c['fecha_confirmacion']}, si se alcanza el cupo mínimo. No transfieras dinero antes de esa confirmación.")
    if c.get("pendiente_archivos"):
        st.warning("Tus documentos quedaron en cola para subir; la coordinación los verá en cuanto se carguen.")
    if st.button("Enviar otra inscripción"):
        st.session_state.pop(f"{pref}_confirmacion", None)
        st.rerun()
