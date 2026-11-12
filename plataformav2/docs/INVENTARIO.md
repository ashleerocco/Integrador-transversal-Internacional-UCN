# Inventario de la plataforma anterior (fase 1)

Revisado: rama `main`, commit `7cf4ffe` (carpeta `plataforma-idiomas/app/`) y el proyecto Supabase
"Idiomas UCN Project" (solo lectura: no se ejecutó ninguna escritura en producción).

Decisión: **R** = se recicla tal cual · **A** = se adapta (copiado a `app_v2/` con cambios) ·
**D** = se descarta en la versión nueva (no se borra; queda como *candidato a revisión*).

## 1. Archivos del repositorio

| Archivo | Contenido / funciones | Decisión | Destino en la nueva estructura |
|---|---|---|---|
| `app/app.py` | `st.set_page_config`, `pantalla_inicio()` (panel morado + pestañas Inscripción / Iniciar sesión), menú por rol con `st.navigation` | **A** | `app_v2/app.py`: mismo layout y navegación; agrega banners de convocatorias abiertas, rol `coordinacion` y páginas nuevas |
| `app/utils/estilos.py` | Paleta DRI, `CSS`, `aplicar_estilos()`, `encabezado()`, `panel_login()` | **R** | `app_v2/utils/estilos.py` (copia literal + clase `.dri-banner` para convocatorias) |
| `app/utils/validaciones.py` | `normalizar_rut()`, `rut_valido()`, `correo_valido()` | **A** | `app_v2/utils/validaciones.py`: mismas funciones + pasaporte, teléfono, archivos, fecha de nacimiento |
| `app/utils/supabase_client.py` | `get_client()` por sesión, `login()`, `logout()` | **A** | `app_v2/utils/supabase_client.py`: mismo patrón; apunta al esquema `idiomas` y a `idiomas.perfil` |
| `app/utils/datos.py` | `nombre_completo()`, `etiqueta_curso()`, `inscripciones_etiquetadas()` | **A** | `app_v2/utils/datos.py`: `nombre_completo` igual; etiquetas por `oferta_id`/RUT |
| `app/utils/inscripcion.py` | `formulario_inscripcion()` público (subconjunto del Google Form) | **D** → reemplazado | `app_v2/utils/formulario_inscripcion.py` (formulario completo, compartido público/coordinación) |
| `app/vistas/coord_resumen.py` | Métricas, gráfico por tipo, tabla `v_inscritos_vs_minimo` | **A** | `app_v2/vistas/coord_resumen.py` + vínculo, pagos, asistencia, certificados, sync y respaldo |
| `app/vistas/coord_solicitudes` | Aprobar/rechazar solicitudes | **A** | `app_v2/vistas/coord_solicitudes.py`. ⚠️ El archivo original **no tiene extensión `.py`**, pero `app.py` lo carga como `coord_solicitudes.py`: en la versión anterior esa página no abre |
| `app/vistas/coord_estudiantes.py` | Registro (duplica `normalizar_rut`/`rut_valido`), listado con búsqueda y filtro por vínculo | **A** | `app_v2/vistas/coord_estudiantes.py` (pestañas Todos / Pagados; registro con el formulario compartido) |
| `app/vistas/coord_cursos.py` | Alta de oferta (idioma, nivel, semestre, valor único, cupos 5/20) | **A** | `app_v2/vistas/coord_cursos.py` (convocatorias + ofertas, valores por vínculo, horario, docente por RUT) |
| `app/vistas/coord_pagos.py` | Pago por inscripción con estado pendiente/pagado/devuelto | **A** | `app_v2/vistas/coord_pagos.py` (columnas de la planilla real, cuotas, comprobante a Drive, totales por mes) |
| `app/vistas/coord_certificados.py` | Estados pendiente/solicitado/entregado, PDF a Storage | **A** | `app_v2/vistas/coord_certificados.py` (flujo Solicitado→Pendiente→Firmado→Entregado, PDF a Drive) |
| `app/vistas/docente_asistencia.py` | Selector de curso, sesiones, `st.data_editor` P/A/J, % asistencia | **R/A** | Misma lógica de pantalla; ahora lista `estudiante_pagado`, agrega código **S** y calendario automático |
| `app/vistas/docente_notas.py` | `st.data_editor` Nota 1-3 (1,0-7,0) | **R/A** | Misma lógica; guarda en una fila por alumno y la nota final la calcula la BD |
| `app/vistas/alumno_notas.py` | Notas del alumno (RLS) | **R/A** | + asistencia; claves por RUT |
| `app/vistas/alumno_certificado.py` | Descarga desde bucket `certificados` | **A** | Descarga desde Drive (la app lo baja con la cuenta de servicio, el enlace no es público) |
| `app/assets/*.png` | Logo DRI blanco y favicon | **R** | copiados a `app_v2/assets/` |
| `app/.streamlit/config.toml` | Tema (violeta `#6D5CE8`, fondo blanco) | **R** | copiado |
| `app/.streamlit/secrets.toml` | URL y clave *publishable* de Supabase **versionadas en git** | **D** | ⚠️ Se quitó del índice de git (`git rm --cached`, el archivo local se conserva). Sigue en el historial: rotar la clave |
| `app/.streamlit/secrets.toml.example` | Plantilla | **A** | `app_v2/.streamlit/secrets.toml.example` con Drive y Sheets |
| `requirements.txt` (raíz y `plataforma-idiomas/`) | streamlit, supabase, pandas | **A** | `app_v2/requirements.txt` + openpyxl, gspread, google-api-python-client |
| `doc/*.md` | Guía, entrevistas, bitácora | — | Sin cambios (fuente de requerimientos) |

