def nombre_completo(e: dict) -> str:
    partes = [e.get("nombres"), e.get("apellido_paterno"), e.get("apellido_materno")]
    return " ".join(p for p in partes if p)


def etiqueta_curso(oferta: dict) -> str:
    return f"{oferta['curso']['nombre']} ({oferta['periodo']})"


def inscripciones_etiquetadas(sb, estados=None) -> dict:
    """Devuelve {'Alumno — Curso (periodo)': inscripcion_id} para usar en selectbox."""
    q = sb.table("inscripcion").select(
        "id, estudiante(nombres, apellido_paterno), oferta_curso(periodo, curso(nombre))"
    )
    if estados:
        q = q.in_("estado", estados)
    data = q.order("id", desc=True).execute().data
    return {
        f"{nombre_completo(i['estudiante'])} — {etiqueta_curso(i['oferta_curso'])}": i["id"]
        for i in data
    }
