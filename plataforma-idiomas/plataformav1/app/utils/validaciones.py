"""Validaciones reutilizables.

`normalizar_rut`, `rut_valido` y `correo_valido` se reciclan de la versión
anterior (utils/validaciones.py) sin cambios de lógica. Lo demás es nuevo:
pasaporte, teléfono, archivos y fecha de nacimiento. Los mensajes de error
nunca incluyen el RUT ingresado (es dato personal).
"""
import re
from datetime import date

EXTENSIONES_PERMITIDAS = {"jpg", "jpeg", "png", "pdf"}
TAMANO_MAXIMO = 10 * 1024 * 1024  # 10 MB
_FIRMAS = {  # primeros bytes de cada tipo, para no confiar solo en la extensión
    "pdf": [b"%PDF"],
    "png": [b"\x89PNG"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
}


# ----- Reciclado tal cual -------------------------------------------------
def normalizar_rut(rut: str) -> str:
    r = rut.replace(".", "").replace(" ", "").upper()
    if "-" not in r and len(r) > 1:
        r = r[:-1] + "-" + r[-1]
    return r


def rut_valido(rut: str) -> bool:
    try:
        cuerpo, dv = rut.split("-")
    except ValueError:
        return False
    if not cuerpo.isdigit():
        return False
    suma, mult = 0, 2
    for d in reversed(cuerpo):
        suma += int(d) * mult
        mult = 2 if mult == 7 else mult + 1
    resto = 11 - suma % 11
    esperado = "0" if resto == 11 else "K" if resto == 10 else str(resto)
    return dv == esperado


def correo_valido(correo: str) -> bool:
    return re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo.strip()) is not None


# ----- Nuevo ----------------------------------------------------------------
def normalizar_pasaporte(doc: str) -> str:
    return re.sub(r"\s", "", doc).upper()


def normalizar_documento(doc: str, tipo: str) -> str:
    doc = (doc or "").strip()
    return normalizar_rut(doc) if tipo == "RUT" else normalizar_pasaporte(doc)


def documento_valido(doc: str, tipo: str) -> bool:
    if tipo == "RUT":
        return rut_valido(doc)
    return re.fullmatch(r"[A-Z0-9]{5,20}", doc or "") is not None


def telefono_valido(tel: str) -> bool:
    """Solo dígitos, espacios y '+', con al menos 8 dígitos."""
    tel = (tel or "").strip()
    return bool(re.fullmatch(r"[0-9+ ]+", tel)) and len(re.sub(r"\D", "", tel)) >= 8


def fecha_nacimiento_valida(f: date | None, hoy: date | None = None) -> bool:
    hoy = hoy or date.today()
    return f is not None and date(1900, 1, 1) <= f and (hoy.year - f.year) >= 10 and f <= hoy


def validar_archivo(archivo, etiqueta: str) -> str | None:
    """Devuelve un mensaje de error o None. Se llama ANTES de subir a Drive."""
    if archivo is None:
        return f"Adjunta {etiqueta}."
    ext = archivo.name.rsplit(".", 1)[-1].lower() if "." in archivo.name else ""
    if ext not in EXTENSIONES_PERMITIDAS:
        return f"{etiqueta}: formato no permitido (usa JPG, PNG o PDF)."
    if archivo.size > TAMANO_MAXIMO:
        return f"{etiqueta}: el archivo supera los 10 MB."
    cabecera = archivo.getvalue()[:8]
    if not any(cabecera.startswith(f) for f in _FIRMAS[ext]):
        return f"{etiqueta}: el contenido no corresponde a un {ext.upper()} válido."
    return None


def extension(archivo) -> str:
    ext = archivo.name.rsplit(".", 1)[-1].lower()
    return "jpg" if ext == "jpeg" else ext
