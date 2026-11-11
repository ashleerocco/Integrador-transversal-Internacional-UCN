"""Formulario compartido de inscripción y registro de estudiantes."""

import re
import time
from datetime import datetime, timezone

import streamlit as st

from utils.validaciones import normalizar_rut, rut_valido


SEXOS = ["Mujer", "Hombre", "Intersexual", "Prefiere no decir"]
GENEROS = ["Femenino", "Masculino", "No binario", "Otro", "Prefiere no decir"]
PRONOMBRES = ["ella", "él", "elle", "otro", "prefiero no decir"]
VINCULOS = ["Estudiante de pregrado", "Estudiante de posgrado", "Egresado/a", "Externo/a", "Otros"]
CAMPUS_UCN = ["Casa Central Antofagasta", "Campus Guayacán Coquimbo", "Campus Santiago", "Otro", "No aplica"]
# Lista local editable, para no agregar una dependencia sólo para poblar el selectbox.
PAISES = [
    "Afganistán", "Alemania", "Argentina", "Australia", "Bolivia", "Brasil", "Canadá", "Chile",
    "China", "Colombia", "Corea del Sur", "Ecuador", "España", "Estados Unidos", "Francia",
    "Haití", "India", "Italia", "Japón", "México", "Países Bajos", "Paraguay", "Perú",
    "Reino Unido", "Uruguay", "Venezuela", "Otra",
]
TIPOS_ARCHIVO = {"jpg", "jpeg", "png", "pdf"}
VINCULOS_UCN = {"Estudiante de pregrado", "Estudiante de posgrado", "Egresado/a"}
TAMANO_MAXIMO = 5 * 1024 * 1024


def _ext(archivo):
    return archivo.name.rsplit(".", 1)[-1].lower() if archivo and "." in archivo.name else ""


