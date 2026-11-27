# Plataforma de Cursos de Idiomas · UCN Internacional (v1, sin datos de prueba)

Mismo código que `../../plataformav2/appv2`, preparado para usarse con datos reales: **no incluye**
datos ficticios (seed/demo), pruebas con datos inventados ni usuarios de demostración.
Todo centralizado en Supabase, archivos en Google Drive (carpeta "A+S Idiomas") y espejo opcional en Google Sheets.

## Estructura

```
plataformav1/
├── app/
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
└── supabase/                   SQL necesario para funcionar (ver supabase/README.md)
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
   - **Drive sin Google Cloud (recomendado):** la cuenta del socio comunitario que administra la carpeta
     **"A+S Idiomas"** instala un pequeño Apps Script que hace de puente. Nada queda asociado a cuentas de estudiantes.
     1. Con esa cuenta: [script.google.com](https://script.google.com) → *Nuevo proyecto* → pegar
        [`apps_script/Codigo.gs`](apps_script/Codigo.gs).
     2. Completar `CARPETA_RAIZ_ID` (parte final de la URL de la carpeta) y `TOKEN` (una clave larga inventada).
     3. Seleccionar la función `probar` → ▶ *Ejecutar* → aceptar permisos. El registro debe decir "Acceso correcto".
     4. *Implementar → Nueva implementación → Aplicación web*. *Ejecutar como:* **Yo**.
        *Quién tiene acceso:* **Cualquier usuario**. Copiar la URL que termina en `/exec`.
     5. En `secrets.toml` (y en *Secrets* de Streamlit Cloud): `DRIVE_APPS_SCRIPT_URL` y `DRIVE_APPS_SCRIPT_TOKEN`.
     6. En la app: **Resumen → Probar conexión con Drive**, y luego **Reintentar subidas** para la cola local.
     - Si se cambia el código del script, hay que volver a implementarlo (*Gestionar implementaciones → Editar →
       Nueva versión*) para que la URL use la versión nueva.
     - El script solo acepta pedidos con el TOKEN y solo lee o borra archivos dentro de "A+S Idiomas".
   - **Importante (Drive con Google Cloud):** una cuenta de servicio *no tiene cuota* y Google rechaza sus subidas a una carpeta
     de "Mi unidad" (`storageQuotaExceeded`). Si no tienes unidad compartida, usa OAuth con tu cuenta:
     1. Google Cloud → *APIs y servicios → Pantalla de consentimiento OAuth*: tipo *Interno* si tu cuenta es de
        la UCN (si es *Externo*, agrégate como usuario de prueba y luego pulsa *Publicar app*: en modo
        "Prueba" el token vence a los 7 días).
     2. *Credenciales → Crear credenciales → ID de cliente OAuth → App de escritorio* → descargar el JSON.
     3. `pip install google-auth-oauthlib` y `python obtener_token_drive.py client_secret_XXX.json`; inicia
        sesión con la cuenta dueña de la carpeta "A+S Idiomas" y pega el bloque `[google_oauth]` que imprime
        en `secrets.toml` (y en *Secrets* de Streamlit Cloud).
     4. Pon el ID de la carpeta en `DRIVE_CARPETA_RAIZ_ID`. Con esto la cuenta de servicio solo se usa para Sheets.
   - Cada archivo subido guarda en Supabase su `drive_file_id` y `drive_url` (enlace "Abrir en Drive"):
     `solicitud.cedula_drive_url / licencia_drive_url`, `documento_estudiante.drive_url`,
     `pago.comprobante_drive_url` y `certificado.drive_url`. En la app se ven como botón y se pueden descargar.
   - Sin Drive configurado la app funciona: los archivos quedan "pendientes de subir" en `PENDIENTES_DIR`
     y se reintentan desde Resumen o Solicitudes. En Streamlit Community Cloud ese disco no es permanente:
     configurar Drive antes de abrir el formulario público.
4. Ejecutar:
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```

## Primer uso (base vacía)

1. Ejecutar en Supabase los SQL de `../supabase/migrations` (ver `../supabase/README.md`).
2. Crear en *Authentication* la cuenta de coordinación y su fila en `idiomas.perfil`.
3. Entrar como coordinación → **Cursos**: crear la convocatoria y las ofertas reales.
4. **Resumen → Probar conexión con Drive** para confirmar que los archivos llegan a "A+S Idiomas".

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
