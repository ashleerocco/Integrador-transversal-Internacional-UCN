# Plataforma de Cursos de Idiomas · UCN Internacional (v2)

Reconstrucción de `../app/` reciclando su código (ver `../docs/INVENTARIO.md`). Misma identidad
visual y navegación; todo centralizado en Supabase, archivos en Google Drive y espejo en Google Sheets.

## Estructura

```
plataforma-idiomas/
├── app/                        versión anterior (intacta, candidata a retiro)
├── app_v2/
│   ├── app.py                  inicio público (convocatorias + formulario) y menú por rol
│   ├── requirements.txt
│   ├── .streamlit/             config.toml (tema DRI) · secrets.toml.example
│   ├── assets/                 logo y favicon
│   ├── utils/
│   │   ├── formulario_inscripcion.py   render_formulario_inscripcion(modo="publico"|"coordinacion")
│   │   ├── validaciones.py     normalizar_rut / rut_valido (reciclados) + pasaporte, teléfono, archivos
│   │   ├── supabase_client.py  cliente por sesión (esquema idiomas) y login por rol
│   │   ├── estilos.py          reciclado + banner de convocatoria
│   │   ├── drive.py            subida a "A+S Idiomas", cola de pendientes, descarga
│   │   ├── sheets.py           espejo Supabase → Sheets + sync_log
│   │   ├── excel.py            descargas .xlsx (cabeceras en español, enlaces clicables)
│   │   ├── catalogos.py · datos.py · errores.py
│   └── vistas/
│       ├── coord_resumen.py  coord_cursos.py  coord_solicitudes.py  coord_estudiantes.py
│       ├── coord_pagos.py    coord_certificados.py
│       ├── docente_asistencia.py  docente_notas.py
│       └── alumno_notas.py   alumno_certificado.py
├── supabase/                   SQL (ver supabase/README.md)
└── docs/INVENTARIO.md
```

## Configuración

1. `cp .streamlit/secrets.toml.example .streamlit/secrets.toml` y completar. **Nunca** subirlo a git.
2. **Supabase**: `SUPABASE_URL` y la clave *anon/publishable* (Settings → API). Exponer el esquema `idiomas`.
   La app **no usa** la clave `service_role`.
3. **Google (Drive + Sheets)** con una cuenta de servicio:
   1. Google Cloud → crear proyecto → habilitar *Google Drive API* y *Google Sheets API*.
   2. *IAM → Cuentas de servicio* → crear → *Claves* → JSON. Copiar sus campos a `[gcp_service_account]`.
   3. En el Drive de la unidad: crear la carpeta **"A+S Idiomas"** (idealmente en una unidad compartida) y
      compartirla como *Editor* con el `client_email` de la cuenta de servicio. Su ID (la parte final de la URL)
      va en `DRIVE_CARPETA_RAIZ_ID`. Las subcarpetas (`Documentos estudiantes/{RUT}`, `Pagos/{período}`,
      `Certificados/{curso}`) se crean solas. Los archivos **no** se comparten por enlace: heredan el acceso
      de la carpeta.
   4. Crear la hoja **"A+S Idiomas – Base de datos"**, compartirla como *Editor* con la cuenta de servicio y poner
      su ID en `SHEETS_ID`. Las pestañas se crean solas. Recomendación: que el resto de la unidad tenga acceso
      de *lector* (es un espejo: lo que se edite a mano se sobrescribe).
   - Sin Drive configurado la app funciona: los archivos quedan "pendientes de subir" en `PENDIENTES_DIR`
     y se reintentan desde Resumen o Solicitudes. En Streamlit Community Cloud ese disco no es permanente:
     configurar Drive antes de abrir el formulario público.