def validar_archivo(archivo, etiqueta, errores):
    if archivo is None:
        return
    if _ext(archivo) not in TIPOS_ARCHIVO:
        errores.append(f"{etiqueta}: el archivo debe ser PDF, JPG, JPEG o PNG.")
    tipos_mime = {
        "pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    }
    if archivo.type and archivo.type != tipos_mime.get(_ext(archivo)):
        errores.append(f"{etiqueta}: el tipo de archivo no coincide con su extensión.")
    if archivo.size > TAMANO_MAXIMO:
        errores.append(f"{etiqueta}: el archivo supera el máximo permitido de 5 MB.")


def subir_documento(sb, archivo, rut, tipo, solicitud_publica=False):
    """Valida y sube un documento al bucket privado; devuelve sólo su ruta."""
    if archivo is None:
        return None
    errores = []
    validar_archivo(archivo, "Documento", errores)
    if errores:
        raise ValueError(errores[0])
    extensiones = {"cedula": "cedula", "licencia_media": "licencia_media"}
    prefijo = extensiones.get(tipo)
    if prefijo is None:
        raise ValueError("Tipo de documento no válido.")
    carpeta = f"solicitudes/{rut}" if solicitud_publica else rut
    ruta = f"{carpeta}/{prefijo}_{time.time_ns()}.{_ext(archivo)}"
    sb.storage.from_("documentos_estudiantes").upload(
        ruta, archivo.getvalue(),
        {"content-type": archivo.type or "application/octet-stream", "upsert": "true"},
    )
    return ruta


def render_formulario_estudiante(sb, modo="registro"):
    """Dibuja campos comunes. Devuelve los datos listos al enviar o None."""
    if modo not in {"registro", "inscripcion"}:
        raise ValueError("Modo de formulario no válido.")

    try:
        tipos = sb.table("tipo_estudiante").select("id, nombre").execute().data
    except Exception:
        st.error("No se pudieron cargar las opciones de vínculo UCN. Inténtalo nuevamente.")
        return None
    tipos_por_nombre = {t["nombre"]: t["id"] for t in tipos}

    # El vínculo queda fuera del formulario para refrescar los campos condicionales al instante.
    st.markdown("**Datos académicos / institucionales**")
    vinculo = st.selectbox(
        "Vínculo UCN *", ["Selecciona un vínculo", *VINCULOS],
        key=f"{modo}_vinculo_ucn",
    )

    with st.form(f"formulario_estudiante_{modo}", clear_on_submit=True):
        st.markdown("**Identificación**")
        rut = st.text_input("RUT *", placeholder="12.345.678-5")
        correo = st.text_input("Correo electrónico *")
        c1, c2, c3 = st.columns(3)
        nombres = c1.text_input("Nombres *")
        apellido_paterno = c2.text_input("Apellido paterno *")
        apellido_materno = c3.text_input("Apellido materno")

        st.markdown("**Identidad**")
        c1, c2 = st.columns(2)
        sexo = c1.selectbox("Sexo", SEXOS)
        genero = c2.selectbox("Género", GENEROS)
        c1, c2 = st.columns(2)
        nombre_social = c1.text_input("Nombre social")
        pronombres = c2.selectbox("Pronombres", PRONOMBRES)

        st.markdown("**Documentos adjuntos**")
        cedula = st.file_uploader("Cédula de identidad (PDF, JPG, JPEG o PNG)", type=["pdf", "jpg", "jpeg", "png"], key=f"{modo}_cedula")
        if cedula and _ext(cedula) in {"jpg", "jpeg", "png"}:
            st.image(cedula, caption="Vista previa de la cédula", width=260)
        licencia = st.file_uploader("Licencia de enseñanza media (PDF, JPG, JPEG o PNG)", type=["pdf", "jpg", "jpeg", "png"], key=f"{modo}_licencia")

        st.markdown("**Datos académicos / institucionales**")
        if vinculo in VINCULOS_UCN:
            carrera = st.text_input("Carrera *")
            ocupacion = ""
            campus = st.selectbox("Campus UCN *", CAMPUS_UCN[:-1])
        elif vinculo in {"Externo/a", "Otros"}:
            carrera = ""
            ocupacion = st.text_input("Profesión u ocupación (opcional)")
            campus = "No aplica"
        else:
            carrera = ""
            ocupacion = ""
            campus = "No aplica"
        nacionalidad_op = st.selectbox("Nacionalidad", PAISES, index=PAISES.index("Chile"))

        st.markdown("**Contacto y salud**")
        telefono = st.text_input("Teléfono *", placeholder="+56 9 1234 5678")
        condicion_salud = st.text_area("Condición de salud (opcional)")
        st.caption("Esta información permite adaptar la atención y se tratará de forma confidencial.")
        consentimiento = st.checkbox(
            "Autorizo el tratamiento de mis datos personales, incluidos los documentos y la condición de salud, para gestionar mi inscripción. *"
        )
        enviar = st.form_submit_button(
            "Guardar estudiante" if modo == "registro" else "Enviar inscripción", type="primary"
        )

    if not enviar:
        pendiente = st.session_state.get(f"estudiante_existente_{modo}")
        if pendiente:
            st.warning("Ya existe un estudiante con ese RUT. Puedes actualizar sus datos o continuar con el registro existente.")
            actualizar, continuar = st.columns(2)
            if actualizar.button("Actualizar datos existentes", key=f"actualizar_existente_{modo}", type="primary"):
                st.session_state.pop(f"estudiante_existente_{modo}", None)
                return pendiente
            if continuar.button("Continuar sin cambios", key=f"continuar_existente_{modo}"):
                st.session_state.pop(f"estudiante_existente_{modo}", None)
                return {"_existing_id": pendiente["_existing_id"], "_sin_cambios": True}
        return None

    errores = []
    rut_limpio = normalizar_rut(rut.strip())
    correo_limpio = correo.strip().lower()
    telefono_limpio = telefono.strip()
    if not rut_limpio:
        errores.append("El RUT es obligatorio.")
    elif not rut_valido(rut_limpio):
        errores.append("El RUT no es válido; revisa el número y el dígito verificador.")
    if not correo_limpio:
        errores.append("El correo electrónico es obligatorio.")
    elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo_limpio):
        errores.append("El correo electrónico no tiene un formato válido.")
    if not nombres.strip():
        errores.append("Los nombres son obligatorios.")
    if not apellido_paterno.strip():
        errores.append("El apellido paterno es obligatorio.")
    if vinculo not in tipos_por_nombre:
        errores.append("No está configurado el vínculo UCN seleccionado. Ejecuta la migración de datos.")
    if vinculo in VINCULOS_UCN and not carrera.strip():
        errores.append("La carrera es obligatoria para este vínculo UCN.")
    if vinculo in VINCULOS_UCN and campus not in CAMPUS_UCN[:-1]:
        errores.append("Selecciona un campus UCN válido.")
    digitos = re.sub(r"\D", "", telefono_limpio)
    if not re.fullmatch(r"[0-9+ ]+", telefono_limpio) or len(digitos) < 8:
        errores.append("El teléfono debe contener sólo dígitos, espacios o +, y al menos 8 dígitos.")
    validar_archivo(cedula, "Cédula de identidad", errores)
    validar_archivo(licencia, "Licencia de enseñanza media", errores)
    if not consentimiento:
        errores.append("Debes autorizar el tratamiento de datos personales para continuar.")
    if errores:
        st.error("Corrige los siguientes campos para continuar:\n\n" + "\n".join(f"- {error}" for error in errores))
        return None

    ahora = datetime.now(timezone.utc).isoformat()
    datos = {
        "nombres": nombres.strip(),
        "apellido_paterno": apellido_paterno.strip(),
        "apellido_materno": apellido_materno.strip() or None,
        "sexo": sexo,
        "genero": genero,
        "nombre_social": nombre_social.strip() or None,
        "pronombres": pronombres,
        "tipo_documento": "RUT",
        "documento": rut_limpio,
        "correo": correo_limpio,
        "telefono": telefono_limpio,
        "tipo_estudiante_id": tipos_por_nombre.get(vinculo),
        "carrera": carrera.strip() or None,
        "unidad_ucn": carrera.strip() or ocupacion.strip() or None,
        "ocupacion": ocupacion.strip() or None,
        "campus": campus,
        "nacionalidad": nacionalidad_op,
        "condicion_salud": condicion_salud.strip() or None,
        "consentimiento_datos": True,
        "fecha_consentimiento": ahora,
        "_cedula": cedula,
        "_licencia": licencia,
    }

    if modo == "registro":
        try:
            existentes = sb.table("estudiante").select("id, nombres, apellido_paterno, apellido_materno").eq("documento", rut_limpio).limit(1).execute().data
        except Exception:
            st.error("No se pudo verificar si el RUT ya está registrado. Inténtalo nuevamente.")
            return None
        if existentes:
            datos["_existing_id"] = existentes[0]["id"]
            st.session_state[f"estudiante_existente_{modo}"] = datos
            st.warning("Ya existe un estudiante con ese RUT. Confirma si quieres actualizar sus datos o continuar sin cambios.")
            actualizar, continuar = st.columns(2)
            if actualizar.button("Actualizar datos existentes", key=f"actualizar_existente_{modo}", type="primary"):
                st.session_state.pop(f"estudiante_existente_{modo}", None)
                return datos
            if continuar.button("Continuar sin cambios", key=f"continuar_existente_{modo}"):
                st.session_state.pop(f"estudiante_existente_{modo}", None)
                return {"_existing_id": existentes[0]["id"], "_sin_cambios": True}
            return None
    return datos
