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
# Composición multicolor de la lámina 14 del manual DRI.
FONDO_GRADIENTE = (
    f"radial-gradient(ellipse at 0% 100%, {AMARILLO} 0%, transparent 48%), "
    f"radial-gradient(ellipse at 100% 100%, {MENTA} 0%, transparent 55%), "
    f"radial-gradient(ellipse at 0% 35%, {FUCSIA} 0%, transparent 60%), "
    f"linear-gradient(135deg, {FUCSIA} 0%, {VIOLETA} 55%, {AZUL_GRIS} 100%)"
)

LOGO = ASSETS / "logo_dri_blanco.png"
FAVICON = ASSETS / "favicon.png"
LOGO_UCN = ASSETS / "ucn-isologo-2018.png"


@lru_cache(maxsize=1)
def logo_base64() -> str:
    return base64.b64encode(LOGO.read_bytes()).decode()


@lru_cache(maxsize=1)
def logo_ucn_base64() -> str:
    return base64.b64encode(LOGO_UCN.read_bytes()).decode()


CSS = f"""
<style>
/* ---------- Estructura general ---------- */
[data-testid="stAppViewContainer"] {{
    background: {FONDO_GRADIENTE};
    background-attachment: fixed;
    background-size: cover;
    min-height: 100vh;
}}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{
    padding: 2.4rem clamp(1rem, 3vw, 3rem) 3rem;
    max-width: 1200px;
    width: calc(100% - 3rem);
    margin: 2rem auto;
    background: rgba(255, 255, 255, .96);
    border: 1px solid rgba(255, 255, 255, .65);
    border-radius: 22px;
    box-shadow: 0 16px 48px rgba(66, 22, 104, .16);
}}
@media (max-width: 640px) {{
    .block-container {{ width: calc(100% - 1rem); margin: 1rem auto; border-radius: 16px; }}
}}

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
[data-testid="stTabs"] [role="tablist"] {{ gap: .6rem; padding: .3rem 0 .6rem; }}
[data-testid="stTabs"] [role="tab"] {{
    background: #EDE3FA; color: {MORADO}; border: 1px solid {MORADO};
    border-radius: 10px; padding: .6rem 1rem; height: auto; font-weight: 600;
}}
[data-testid="stTabs"] [role="tab"]:hover {{ background: #DFD0F3; }}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    background: {MORADO}; color: #FFFFFF;
}}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] p {{ color: #FFFFFF; }}
[data-testid="stTabs"] [role="tab"]:focus-visible {{ outline: 3px solid {VIOLETA}; outline-offset: 2px; }}
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button,
[data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryFormSubmit"] {{
    border-radius: 10px; font-weight: 600; border: 1.5px solid {MORADO}; color: {MORADO}; }}
.stButton > button:hover, .stDownloadButton > button:hover {{
    background: #F3EEF8; border-color: {VIOLETA}; color: {VIOLETA}; }}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"],
.stButton > [data-testid="stBaseButton-primary"],
.stFormSubmitButton > [data-testid="stBaseButton-primaryFormSubmit"] {{
    background: {MORADO}; color: #FFFFFF; border: 1.5px solid {MORADO}; }}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover,
.stButton > [data-testid="stBaseButton-primary"]:hover,
.stFormSubmitButton > [data-testid="stBaseButton-primaryFormSubmit"]:hover {{
    background: {VIOLETA}; border-color: {VIOLETA}; color: #FFFFFF; }}
/* El texto del botón principal va en un <p>: blanco también (antes quedaba morado sobre morado) */
[data-testid="stBaseButton-primary"] p, [data-testid="stBaseButton-primaryFormSubmit"] p {{ color: #FFFFFF; }}

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
.dri-login img {{ width: 80%; max-width: 360px; height: auto; display: block; opacity: 1; }}
.dri-login .dri-logo-ucn {{
    width: 100%; max-width: 360px; box-sizing: border-box;
    margin-top: 24px; padding: 12px; background: transparent; border-radius: 10px;
    /* La imagen original tiene blanco: convertir a blanco sobre negro y
       fundir el negro con el panel conserva la lectura sin un recuadro. */
    filter: grayscale(1) invert(1) brightness(4) contrast(2);
    mix-blend-mode: screen;
}}
.dri-login .texto {{ color: #FFFFFF; margin-top: 30px; font-size: 1.08rem; line-height: 1.5; opacity: .92; }}
.dri-login .franja {{ height: 12px; margin: 0 -40px; background: {GRADIENTE}; }}

/* ---------- Banner de convocatoria abierta (nuevo, misma paleta) ---------- */
.dri-banner {{ background: #FFFFFF; border: 1px solid #E7E2EC; border-left: 6px solid {MENTA};
    border-radius: 14px; padding: 16px 20px; margin-bottom: 14px; }}
.dri-banner .t {{ color: {MORADO}; font-weight: 800; font-size: 1.15rem; }}
.dri-banner .d {{ color: #6B5A7E; font-size: .95rem; margin-top: 4px; }}
.dri-banner .chip {{ display: inline-block; background: #F3EEF8; color: {MORADO}; border-radius: 999px;
    padding: 2px 10px; font-size: .8rem; font-weight: 700; margin-right: 6px; }}
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


@lru_cache(maxsize=1)
def _fotos_inicio() -> str:
    fotos = [
        ("inicio-universidad.jpg", "Universidad Católica del Norte"),
        ("inicio-estudiantes.jpg", "Estudiantes reunidos con banderas de distintos países"),
        ("inicio-banderas.jpg", "Personas levantando banderas internacionales"),
    ]
    return "".join(
        f'<img src="data:image/jpeg;base64,{base64.b64encode((ASSETS / archivo).read_bytes()).decode()}" '
        f'alt="{descripcion}">'
        for archivo, descripcion in fotos
    )


def portada_inscripcion():
    st.html("""
    <style>
    .dri-portada {position:relative;isolation:isolate;display:flex;align-items:center;
        min-height:340px;background:#421668;border-radius:20px;overflow:hidden;margin:0 0 24px;}
    .dri-portada-texto {position:relative;z-index:2;box-sizing:border-box;
        width:min(85%,560px);margin:28px;padding:26px 28px;background:rgba(255,255,255,.9);
        border:1px solid rgba(255,255,255,.8);border-radius:16px;
        box-shadow:0 8px 28px #42166826;}
    .dri-portada h2 {font-family:"Twogether Sans","Arial Black","Segoe UI",sans-serif;
        font-size:clamp(2rem,3.2vw,3rem);font-weight:900;line-height:1.08;
        letter-spacing:-.035em;color:#421668;margin:0 0 18px;
        text-wrap:balance;text-shadow:0 2px 0 rgba(255,255,255,.7);}
    .dri-portada p {color:#49345F;margin:0;line-height:1.5;}
    .dri-collage {position:absolute;inset:0;display:grid;grid-template-columns:1.1fr 1fr;
        grid-template-rows:1fr 1fr;gap:4px;z-index:0;}
    .dri-collage img {display:block;width:100%;height:100%;min-height:0;min-width:0;
        object-fit:cover;opacity:.85;border:0;border-radius:0;}
    .dri-collage img:nth-child(1) {grid-row:1 / 3;object-position:50% 50%;}
    .dri-collage img:nth-child(2) {object-position:50% 60%;}
    .dri-portada::after {content:"";position:absolute;inset:0;z-index:1;pointer-events:none;
        background:linear-gradient(100deg,rgba(66,22,104,.3),rgba(109,92,232,.12));}
    @media(max-width:640px){.dri-portada{min-height:320px;}
        .dri-portada-texto{width:calc(100% - 32px);margin:16px;padding:22px;}
        .dri-portada h2{font-size:clamp(1.8rem,7vw,2.3rem);}}
    </style>
    <section class="dri-portada" aria-label="Cursos de idiomas UCN">
      <div class="dri-portada-texto">
        <h2>Inscríbete en un curso de idiomas</h2>
        <p>Completa el formulario; no necesitas crear una cuenta</p>
      </div>
      <div class="dri-collage" aria-label="Galería de la universidad y comunidad internacional">
    """ + _fotos_inicio() + """
      </div>
    </section>
    """)


def panel_login():
    st.markdown(
        f"""
        <div class="dri-login">
          <div>
            <img src="data:image/png;base64,{logo_base64()}" alt="Dirección de Relaciones Internacionales UCN">
            <img class="dri-logo-ucn" style="opacity:1!important;background:transparent!important;filter:grayscale(1) invert(1) brightness(4) contrast(2)!important;mix-blend-mode:screen!important" src="data:image/png;base64,{logo_ucn_base64()}" alt="Universidad Católica del Norte">
            <div class="texto"><b>Sección de Idiomas</b><br>Sistema de gestión de cursos,
            asistencia, notas, pagos y certificados.</div>
          </div>
          <div class="franja"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def banner_convocatoria(titulo: str, detalle: str, chips: list[str] | None = None):
    """Tarjeta para las convocatorias abiertas en la pantalla de inicio."""
    import html
    chips_html = "".join(f'<span class="chip">{html.escape(c)}</span>' for c in (chips or []))
    st.markdown(
        f'<div class="dri-banner"><div>{chips_html}</div><div class="t">{html.escape(titulo)}</div>'
        f'<div class="d">{html.escape(detalle)}</div></div>',
        unsafe_allow_html=True,
    )
