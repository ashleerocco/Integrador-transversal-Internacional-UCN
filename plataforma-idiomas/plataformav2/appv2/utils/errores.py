"""Traduce errores de la BD a mensajes claros, sin exponer datos personales."""
from utils.datos import log

MENSAJES = {
    "SOLICITUD_DUPLICADA": "Ya existe una solicitud vigente para esta persona en este curso. "
                           "Si necesitas cambiar algo, escribe a idiomas.pie@ucn.cl.",
    "LIMITE_SOLICITUDES": "Se alcanzó el máximo de envíos por día para este correo o documento. "
                          "Inténtalo mañana o escribe a idiomas.pie@ucn.cl.",
    "OFERTA_NO_DISPONIBLE": "El curso elegido ya no está disponible. Recarga la página y elige otro.",
    "FECHA_NACIMIENTO_INVALIDA": "La fecha de nacimiento no es coherente.",
    "FALTA_OFERTA": "Esta solicitud es «Otro (a convenir)»: elige el curso al que se inscribirá.",
    "SOLICITUD_YA_REVISADA": "La solicitud ya fue revisada por otra persona. Recarga la lista.",
    "FALTA_MOTIVO": "Indica el motivo.",
    "ALUMNO_NO_PAGADO": "El alumno no está en «Estudiantes pagados» para este curso.",
    "NOTAS_INCOMPLETAS": "El certificado requiere las 3 notas y la nota final.",
    "RETROCESO_NO_CONFIRMADO": "Para volver a un estado anterior debes confirmarlo.",
    "certificado_entregado_con_archivo": "Para marcar «Entregado» primero sube el PDF del certificado.",
    "PAGO_NO_ANULABLE": "El pago ya estaba anulado.",
    "NO_CUMPLE_NOTA_MINIMA": "El alumno no alcanza la nota mínima configurada.",
    "NO_CUMPLE_ASISTENCIA_MINIMA": "El alumno no alcanza la asistencia mínima configurada.",
    "SESION_NO_EXISTE": "La sesión no existe.",
    "SOLO_COORDINACION": "Solo la coordinación puede hacer esto.",
    "rut_valido": "El RUT o pasaporte no es válido.",
    "23505": "Ya existe un registro con esos datos.",
    "42501": "No tienes permiso para esta acción.",
}


def mensaje_error(e: Exception, accion: str = "guardar") -> str:
    texto = " ".join(str(getattr(e, a, "") or "") for a in ("message", "code", "details", "hint")) or str(e)
    for clave, msg in MENSAJES.items():
        if clave in texto:
            return msg
    # Solo se registra el tipo de error, nunca el contenido (podría incluir RUT o datos)
    log.warning("Error al %s: %s", accion, type(e).__name__)
    return f"No se pudo {accion}. Inténtalo de nuevo; si persiste, avisa a la coordinación."
