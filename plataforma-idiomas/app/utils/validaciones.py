import re


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
