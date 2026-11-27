# Base de datos (Supabase) · Plataforma de Cursos de Idiomas (v1, sin datos de prueba)

Todo el modelo vive en el esquema **`idiomas`**. Esta carpeta trae solo lo necesario para que la app
funcione con datos reales: **no** incluye datos ficticios, usuarios de demostración ni pruebas.

```
supabase/
├── migrations/                     NECESARIO PARA FUNCIONAR
│   ├── 0001_esquema_base.sql       tablas, PK/FK por RUT, restricciones, índices
│   ├── 0002_catalogos.sql          idiomas (+ código de proyecto), vínculos, campus, sedes, formas de pago, P/A/J/S, config
│   ├── 0003_vistas_funciones_triggers.sql
│   └── 0004_rls.sql                permisos y políticas por rol
└── opcional/migrar_desde_v1.sql    copia public.* (app antigua) → idiomas.* sin borrar nada
```

## Puesta en marcha

1. **SQL Editor**, en este orden: `0001` → `0002` → `0003` → `0004`. Se pueden volver a ejecutar sin errores.
2. Marcar el entorno como producción (impide cargar datos de demostración por error):
   ```sql
   insert into idiomas.config (clave, valor) values ('entorno', '"produccion"')
   on conflict (clave) do update set valor = excluded.valor;
   ```
3. **Exponer el esquema a la API:** *Project Settings → API → Exposed schemas* → agregar `idiomas`.
4. Crear las cuentas reales en *Authentication* y su fila en `idiomas.perfil`:
   ```sql
   insert into idiomas.perfil (id, nombre, rol) values ('<uuid de auth.users>', 'Coordinación Idiomas', 'coordinacion');
   insert into idiomas.perfil (id, nombre, rol, rut_docente) values ('<uuid>', 'Nombre Docente', 'docente', '12345678-5');
   insert into idiomas.perfil (id, nombre, rol, rut_estudiante) values ('<uuid>', 'Nombre Alumno', 'alumno', '12345678-5');
   ```
5. Opcional: `opcional/migrar_desde_v1.sql` para traer datos de la app antigua (esquema `public`). Antes,
   completar `idiomas._mapa_docente` (los docentes antiguos no tienen RUT) y revisar
   `select * from idiomas._migracion_reporte`. Si esos datos eran de prueba, **no** conviene migrarlos.

Las reglas de negocio (validación de RUT, anti-duplicados, cálculo de nota final, permisos por rol, etc.)
viven en la base de datos y son las mismas de la v2; ver `../../plataformav2/supabase/README.md`.
