"""Identidad visual: Manual de Marca Dirección de Relaciones Internacionales UCN.

Paleta oficial:  Morado #421668 · Azul grisáceo #7C9AC0 · Violeta #6D5CE8
                 Menta #00DBAD · Fucsia #DB4ED2 · Rosa #EC4D85 · Amarillo #FFAD0C
Tipografía institucional: Twogether Sans (títulos) y Myriad Pro (texto).
Streamlit usa Source Sans, de aspecto muy cercano a Myriad Pro.
"""
import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).resolve().parent.parent / "assets"

MORADO = "#421668"
AZUL_GRIS = "#7C9AC0"
VIOLETA = "#6D5CE8"
MENTA = "#00DBAD"
FUCSIA = "#DB4ED2"
ROSA = "#EC4D85"
AMARILLO = "#FFAD0C"

GRADIENTE = f"linear-gradient(90deg, {VIOLETA} 0%, {FUCSIA} 55%, {AMARILLO} 100%)"

LOGO = ASSETS / "logo_dri_blanco.png"
FAVICON = ASSETS / "favicon.png"


@lru_cache(maxsize=1)
def logo_base64() -> str:
    return base64.b64encode(LOGO.read_bytes()).decode()


CSS = f"""
<style>
/* ---------- Estructura general ---------- */
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 2.4rem; max-width: 1200px; }}

/* ---------- Encabezado de página ---------- */
.dri-titulo {{ font-size: 2.1rem; font-weight: 800; line-height: 1.15;
              color: {MORADO}; letter-spacing: -0.01em; margin: 0; }}
.dri-sub {{ color: #6B5A7E; font-size: 1.02rem; margin-top: .35rem; }}
.dri-franja {{ height: 4px; width: 96px; border-radius: 2px;
              background: {GRADIENTE}; margin: .7rem 0 1.6rem 0; }}
h2, h3 {{ color: {MORADO}; font-weight: 700; }}

/* ---------- Barra lateral ---------- */
[data-testid="stSidebar"] {{ background: {MORADO}; }}
[data-testid="stSidebar"] * {{ color: #FFFFFF; }}
[data-testid="stSidebarHeader"] {{ height: auto; padding: 1.6rem 1.2rem .6rem 1.2rem; }}
[data-testid="stSidebarHeader"] img, [data-testid="stLogo"] {{
    height: auto !important; width: 100% !important; max-width: 230px !important; }}
[data-testid="stSidebarNav"] a, [data-testid="stSidebarNavLink"] {{ border-radius: 10px; }}
[data-testid="stSidebarNav"] a:hover, [data-testid="stSidebarNavLink"]:hover {{
    background: rgba(255,255,255,.10); }}
[data-testid="stSidebarNav"] a[aria-current="page"],
[data-testid="stSidebarNavLink"][aria-current="page"] {{
    background: rgba(255,255,255,.18); font-weight: 700; }}
[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,.22); }}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {{ opacity: .8; }}
[data-testid="stSidebar"] .stButton > button {{
    background: transparent; border: 1.5px solid rgba(255,255,255,.6); color: #FFFFFF; }}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(255,255,255,.14); border-color: #FFFFFF; color: #FFFFFF; }}

/* ---------- Botones ---------- */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button,
[data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryFormSubmit"] {{
    border-radius: 10px; font-weight: 600; border: 1.5px solid {MORADO}; color: {MORADO}; }}
.stButton > button:hover, .stDownloadButton > button:hover {{
    background: #F3EEF8; border-color: {VIOLETA}; color: {VIOLETA}; }}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"],
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {{
    background: {MORADO}; color: #FFFFFF; border: 1.5px solid {MORADO}; }}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover {{
    background: {VIOLETA}; border-color: {VIOLETA}; color: #FFFFFF; }}

/* ---------- Tarjetas, tablas y formularios ---------- */
[data-testid="stMetric"] {{ background: #FFFFFF; border: 1px solid #E7E2EC;
    border-left: 5px solid {VIOLETA}; border-radius: 12px; padding: 14px 18px; }}
[data-testid="stMetricLabel"] p {{ color: #6B5A7E; font-weight: 600; }}
[data-testid="stMetricValue"] {{ color: {MORADO}; font-weight: 800; }}
[data-testid="stExpander"] {{ border: 1px solid #E7E2EC; border-radius: 12px; }}
[data-testid="stExpander"] summary p {{ font-weight: 600; color: {MORADO}; }}
[data-testid="stForm"] {{ border: 1px solid #E7E2EC; border-radius: 14px; background: #FBFAFD; }}
[data-testid="stDataFrame"] {{ border: 1px solid #E7E2EC; border-radius: 12px; overflow: hidden; }}

/* ---------- Pantalla de ingreso ---------- */
.dri-login {{ background: {MORADO}; border-radius: 18px; padding: 52px 40px 0 40px;
    min-height: 500px; display: flex; flex-direction: column; justify-content: space-between;
    overflow: hidden; }}
.dri-login img {{ width: 80%; max-width: 360px; height: auto; display: block; }}
.dri-login .texto {{ color: #FFFFFF; margin-top: 30px; font-size: 1.08rem; line-height: 1.5; opacity: .92; }}
.dri-login .franja {{ height: 12px; margin: 0 -40px; background: {GRADIENTE}; }}
</style>
"""


def aplicar_estilos():
    st.markdown(CSS, unsafe_allow_html=True)


def encabezado(titulo: str, subtitulo: str | None = None):
    sub = f'<div class="dri-sub">{subtitulo}</div>' if subtitulo else ""
    st.markdown(
        f'<div class="dri-titulo">{titulo}</div>{sub}<div class="dri-franja"></div>',
        unsafe_allow_html=True,
    )


def panel_login():
    st.markdown(
        f"""
        <div class="dri-login">
          <div>
            <img src="data:image/png;base64,{logo_base64()}" alt="Dirección de Relaciones Internacionales UCN">
            <div class="texto"><b>Sección de Idiomas</b><br>Sistema de gestión de cursos,
            asistencia, notas, pagos y certificados.</div>
          </div>
          <div class="franja"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
