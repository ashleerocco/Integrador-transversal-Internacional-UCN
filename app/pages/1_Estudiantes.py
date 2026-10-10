"""RF-01: registrar y consultar estudiantes con su tipo."""
import pandas as pd
import streamlit as st
from postgrest.exceptions import APIError

from supabase_client import get_client

st.set_page_config(page_title="Estudiantes", page_icon="🎓", layout="wide")
st.title("🎓 Estudiantes")

client = get_client()


@st.cache_data(ttl=30)
def cargar_tipos():
    resp = client.table("tipo_estudiante").select("id, nombre").order("id").execute()
    return resp.data


@st.cache_data(ttl=30)
def cargar_estudiantes():
    resp = (
        client.table("estudiante")
        .select(
            "id, tipo_documento, documento, nombres, apellido_paterno, apellido_materno, "
            "correo, telefono, nacionalidad, tipo_estudiante(nombre)"
        )
        .order("apellido_paterno")
        .execute()
    )
    filas = []
    for fila in resp.data:
        tipo = fila.pop("tipo_estudiante", None) or {}
        fila["tipo"] = tipo.get("nombre", "")
        filas.append(fila)
    return pd.DataFrame(filas)


tipos = cargar_tipos()
tipos_por_nombre = {t["nombre"]: t["id"] for t in tipos}

tab_lista, tab_nuevo = st.tabs(["Consultar", "Registrar nuevo"])

# ---------------- Consultar ----------------
with tab_lista:
    df = cargar_estudiantes()
    if df.empty:
        st.info("No hay estudiantes registrados todavía.")
    else:
        c1, c2 = st.columns([2, 1])
        texto = c1.text_input("Buscar por nombre, correo o documento")
        tipo_filtro = c2.selectbox("Tipo de estudiante", ["Todos"] + list(tipos_por_nombre))

        filtrado = df.copy()
        if texto:
            patron = texto.strip().lower()
            columnas_busqueda = ["nombres", "apellido_paterno", "apellido_materno", "correo", "documento"]
            mascara = filtrado[columnas_busqueda].fillna("").apply(
                lambda col: col.str.lower().str.contains(patron, regex=False)
            ).any(axis=1)
            filtrado = filtrado[mascara]
        if tipo_filtro != "Todos":
            filtrado = filtrado[filtrado["tipo"] == tipo_filtro]

        st.caption(f"{len(filtrado)} de {len(df)} estudiantes")
        st.dataframe(
            filtrado.drop(columns=["id"]).rename(
                columns={
                    "tipo_documento": "Tipo doc.",
                    "documento": "Documento",
                    "nombres": "Nombres",
                    "apellido_paterno": "Apellido paterno",
                    "apellido_materno": "Apellido materno",
                    "correo": "Correo",
                    "telefono": "Teléfono",
                    "nacionalidad": "Nacionalidad",
                    "tipo": "Tipo",
                }
            ),
            width="stretch",
            hide_index=True,
        )

        st.subheader("Estudiantes por tipo")
        st.bar_chart(df["tipo"].value_counts(), horizontal=True)

# ---------------- Registrar ----------------
with tab_nuevo:
    with st.form("form_estudiante", clear_on_submit=True):
        c1, c2 = st.columns(2)
        tipo_doc = c1.selectbox("Tipo de documento", ["RUT", "Pasaporte", "Otro"])
        documento = c2.text_input("Documento *")
        nombres = c1.text_input("Nombres *")
        ap_pat = c2.text_input("Apellido paterno *")
        ap_mat = c1.text_input("Apellido materno")
        nombre_social = c2.text_input("Nombre social")
        correo = c1.text_input("Correo electrónico *")
        telefono = c2.text_input("Teléfono")
        nacionalidad = c1.text_input("Nacionalidad")
        tipo = c2.selectbox("Tipo de estudiante *", list(tipos_por_nombre))
        unidad = c1.text_input("Unidad UCN (si aplica)")
        campus = c2.text_input("Campus")
        enviado = st.form_submit_button("Guardar estudiante")

    if enviado:
        faltantes = [
            n for n, v in {
                "Documento": documento, "Nombres": nombres,
                "Apellido paterno": ap_pat, "Correo": correo,
            }.items() if not v.strip()
        ]
        if faltantes:
            st.error("Faltan campos obligatorios: " + ", ".join(faltantes))
        elif "@" not in correo:
            st.error("El correo no parece válido.")
        else:
            registro = {
                "tipo_documento": tipo_doc,
                "documento": documento.strip(),
                "nombres": nombres.strip(),
                "apellido_paterno": ap_pat.strip(),
                "apellido_materno": ap_mat.strip() or None,
                "nombre_social": nombre_social.strip() or None,
                "correo": correo.strip().lower(),
                "telefono": telefono.strip() or None,
                "nacionalidad": nacionalidad.strip() or None,
                "unidad_ucn": unidad.strip() or None,
                "campus": campus.strip() or None,
                "tipo_estudiante_id": tipos_por_nombre[tipo],
            }
            try:
                client.table("estudiante").insert(registro).execute()
                st.success("Estudiante registrado correctamente.")
                cargar_estudiantes.clear()
            except APIError as error:
                if "duplicate" in str(error).lower() or "unique" in str(error).lower():
                    st.error("Ya existe un estudiante con ese documento o correo.")
                else:
                    st.error("No se pudo guardar el registro.")
