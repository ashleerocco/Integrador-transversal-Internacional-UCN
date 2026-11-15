# Base de datos (Supabase) · Plataforma de Cursos de Idiomas

Todo el modelo nuevo vive en el esquema **`idiomas`**. El esquema `public` de la
versión anterior **no se toca** (se puede migrar con el script opcional).

```
supabase/
├── migrations/                     ← Grupo A: NECESARIO PARA FUNCIONAR (siempre)
│   ├── 0001_esquema_base.sql       tablas, PK/FK por RUT, restricciones, índices
│   ├── 0002_catalogos.sql          idiomas (+ código de proyecto), vínculos, campus, sedes, formas de pago, P/A/J/S, config
│   ├── 0003_vistas_funciones_triggers.sql
│   └── 0004_rls.sql                permisos y políticas por rol
├── seed/                           ← Grupo B: SOLO DESARROLLO
│   ├── seed_demo.sql               datos ficticios es_demo (aborta si detecta producción)
│   └── reset_demo.sql              borra solo es_demo
├── tests/verificacion.sql          30 pruebas de aceptación (se revierten solas)
└── opcional/migrar_desde_v1.sql    copia public.* → idiomas.* sin borrar nada
```

## Orden de ejecución

> ⚠️ **No ejecutar en producción mientras se valida.** El proyecto "Idiomas UCN Project"
> es hoy el único entorno y contiene datos. Crea primero una **rama de desarrollo**
> (Supabase → Branches → *Create branch*) o un proyecto nuevo de pruebas, y ejecuta ahí.

1. **SQL Editor** (rama/proyecto de pruebas), en este orden:
   `0001` → `0002` → `0003` → `0004`. Se pueden volver a ejecutar sin errores.
2. **Exponer el esquema a la API:** *Project Settings → API → Exposed schemas* → agregar `idiomas`
   (y en *Extra search path* no hace falta nada más).
3. **Solo en desarrollo**, marca el entorno y carga la demo:
   ```sql
   insert into idiomas.config (clave, valor) values ('entorno', '"desarrollo"')
   on conflict (clave) do update set valor = excluded.valor;
   ```
   Luego `seed/seed_demo.sql`. Al final muestra la **contraseña aleatoria** de los 3 usuarios demo
   (`coordinacion@`, `docente1@`, `alumno@demo.ucn.test`). No hay contraseñas en el repositorio.
4. `tests/verificacion.sql` → debe mostrar 30 filas **OK**.
5. `seed/reset_demo.sql` borra la demo (solo filas `es_demo`). Se puede volver a sembrar.

### Pasar a producción (cuando la coordinación lo apruebe)
1. Ejecutar `0001`–`0004` en producción (no toca `public`).
2. Opcional: `opcional/migrar_desde_v1.sql`. Antes, completar `idiomas._mapa_docente`
   (los docentes antiguos no tienen RUT). Revisar `select * from idiomas._migracion_reporte`.
   En la revisión de nov-2026 los 10 estudiantes de `public` tenían documentos y correos de prueba:
   probablemente **no** conviene migrarlos.
3. Crear las cuentas reales en *Authentication* y su fila en `idiomas.perfil`:
   ```sql
   insert into idiomas.perfil (id, nombre, rol) values ('<uuid de auth.users>', 'Coordinación Idiomas', 'coordinacion');
   insert into idiomas.perfil (id, nombre, rol, rut_docente) values ('<uuid>', 'Nombre Docente', 'docente', '12345678-5');
   insert into idiomas.perfil (id, nombre, rol, rut_estudiante) values ('<uuid>', 'Nombre Alumno', 'alumno', '12345678-5');
   ```
4. **Nunca** ejecutar el seed en producción (además, aborta solo).

## Reglas que viven en la base de datos

| Regla | Dónde |
|---|---|
| RUT/pasaporte normalizado y validado (DV solo si es RUT) | `normalizar_documento`, `documento_valido`, CHECK + trigger `normalizar` |
| PK = RUT en `estudiante`/`docente`; FK compuestas `(rut, oferta_id)` con `ON UPDATE CASCADE` | 0001 |
| Formulario público: anon solo puede `INSERT` en `solicitud`; anti-duplicado (misma persona + oferta vigente) y límite diario por correo/RUT | política `publico_inserta_solicitud`, índice `solicitud_vigente_uk`, trigger `validar` |
| Lectura pública mínima sin políticas anon | funciones `ofertas_publicas()`, `convocatorias_publicas()`, `catalogos_publicos()`, `proxima_convocatoria()` |
| Aceptar solicitud = upsert por RUT + inscripción (sin duplicar) | `aceptar_solicitud()`, `inscribir_estudiante()` |
| Pago confirmado → `estudiante_pagado`; anular recalcula | trigger `recalcular_pagado`, `config.regla_ingreso_pagado` (`primer_pago` \| `pago_total`) |
| Asistencia/notas/certificados solo para pagados | trigger `requiere_pagado`, RLS docente |
| Nota final = promedio de 3 notas, 1 decimal, solo con las 3 | columna generada `nota.nota_final` |
| Certificado: requiere notas completas; fechas automáticas; "Entregado" exige PDF; retroceso solo confirmado | trigger `reglas`, `cambiar_estado_certificado()` |
| Resumen con ofertas en 0 inscritos | vista `v_inscritos_vs_minimo` (LEFT JOIN) |

Vistas: `v_oferta`, `v_inscritos_vs_minimo`, `v_estudiante`, `v_estudiante_pagado`, `v_pago`, `v_pagos_mes`,
`v_asistencia_resumen`, `v_certificable`, `v_solicitud`, `v_nota` (todas `security_invoker`, respetan RLS).
