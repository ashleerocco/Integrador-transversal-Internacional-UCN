from datetime import date

import streamlit as st

from utils.datos import nombre_completo
from utils.estilos import encabezado
from utils.supabase_client import get_client

sb = get_client()
perfil = st.session_state["perfil"]
encabezado("Solicitudes de inscripción",
           "Pre-inscripciones recibidas desde el formulario público")


def aprobar(s: dict):
    """Crea (o reutiliza) el estudiante, crea la inscripción y un pago pendiente."""
    existente = sb.table("estudiante").select("id").eq("documento", s["documento"]).execute().data
    if existente:
        est_id = existente[0]["id"]
    else:
        campos = ["nombres", "apellido_paterno", "apellido_materno", "sexo",
                  "tipo_documento", "documento", "correo", "telefono",
                  "tipo_estudiante_id", "unidad_ucn", "campus"]
        datos = {k: s[k] for k in campos if s.get(k) not in (None, "")}
        est_id = sb.table("estudiante").insert(datos).execute().data[0]["id"]

    ya = (sb.table("inscripcion").select("id")
          .eq("estudiante_id", est_id).eq("oferta_id", s["oferta_id"]).execute().data)
    if ya:
        insc_id = ya[0]["id"]
    else:
        insc_id = sb.table("inscripcion").insert({
            "estudiante_id": est_id,
            "oferta_id": s["oferta_id"],
            "estado": "inscrito",
        }).execute().data[0]["id"]
        valor = (s.get("oferta_curso") or {}).get("valor")
        if valor:
            sb.table("pago").insert({
                "inscripcion_id": insc_id, "monto": int(valor), "estado": "pendiente",
            }).execute()

    sb.table("solicitud_inscripcion").update({
        "estado": "aprobada", "estudiante_id": est_id, "inscripcion_id": insc_id,
        "revisado_por": perfil["id"], "revisado_en": date.today().isoformat(),
    }).eq("id", s["id"]).execute()


def rechazar(s: dict, motivo: str):
    sb.table("solicitud_inscripcion").update({
        "estado": "rechazada", "observacion": motivo or None,
        "revisado_por": perfil["id"], "revisado_en": date.today().isoformat(),
    }).eq("id", s["id"]).execute()


estado = st.radio("Mostrar", ["pendiente", "aprobada", "rechazada"], horizontal=True)
sols = sb.table("solicitud_inscripcion").select(
    "*, oferta_curso(periodo, valor, curso(nombre)), tipo_estudiante(nombre)"
).eq("estado", estado).order("id", desc=True).execute().data

st.caption(f"{len(sols)} solicitud(es) {estado}(s)")
if not sols:
    st.info("No hay solicitudes en este estado.")

for s in sols:
    oc = s["oferta_curso"]
    titulo = f"{nombre_completo(s)} — {oc['curso']['nombre']} ({oc['periodo']})"
    with st.expander(titulo):
        c1, c2 = st.columns(2)
        c1.write(f"**Documento:** {s['documento']}")
        c1.write(f"**Correo:** {s['correo']}")
        c1.write(f"**Teléfono:** {s['telefono'] or '—'}")
        c2.write(f"**Vínculo UCN:** {s['tipo_estudiante']['nombre']}")
        c2.write(f"**Carrera / Unidad:** {s['unidad_ucn'] or '—'}")
        c2.write(f"**Campus:** {s['campus'] or '—'}")
        st.caption(f"Recibida: {s['creado_en'][:16].replace('T', ' ')}")
        if s.get("observacion"):
            st.write(f"**Observación:** {s['observacion']}")

        if estado == "pendiente":
            motivo = st.text_input("Motivo (solo si rechazas)", key=f"m{s['id']}")
            b1, b2, _ = st.columns([1, 1, 3])
            if b1.button("Aprobar", type="primary", key=f"a{s['id']}"):
                try:
                    aprobar(s)
                    st.rerun()
                except Exception as e:
                    msg = str(e)
                    if "duplicate" in msg or "23505" in msg:
                        st.error("Ya existe un estudiante con ese correo o documento. Revísalo en Estudiantes.")
                    else:
                        st.error(f"No se pudo aprobar: {msg}")
            if b2.button("Rechazar", key=f"r{s['id']}"):
                rechazar(s, motivo)
                st.rerun()