## 2. Base de datos de producción (esquema `public`)

Filas al momento de la revisión: estudiante 10, oferta_curso 4, inscripcion 10, pago 10, nota 21,
asistencia 48, certificado 7, perfil 2, docente 2, solicitud_inscripcion 0.

| Objeto | Tipo | Observación | Decisión |
|---|---|---|---|
| `estudiante` | tabla | PK `id` bigint; `documento` único | **A** → `idiomas.estudiante` con PK `rut` |
| `docente` | tabla | PK `id`, sin RUT | **A** → `idiomas.docente` con PK `rut` (los 2 docentes actuales necesitan RUT: ver migración) |
| `perfil` | tabla | rol `coordinadora/docente/estudiante`, FKs por id | **A** → `idiomas.perfil` con `rut_docente` / `rut_estudiante` |
| `tipo_estudiante` | catálogo | 4 valores (falta "Otros") | **A** → `idiomas.vinculo_ucn` (5 valores) + `vinculo_detalle` |
| `idioma` | catálogo | solo Inglés y Francés | **A** → 6 idiomas + código de proyecto |
| `curso`, `oferta_curso` | tablas | Sin convocatoria, sin horario/sede, valor único | **A** → `convocatoria` + `oferta` + `oferta_valor` |
| `solicitud_inscripcion` | tabla | Campos parciales, rutas de Storage | **A** → `idiomas.solicitud` |
| `inscripcion` | tabla | Varios estados + `nota_final` manual | **A** → PK `(rut_estudiante, oferta_id)` |
| `pago` | tabla | Sin N° transacción/boleta/cuota | **A** → `idiomas.pago` + `estudiante_pagado` (trigger) |
| `sesion`, `asistencia` | tablas | Códigos P/A/J | **A** → `sesion (oferta_id, fecha)`, `asistencia (rut, oferta_id, fecha)` P/A/J/S |
| `nota` | tabla | Una fila por evaluación (+ porcentaje) | **A** → una fila por alumno, `nota_final` columna generada |
| `certificado` | tabla | FK a inscripción, `archivo_path` | **A** → PK `(rut, oferta_id)`, Drive |
| `v_inscritos_vs_minimo` | vista | Solo ofertas con curso; no cuenta solicitudes pendientes | **A** (misma idea, nuevo modelo) |
| `v_asistencia_inscripcion`, `v_oferta_cupos` | vistas | | **A** → `v_asistencia_resumen`, `v_oferta` |
| `abrir_oferta()`, `cerrar_oferta_sin_cupos()` | funciones | Flujo preinscrito→lista_espera | **D** (reemplazado por estados de convocatoria/oferta) |
| `app.rol()`, `app.estudiante_id()`, `app.docente_id()`, `app.ofertas_docente()` | funciones RLS | patrón `security definer` + `(select ...)` | **A** → `idiomas.rol_actual()`, `rut_*_actual()`, `ofertas_docente()` |
| `app.registrar_estudiante_auth()` | trigger en auth | Autorregistro de alumnos | **D** (candidato a revisión: las cuentas de alumno las crea coordinación) |
| Trigger `estudiantes_sheets` en `public.estudiante` | webhook | Envía cada cambio a un Apps Script **sin autenticación** | **D** (candidato a revisión; reemplazado por espejo Supabase→Sheets con cuenta de servicio) |
| Buckets `certificados`, `comprobantes` | Storage | privados | **D** → Google Drive "A+S Idiomas" (los PDFs existentes se migran a mano, ver `supabase/README.md`) |
| Política anon `oferta_curso`, `curso`, `tipo_estudiante` SELECT | RLS | Lectura pública de tablas | **D** → funciones `idiomas.ofertas_publicas()` y `catalogos_publicos()` (sin políticas anon de lectura) |

## 3. Material de referencia revisado

- **Formulario "Cursos Idiomas PIE-UCN 1-2026"**: 26 preguntas; vínculo en el Form es "Estudiante UCN/CEDUC, Funcionario/Académico, Egresado/ex alumno, Externo" (la tarea pide pregrado/posgrado/egresado/externo/otros: se usa el de la tarea y se guarda el detalle).
- **"TODOS LOS CURSOS 1-2026 – Inglés A1"**: códigos de asistencia P, A, J y **S**. La S aparece en *toda la columna* de una misma fecha → se interpreta como **sesión suspendida** (feriado/suspensión), que no cuenta para el porcentaje. El código anterior no tenía S (solo P/A/J), así que no se pudo confirmar desde el código. Las notas se registran como "porcentaje/nota" (ej. 96/6.3).
- **"Pagos Cursos de Idiomas 2025.xlsx"**: una hoja por proyecto (Inglés 20104063, Alemán 20104064, Francés 20104077, Italiano 20104168, Portugués *repite 20104063*, Coreano 20104167), bloques por mes con fila "Mes / Total". Columnas: N°, Nombre, Banco, RUT, Fecha, Monto, N° Transacción, código boleta (C9-xxxx, columna sin título).

## 4. Candidatos a revisión (no se borró nada)

1. `plataforma-idiomas/app/` completa (reemplazada por `app_v2/`).
2. Todo el esquema `public` de Supabase (la versión nueva vive en el esquema `idiomas`).
3. Webhook `estudiantes_sheets` (Apps Script sin autenticación, recibe datos personales).
4. Buckets `certificados` y `comprobantes`.
5. `app.registrar_estudiante_auth()` y sus funciones `abrir_oferta` / `cerrar_oferta_sin_cupos`.
6. La clave publishable versionada en `app/.streamlit/secrets.toml` (rotar).