4. Ejecutar:
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```

## Cómo probar cada flujo (con `seed_demo.sql` cargado)

| # | Flujo | Pasos | Resultado esperado |
|---|---|---|---|
| 1 | Convocatoria → inicio | Coordinación → **Cursos** → cambiar la convocatoria DEMO a *Cerrada* y volver al inicio sin sesión | El banner y el formulario desaparecen; con *Abierta* vuelven. En **Resumen** la oferta de Portugués aparece con 0 inscritos |
| 2 | Formulario público | Inicio → elegir idioma y modalidad → la lista de cursos cambia en vivo; enviar con errores | Todos los errores juntos, numerados como el Google Form |
| 3 | Duplicado/spam | Enviar dos veces la misma persona y curso | Mensaje claro de solicitud vigente; >3 envíos/día bloqueados |
| 4 | Solicitudes | **Solicitudes** → aceptar `DEMO-0005` (Ana, ya estudiante) | No se duplica en **Estudiantes**; suma una inscripción a Francés y al contador del Resumen |
| 5 | "Otro (a convenir)" | Aceptar `DEMO-0006` | Pide elegir el curso antes de aceptar |
| 6 | Registro por coordinación | **Estudiantes → Registrar estudiante** | Mismo formulario; queda aceptado e inscrito sin pasar por Solicitudes |
| 7 | Filtros | **Estudiantes** → vínculo, género, campus, curso | Contador y Excel respetan los filtros |
| 8 | Pago | **Pagos** → RUT `41011211-6` (Héctor) → 220.000 | El nombre se completa solo; aparece en **Estudiantes pagados** y en Asistencia/Notas de Inglés A1 |
| 9 | Docente | Entrar como `docente1@demo.ucn.test` | Solo ve sus 2 cursos y solo alumnos pagados; S marca la sesión suspendida |
| 10 | Nota final | **Notas** → completar la Nota 3 de Javier Lagos | La BD calcula la nota final y el alumno pasa a **Certificados** |
| 11 | Certificados | Avanzar estados; intentar "Entregado" sin PDF; volver atrás | Fechas automáticas; exige PDF; retroceso solo con confirmación |
| 12 | Alumno | Entrar como `alumno@demo.ucn.test` | Ve sus notas, asistencia y su certificado entregado (en la demo el PDF es ficticio) |
| 13 | Sheets / Excel | **Resumen → Sincronizar ahora**, **Preparar respaldo** | Una pestaña por base; libro Excel con una hoja por tabla |

Pruebas automáticas usadas en el desarrollo: `supabase/tests/verificacion.sql` (30 pruebas de BD) y una
prueba de humo de todas las páginas con `streamlit.testing` contra PostgREST local.

## Supuestos y discrepancias encontradas

1. **Código S de asistencia**: el código anterior solo tenía P/A/J. En la planilla "TODOS LOS CURSOS 1-2026"
   la S aparece en *toda la columna* de una fecha → se implementó como **Sesión suspendida** (no cuenta para el %).
   Confirmar con la coordinación.
2. **Código de proyecto de Portugués**: la planilla repite 20104063 (el de Inglés). Se guardó tal cual,
   marcado "por confirmar" y editable en `idiomas.idioma`.
3. **Vínculo UCN**: el Google Form usa "Estudiante UCN/CEDUC, Funcionario/Académico, Egresado, Externo";
   la tarea pide pregrado/posgrado/egresado/externo/otros (+detalle). Se usó el de la tarea; el precio se
   deriva del vínculo/detalle (UCN $190.000, egresado/funcionario/otra institución $210.000, externo $220.000).
4. **Montos reales vs. lista**: en la planilla 2025 hay pagos al contado de $170.000 y cuotas de $60.000
   (3 × 60.000 = 180.000), distintos de la lista del formulario. El monto total de cada inscripción es editable;
   conviene confirmar si existe descuento por pago al contado.
5. **Pago en la v1 tenía estado "pendiente"**: ahora un pago es dinero recibido (confirmado/anulado);
   lo pendiente es el saldo de `estudiante_pagado`.
6. **Campus**: el Form lo llama "Ciudad" y no es obligatorio. Se exige si el vínculo es pregrado,
   posgrado o funcionario.
7. **RUT en el Form no es obligatorio**; aquí sí (es el ID). Extranjeros usan pasaporte (sin validar DV).
8. **Fecha de nacimiento**: se exige al menos 10 años de edad.
9. **Producción**: hoy existe un solo proyecto Supabase (con datos de prueba) y ninguna rama. No se ejecutó
   ningún cambio en él. Los 10 estudiantes de `public` tienen documentos no válidos como RUT.
10. **Credenciales**: `app/.streamlit/secrets.toml` estaba versionado con la URL y la clave *publishable*.
    Se sacó del índice de git, pero sigue en el historial: rotar la clave.
11. **Webhook a Apps Script** en `public.estudiante` envía datos personales sin autenticación. No se tocó;
    queda como candidato a revisión.
12. **Certificados de la v1** estaban en Supabase Storage; el script de migración los deja en "Firmado"
    con una nota para subir el PDF a Drive.
13. **Docentes de la v1** no tienen RUT: hay que completar `idiomas._mapa_docente` antes de migrar.
14. **Seed**: el certificado "Entregado" usa un ID de Drive ficticio, por lo que su descarga avisa que no está disponible.
