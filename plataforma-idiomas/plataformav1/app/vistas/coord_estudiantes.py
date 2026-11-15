import streamlit as st
import pandas as pd
from utils.supabase_client import get_client
from utils.estilos import encabezado
from utils.datos import nombre_completo
from utils.exportar import boton_descarga
from utils.formulario_estudiante import render_formulario_estudiante, subir_documento

sb = get_client()
encabezado("Estudiantes")  # RF-01


# ---------- Formulario de registro ----------
with st.expander("➕ Registrar estudiante", expanded=False):
    datos = render_formulario_estudiante(sb, modo="registro")
    if datos:
        try:
            datos = dict(datos)
            cedula = datos.pop("_cedula")
            licencia = datos.pop("_licencia")
            existente_id = datos.pop("_existing_id", None)
            sin_cambios = datos.pop("_sin_cambios", False)
            if sin_cambios:
                st.success("Se continuará usando el registro existente.")
            else:
                datos["cedula_path"] = subir_documento(sb, cedula, datos["documento"], "cedula")
                datos["licencia_media_path"] = subir_documento(sb, licencia, datos["documento"], "licencia_media")
                if existente_id:
                    sb.table("estudiante").update(datos).eq("id", existente_id).execute()
                    st.success("Datos del estudiante actualizados.")
                else:
                    sb.table("estudiante").insert(datos).execute()
                    st.success("Estudiante registrado.")
            st.rerun()
        except Exception as error:
            mensaje = str(error).lower()
            if "duplicate" in mensaje or "23505" in mensaje:
                st.error("Ya existe un estudiante con ese RUT o correo electrónico.")
            else:
                st.error("No se pudo guardar el registro. Revisa los datos y vuelve a intentarlo.")

# ---------- Listado ----------
st.subheader("Estudiantes registrados")
try:
    est = sb.table("estudiante").select(
        "id, nombres, apellido_paterno, apellido_materno, nombre_social, documento, "
        "correo, telefono, unidad_ucn, carrera, campus, nacionalidad, cedula_path, "
        "licencia_media_path, tipo_estudiante(nombre)"
    ).order("id", desc=True).execute().data
except Exception:
    st.error("No se pudo cargar el listado de estudiantes. Inténtalo nuevamente.")
    st.stop()

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
    "Carrera": e.get("carrera") or e.get("unidad_ucn"),
    "Campus": e["campus"],
    "Nacionalidad": e["nacionalidad"],
    "Cédula adjunta": "✅" if e.get("cedula_path") else "❌",
    "Licencia adjunta": "✅" if e.get("licencia_media_path") else "❌",
} for e in est])

c1, c2 = st.columns([2, 2])
buscar = c1.text_input("Buscar por nombre, documento o correo")
vinculos = sorted(df["Vínculo UCN"].dropna().unique().tolist())
filtro = c2.multiselect("Filtrar por vínculo UCN", vinculos)

if buscar:
    b = buscar.strip().lower()
    df = df[df[["Nombre", "Documento", "Correo"]].apply(
        lambda col: col.fillna("").str.lower().str.contains(b, regex=False)).any(axis=1)]
if filtro:
    df = df[df["Vínculo UCN"].isin(filtro)]

st.caption(f"{len(df)} estudiante(s)")
boton_descarga(df, "estudiantes", "Estudiantes", key="export_estudiantes")
st.dataframe(df, hide_index=True, use_container_width=True)

st.subheader("Documentos adjuntos")
for indice in df.index:
    estudiante = est[indice]
    rutas = {
        "Cédula de identidad": estudiante.get("cedula_path"),
        "Licencia de enseñanza media": estudiante.get("licencia_media_path"),
    }
    if not any(rutas.values()):
        continue
    with st.expander(nombre_completo(estudiante)):
        for etiqueta, ruta in rutas.items():
            if not ruta:
                continue
            try:
                respuesta = sb.storage.from_("documentos_estudiantes").create_signed_url(ruta, 60)
                url = respuesta.get("signedURL") or respuesta.get("signedUrl")
                if url:
                    st.link_button(f"Ver / descargar {etiqueta}", url)
                else:
                    st.error(f"No se pudo generar el acceso temporal a {etiqueta.lower()}.")
            except Exception:
                st.error(f"No se pudo abrir {etiqueta.lower()}.")
