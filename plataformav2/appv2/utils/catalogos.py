"""Catálogos (idiomas, vínculos, campus, formas de pago) y textos editables.

Se leen con la función pública `idiomas.catalogos_publicos()`, que también
funciona sin login. Se guardan 5 minutos en la sesión.
"""
import time

import streamlit as st

TTL = 300


def catalogos(sb) -> dict:
    c = st.session_state.get("cache_catalogos")
    if c and time.time() - c["t"] < TTL:
        return c["data"]
    data = sb.rpc("catalogos_publicos").execute().data or {}
    st.session_state.cache_catalogos = {"t": time.time(), "data": data}
    return data


def opciones(sb, nombre: str) -> dict[str, str]:
    """{nombre visible: código}"""
    return {x["nombre"]: x["codigo"] for x in catalogos(sb).get(nombre) or []}


def nombres(sb, nombre: str) -> dict[str, str]:
    """{código: nombre visible}"""
    return {x["codigo"]: x["nombre"] for x in catalogos(sb).get(nombre) or []}


def config(sb, clave: str, defecto=None):
    return (catalogos(sb).get("config") or {}).get(clave, defecto)


def vinculo_es_ucn(sb, vinculo: str, detalle: str | None) -> bool:
    cat = catalogos(sb)
    v = next((x for x in cat.get("vinculo_ucn") or [] if x["codigo"] == vinculo), None)
    if v and v.get("es_ucn"):
        return True
    d = next((x for x in cat.get("vinculo_detalle") or [] if x["codigo"] == detalle), None)
    return bool(d and d.get("es_ucn"))


def categoria_precio(sb, vinculo: str, detalle: str | None) -> str:
    cat = catalogos(sb)
    v = next((x for x in cat.get("vinculo_ucn") or [] if x["codigo"] == vinculo), {})
    if v.get("categoria_precio"):
        return v["categoria_precio"]
    d = next((x for x in cat.get("vinculo_detalle") or [] if x["codigo"] == detalle), {})
    return d.get("categoria_precio") or "externo"


PAISES = [
    "Chile", "Argentina", "Bolivia", "Brasil", "Colombia", "Costa Rica", "Cuba", "Ecuador", "El Salvador",
    "España", "Estados Unidos", "Francia", "Alemania", "Guatemala", "Haití", "Honduras", "Italia", "México",
    "Nicaragua", "Panamá", "Paraguay", "Perú", "Portugal", "Puerto Rico", "República Dominicana", "Uruguay",
    "Venezuela", "Canadá", "China", "Corea del Sur", "Japón", "India", "Reino Unido", "Rusia", "Ucrania",
    "Siria", "Marruecos", "Sudáfrica", "Australia", "Nueva Zelanda", "Otro",
]
