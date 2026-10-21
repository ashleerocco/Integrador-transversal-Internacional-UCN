import streamlit as st
import pandas as pd
from utils.supabase_client import get_client
from utils.estilos import encabezado
from utils.datos import nombre_completo

sb = get_client()
encabezado("Estudiantes")  # RF-01


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


tipos = sb.table("tipo_estudiante").select("id, nombre").order("id").execute().data
tipos_op = {t["nombre"]: t["id"] for t in tipos}

# ---------- Formulario de registro ----------
with st.expander("➕ Registrar estudiante", expanded=False):
    with st.form("nuevo_estudiante", clear_on_submit=True):
        st.markdown("**Datos personales**")
        c1, c2, c3 = st.columns(3)
        nombres = c1.text_input("Nombres *")
        ap_pat = c2.text_input("Apellido paterno *")
        ap_mat = c3.text_input("Apellido materno")

        c1, c2, c3, c4 = st.columns(4)
        sexo = c1.selectbox("Sexo", ["", "Mujer", "Hombre", "Otro / Prefiere no decir"])
        genero = c2.selectbox("Género", ["", "Femenino", "Masculino", "No binario", "Otro / Prefiere no decir"])
        nombre_social = c3.text_input("Nombre social")
        pronombres = c4.text_input("Pronombres")

        c1, c2, c3 = st.columns(3)
        tipo_doc = c1.selectbox("Tipo de documento", ["RUT", "Pasaporte", "Otro"])
        documento = c2.text_input("N° de documento * (RUT con guion, ej: 12345678-5)")
        nacionalidad = c3.text_input("Nacionalidad")

        st.markdown("**Contacto**")
        c1, c2 = st.columns(2)
        correo = c1.text_input("Correo electrónico *")
        telefono = c2.text_input("Teléfono")

        st.markdown("**Vínculo con la UCN**")
        c1, c2, c3 = st.columns(3)
        tipo = c1.selectbox("Vínculo UCN *", list(tipos_op))
        unidad = c2.text_input("Carrera / Unidad (o profesión si es externo)")
        campus = c3.text_input("Campus", placeholder="Ej: Casa Central - Antofagasta")
        salud = st.text_input("Condición de salud relevante (opcional)")

        guardar = st.form_submit_button("Guardar estudiante", type="primary")

    if guardar:
        doc = documento.strip()
        if tipo_doc == "RUT":
            doc = normalizar_rut(doc)

        if not (nombres.strip() and ap_pat.strip() and doc and correo.strip()):
            st.error("Completa los campos obligatorios (*).")
        elif tipo_doc == "RUT" and not rut_valido(doc):
            st.error("El RUT no es válido. Revisa el número y el dígito verificador.")
        elif "@" not in correo:
            st.error("El correo no parece válido.")
        else:
            try:
                sb.table("estudiante").insert({
                    "nombres": nombres.strip(),
                    "apellido_paterno": ap_pat.strip(),
                    "apellido_materno": ap_mat.strip() or None,
                    "sexo": sexo or None,
                    "genero": genero or None,
                    "nombre_social": nombre_social.strip() or None,
                    "pronombres": pronombres.strip() or None,
                    "tipo_documento": tipo_doc,
                    "documento": doc,
                    "nacionalidad": nacionalidad.strip() or None,
                    "correo": correo.strip().lower(),
                    "telefono": telefono.strip() or None,
                    "tipo_estudiante_id": tipos_op[tipo],
                    "unidad_ucn": unidad.strip() or None,
                    "campus": campus.strip() or None,
                    "condicion_salud": salud.strip() or None,
                }).execute()
                st.success("Estudiante registrado.")
            except Exception as e:
                msg = str(e)
                if "duplicate" in msg or "23505" in msg:
                    st.error("Ya existe un estudiante con ese documento o ese correo.")
                else:
                    st.error(f"No se pudo guardar: {msg}")

# ---------- Listado ----------
st.subheader("Estudiantes registrados")
est = sb.table("estudiante").select(
    "id, nombres, apellido_paterno, apellido_materno, nombre_social, documento, "
    "correo, telefono, unidad_ucn, campus, nacionalidad, tipo_estudiante(nombre)"
).order("id", desc=True).execute().data

if not est:
    st.info("Aún no hay estudiantes registrados.")
    st.stop()

df = pd.DataFrame([{
    "Nombre": nombre_completo(e),
    "Nombre social": e["nombre_social"],
    "Documento": e["documento"],
    "Correo": e["correo"],
    "Teléfono": e["telefono"],
    "Vínculo UCN": e["tipo_estudiante"]["nombre"],
    "Carrera / Unidad": e["unidad_ucn"],
    "Campus": e["campus"],
    "Nacionalidad": e["nacionalidad"],
} for e in est])

c1, c2 = st.columns([2, 2])
buscar = c1.text_input("Buscar por nombre, documento o correo")
filtro = c2.multiselect("Filtrar por vínculo UCN", list(tipos_op))

if buscar:
    b = buscar.strip().lower()
    df = df[df[["Nombre", "Documento", "Correo"]].apply(
        lambda col: col.fillna("").str.lower().str.contains(b, regex=False)).any(axis=1)]
if filtro:
    df = df[df["Vínculo UCN"].isin(filtro)]

st.caption(f"{len(df)} estudiante(s)")
st.dataframe(df, hide_index=True, use_container_width=True)
