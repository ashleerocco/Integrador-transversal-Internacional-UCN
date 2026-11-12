-- =====================================================================
-- 0001 · Esquema base · Plataforma Cursos de Idiomas (UCN Internacional / PIE-UCN)
-- Grupo A (NECESARIO PARA FUNCIONAR). Idempotente: se puede ejecutar dos veces.
--
-- Todo vive en el esquema `idiomas` para NO tocar las tablas de la versión
-- anterior (esquema `public`). Regla transversal: el RUT / N° de pasaporte
-- normalizado es la clave de `estudiante` y `docente` y la llave foránea
-- (ON UPDATE CASCADE) de toda tabla relacionada con una persona.
-- =====================================================================

create schema if not exists idiomas;

-- ---------------------------------------------------------------------
-- Funciones de validación del documento (se usan en CHECKs)
-- ---------------------------------------------------------------------
create or replace function idiomas.normalizar_documento(p_doc text, p_tipo text default 'RUT')
returns text language sql immutable set search_path = '' as $$
  select case
    when p_doc is null then null
    when coalesce(p_tipo, 'RUT') = 'RUT' then
      (select case when length(r) > 1 and position('-' in r) = 0
                   then left(r, length(r) - 1) || '-' || right(r, 1) else r end
         from (select upper(regexp_replace(p_doc, '[.\s]', '', 'g')) as r) x)
    else upper(regexp_replace(p_doc, '\s', '', 'g'))
  end
$$;

create or replace function idiomas.rut_valido(p_rut text)
returns boolean language plpgsql immutable set search_path = '' as $$
declare
  cuerpo text; dv text; suma int := 0; mult int := 2; resto int; esperado text; i int;
begin
  if p_rut is null or p_rut !~ '^[0-9]{1,8}-[0-9K]$' then return false; end if;
  cuerpo := split_part(p_rut, '-', 1);
  dv := split_part(p_rut, '-', 2);
  for i in reverse length(cuerpo)..1 loop
    suma := suma + substr(cuerpo, i, 1)::int * mult;
    mult := case when mult = 7 then 2 else mult + 1 end;
  end loop;
  resto := 11 - (suma % 11);
  esperado := case resto when 11 then '0' when 10 then 'K' else resto::text end;
  return dv = esperado;
end $$;

create or replace function idiomas.documento_valido(p_doc text, p_tipo text)
returns boolean language sql immutable set search_path = '' as $$
  select case p_tipo
    when 'RUT' then idiomas.rut_valido(p_doc)
    when 'Pasaporte' then p_doc ~ '^[A-Z0-9]{5,20}$'
    else false end
$$;

-- ---------------------------------------------------------------------
-- Catálogos (los valores se cargan en 0002)
-- ---------------------------------------------------------------------
create table if not exists idiomas.idioma (
  codigo text primary key,                         -- 'ingles'
  nombre text not null unique,                     -- 'Inglés'
  codigo_proyecto text,                            -- centro de costo de la planilla de pagos
  codigo_proyecto_por_confirmar boolean not null default false,
  orden smallint not null default 0,
  activo boolean not null default true
);

create table if not exists idiomas.categoria_precio (
  codigo text primary key,                         -- 'ucn', 'egresado_funcionario', 'externo'
  nombre text not null,
  orden smallint not null default 0
);

create table if not exists idiomas.vinculo_ucn (
  codigo text primary key,                         -- 'pregrado', 'posgrado', 'egresado', 'externo', 'otros'
  nombre text not null unique,
  es_ucn boolean not null default false,           -- exige campus
  requiere_detalle boolean not null default false, -- "Otros" pide especificar
  categoria_precio text references idiomas.categoria_precio(codigo),
  orden smallint not null default 0
);

create table if not exists idiomas.vinculo_detalle (
  codigo text primary key,                         -- 'funcionario', 'otra_institucion', 'otro'
  nombre text not null unique,
  categoria_precio text not null references idiomas.categoria_precio(codigo),
  orden smallint not null default 0
);

create table if not exists idiomas.campus (
  codigo text primary key, nombre text not null unique, orden smallint not null default 0
);

create table if not exists idiomas.sede (
  codigo text primary key, nombre text not null unique, orden smallint not null default 0
);

create table if not exists idiomas.forma_pago (
  codigo text primary key, nombre text not null unique,
  num_cuotas smallint not null default 1, orden smallint not null default 0
);

create table if not exists idiomas.estado_asistencia (
  codigo char(1) primary key, nombre text not null, cuenta_para_porcentaje boolean not null,
  cuenta_como_presente boolean not null
);

-- Configuración editable (cabecera del formulario, reglas, nota mínima, etc.)
create table if not exists idiomas.config (
  clave text primary key,
  valor jsonb not null,
  descripcion text,
  actualizado_en timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Personas (PK = RUT / pasaporte normalizado)
-- ---------------------------------------------------------------------
create table if not exists idiomas.docente (
  rut text primary key,
  tipo_documento text not null default 'RUT' check (tipo_documento in ('RUT', 'Pasaporte')),
  nombres text not null,
  apellidos text not null,
  correo text unique,
  telefono text,
  activo boolean not null default true,
  es_demo boolean not null default false,
  creado_en timestamptz not null default now(),
  constraint docente_rut_valido check (idiomas.documento_valido(rut, tipo_documento))
);

create table if not exists idiomas.estudiante (
  -- Algunos campos admiten NULL solo para datos migrados de la versión anterior;
  -- el formulario (público y de coordinación) los exige todos.
  rut text primary key,
  tipo_documento text not null default 'RUT' check (tipo_documento in ('RUT', 'Pasaporte')),
  correo text not null,
  nombres text not null,
  apellido_paterno text not null,
  apellido_materno text,
  sexo text check (sexo in ('Hombre', 'Mujer', 'Prefiero no decirlo')),
  genero text check (genero in ('Femenino', 'Masculino', 'Otro')),
  nombre_social text,
  pronombres text,
  fecha_nacimiento date check (fecha_nacimiento >= date '1900-01-01'),
  carrera text,
  campus text references idiomas.campus(codigo),
  campus_otro text,
  nacionalidad text not null default 'Chile',
  vinculo text not null references idiomas.vinculo_ucn(codigo),
  vinculo_detalle text references idiomas.vinculo_detalle(codigo),
  telefono text,
  salud_tiene_condicion boolean not null default false,
  salud_requerimiento text,
  consentimiento_datos boolean not null default false,
  fecha_consentimiento timestamptz,
  origen text not null default 'solicitud' check (origen in ('solicitud', 'coordinacion', 'migracion')),
  es_demo boolean not null default false,
  creado_en timestamptz not null default now(),
  actualizado_en timestamptz not null default now(),
  constraint estudiante_rut_valido check (idiomas.documento_valido(rut, tipo_documento)),
  constraint estudiante_detalle_otros check (vinculo <> 'otros' or vinculo_detalle is not null)
);
create index if not exists estudiante_correo_idx on idiomas.estudiante (lower(correo));
create index if not exists estudiante_vinculo_idx on idiomas.estudiante (vinculo);

-- Documentos adjuntos del estudiante (cédula, licencia). Solo id/enlace de Drive.
create table if not exists idiomas.documento_estudiante (
  rut_estudiante text not null references idiomas.estudiante(rut) on update cascade on delete cascade,
  tipo text not null check (tipo in ('cedula', 'licencia')),
  drive_file_id text,
  drive_url text,
  nombre_archivo text,
  estado_archivo text not null default 'subido' check (estado_archivo in ('subido', 'pendiente_subir')),
  actualizado_en timestamptz not null default now(),
  primary key (rut_estudiante, tipo)
);

-- Usuarios de la plataforma (Supabase Auth) y su rol
create table if not exists idiomas.perfil (
  id uuid primary key references auth.users(id) on delete cascade,
  nombre text not null,
  rol text not null check (rol in ('coordinacion', 'docente', 'alumno')),
  rut_docente text references idiomas.docente(rut) on update cascade,
  rut_estudiante text references idiomas.estudiante(rut) on update cascade,
  es_demo boolean not null default false,
  constraint perfil_rut_segun_rol check (
    (rol = 'docente' and rut_docente is not null) or
    (rol = 'alumno' and rut_estudiante is not null) or
    (rol = 'coordinacion'))
);

-- ---------------------------------------------------------------------
-- Convocatorias y ofertas (id propio)
-- ---------------------------------------------------------------------
create table if not exists idiomas.convocatoria (
  id bigint generated always as identity primary key,
  nombre text not null,                            -- 'Cursos Idiomas PIE-UCN 1-2026'
  periodo text not null,                           -- '1-2026'
  fecha_apertura date not null,
  fecha_cierre date not null,
  fecha_confirmacion date,                         -- confirmación del curso por e-mail
  fecha_inicio_curso date,
  fecha_fin_curso date,
  fechas_cuotas date[] not null default '{}',
  estado text not null default 'borrador' check (estado in ('borrador', 'abierta', 'cerrada')),
  es_demo boolean not null default false,
  creado_en timestamptz not null default now(),
  constraint convocatoria_fechas check (fecha_cierre >= fecha_apertura
    and (fecha_fin_curso is null or fecha_inicio_curso is null or fecha_fin_curso >= fecha_inicio_curso))
);

create table if not exists idiomas.oferta (
  id bigint generated always as identity primary key,
  convocatoria_id bigint not null references idiomas.convocatoria(id) on delete restrict,
  idioma text not null references idiomas.idioma(codigo),
  nivel text not null,                             -- 'Básico A1', 'A1.1', 'Preparación TOEFL'
  modalidad text not null check (modalidad in ('Presencial', 'Virtual')),
  sede text not null references idiomas.sede(codigo),
  dias smallint[] not null default '{}',           -- ISO: 1 = lunes … 7 = domingo
  hora_inicio time,
  hora_fin time,
  horario_texto text,                              -- 'a convenir lunes, jueves y viernes'
  rut_docente text references idiomas.docente(rut) on update cascade,
  cupo_minimo int not null default 5 check (cupo_minimo > 0),
  cupo_maximo int not null default 10,
  valor_universal numeric(12,0) check (valor_universal >= 0), -- si se fija, aplica a todos los vínculos
  num_sesiones_plan int check (num_sesiones_plan > 0),
  estado text not null default 'abierta'
    check (estado in ('abierta', 'confirmada', 'no_se_dicta', 'finalizada')),
  es_demo boolean not null default false,
  creado_en timestamptz not null default now(),
  constraint oferta_cupos check (cupo_maximo >= cupo_minimo),
  constraint oferta_horas check (hora_fin is null or hora_inicio is null or hora_fin > hora_inicio)
);
create index if not exists oferta_convocatoria_idx on idiomas.oferta (convocatoria_id);
create index if not exists oferta_docente_idx on idiomas.oferta (rut_docente);

create table if not exists idiomas.oferta_valor (
  oferta_id bigint not null references idiomas.oferta(id) on delete cascade,
  categoria_precio text not null references idiomas.categoria_precio(codigo),
  valor numeric(12,0) not null check (valor >= 0),
  primary key (oferta_id, categoria_precio)
);

-- ---------------------------------------------------------------------
-- Solicitudes del formulario público (id propio + RUT indexado)
-- ---------------------------------------------------------------------
create table if not exists idiomas.solicitud (
  id bigint generated always as identity primary key,
  codigo text not null unique,                     -- código entregado a la persona (SOL-XXXXXX)
  estado text not null default 'pendiente' check (estado in ('pendiente', 'aceptada', 'rechazada')),
  -- B. contacto y curso
  correo text not null,
  idioma text not null references idiomas.idioma(codigo),
  modalidad text not null check (modalidad in ('Presencial', 'Virtual')),
  oferta_id bigint references idiomas.oferta(id),
  otro_idioma_nivel text,
  -- C. información personal
  nombres text not null,
  apellido_paterno text not null,
  apellido_materno text not null,
  sexo text not null check (sexo in ('Hombre', 'Mujer', 'Prefiero no decirlo')),
  genero text not null check (genero in ('Femenino', 'Masculino', 'Otro')),
  nombre_social text,
  pronombres text not null,
  tipo_documento text not null check (tipo_documento in ('RUT', 'Pasaporte')),
  rut text not null,
  fecha_nacimiento date not null check (fecha_nacimiento >= date '1900-01-01'),
  cedula_drive_file_id text, cedula_drive_url text,
  cedula_estado text not null default 'subido' check (cedula_estado in ('subido', 'pendiente_subir')),
  licencia_drive_file_id text, licencia_drive_url text,
  licencia_estado text not null default 'subido' check (licencia_estado in ('subido', 'pendiente_subir')),
  carrera text not null,
  campus text references idiomas.campus(codigo),
  campus_otro text,
  nacionalidad text not null,
  vinculo text not null references idiomas.vinculo_ucn(codigo),
  vinculo_detalle text references idiomas.vinculo_detalle(codigo),
  telefono text,
  salud_tiene_condicion boolean not null,
  salud_requerimiento text,
  -- D. pago y consentimientos
  forma_pago text not null references idiomas.forma_pago(codigo),
  acepta_terminos boolean not null check (acepta_terminos),
  consentimiento_datos boolean not null check (consentimiento_datos),
  fecha_consentimiento timestamptz not null default now(),
  -- revisión
  motivo_rechazo text,
  revisado_por uuid references auth.users(id),
  revisado_en timestamptz,
  es_demo boolean not null default false,
  creado_en timestamptz not null default now(),
  constraint solicitud_rut_valido check (idiomas.documento_valido(rut, tipo_documento)),
  constraint solicitud_oferta_u_otro check (oferta_id is not null or nullif(trim(otro_idioma_nivel), '') is not null),
  constraint solicitud_salud check (not salud_tiene_condicion or nullif(trim(salud_requerimiento), '') is not null),
  constraint solicitud_detalle_otros check (vinculo <> 'otros' or vinculo_detalle is not null)
);
create index if not exists solicitud_rut_idx on idiomas.solicitud (rut);
create index if not exists solicitud_estado_idx on idiomas.solicitud (estado);
create index if not exists solicitud_correo_idx on idiomas.solicitud (lower(correo));
-- Duplicados: misma persona + misma oferta con solicitud vigente
create unique index if not exists solicitud_vigente_uk on idiomas.solicitud (rut, oferta_id)
  where estado in ('pendiente', 'aceptada') and oferta_id is not null;

-- ---------------------------------------------------------------------
-- Inscripción (PK compuesta con el RUT)
-- ---------------------------------------------------------------------
create table if not exists idiomas.inscripcion (
  rut_estudiante text not null references idiomas.estudiante(rut) on update cascade,
  oferta_id bigint not null references idiomas.oferta(id),
  estado text not null default 'inscrito' check (estado in ('inscrito', 'retirado')),
  origen text not null check (origen in ('solicitud', 'coordinacion', 'migracion')),
  solicitud_id bigint references idiomas.solicitud(id),
  forma_pago text references idiomas.forma_pago(codigo),
  monto_total numeric(12,0) check (monto_total >= 0),  -- valor según vínculo (editable)
  fecha_inscripcion date not null default current_date,
  es_demo boolean not null default false,
  primary key (rut_estudiante, oferta_id)
);
create index if not exists inscripcion_oferta_idx on idiomas.inscripcion (oferta_id);

-- ---------------------------------------------------------------------
-- Pagos (id propio + RUT indexado) y base derivada "estudiantes pagados"
-- ---------------------------------------------------------------------
create table if not exists idiomas.pago (
  id bigint generated always as identity primary key,
  rut_estudiante text not null,
  oferta_id bigint not null,
  fecha date not null,
  monto numeric(12,0) not null check (monto > 0),
  banco text,
  n_transaccion text,
  n_boleta text,                                   -- 'C9-1146'
  forma_pago text references idiomas.forma_pago(codigo),
  n_cuota smallint check (n_cuota between 1 and 12),
  estado text not null default 'confirmado' check (estado in ('confirmado', 'anulado')),
  motivo_anulacion text,
  comprobante_drive_file_id text,
  comprobante_drive_url text,
  comprobante_estado text check (comprobante_estado in ('subido', 'pendiente_subir')),
  observacion text,
  registrado_por uuid references auth.users(id),
  es_demo boolean not null default false,
  creado_en timestamptz not null default now(),
  foreign key (rut_estudiante, oferta_id)
    references idiomas.inscripcion(rut_estudiante, oferta_id) on update cascade
);
create index if not exists pago_rut_idx on idiomas.pago (rut_estudiante);
create index if not exists pago_oferta_idx on idiomas.pago (oferta_id);
create index if not exists pago_fecha_idx on idiomas.pago (fecha);

create table if not exists idiomas.estudiante_pagado (
  rut text not null,
  oferta_id bigint not null,
  monto_total numeric(12,0),
  monto_pagado numeric(12,0) not null default 0,
  estado_pago text not null check (estado_pago in ('parcial', 'total')),
  fecha_primer_pago date not null,
  actualizado_en timestamptz not null default now(),
  primary key (rut, oferta_id),
  foreign key (rut, oferta_id)
    references idiomas.inscripcion(rut_estudiante, oferta_id) on update cascade on delete cascade
);
create index if not exists estudiante_pagado_oferta_idx on idiomas.estudiante_pagado (oferta_id);

-- ---------------------------------------------------------------------
-- Sesiones, asistencia y notas
-- ---------------------------------------------------------------------
create table if not exists idiomas.sesion (
  oferta_id bigint not null references idiomas.oferta(id) on delete cascade,
  fecha date not null,
  numero int,
  suspendida boolean not null default false,       -- S en toda la columna (feriado, suspensión)
  motivo text,
  primary key (oferta_id, fecha)
);

create table if not exists idiomas.asistencia (
  rut_estudiante text not null,
  oferta_id bigint not null,
  fecha date not null,
  estado char(1) not null references idiomas.estado_asistencia(codigo),
  actualizado_en timestamptz not null default now(),
  primary key (rut_estudiante, oferta_id, fecha),
  foreign key (rut_estudiante, oferta_id)
    references idiomas.inscripcion(rut_estudiante, oferta_id) on update cascade,
  foreign key (oferta_id, fecha) references idiomas.sesion(oferta_id, fecha) on update cascade on delete cascade
);
create index if not exists asistencia_oferta_idx on idiomas.asistencia (oferta_id);

create table if not exists idiomas.nota (
  rut_estudiante text not null,
  oferta_id bigint not null,
  nota1 numeric(2,1) check (nota1 between 1.0 and 7.0),
  nota2 numeric(2,1) check (nota2 between 1.0 and 7.0),
  nota3 numeric(2,1) check (nota3 between 1.0 and 7.0),
  porcentaje1 numeric(5,1) check (porcentaje1 between 0 and 100),
  porcentaje2 numeric(5,1) check (porcentaje2 between 0 and 100),
  porcentaje3 numeric(5,1) check (porcentaje3 between 0 and 100),
  -- Nota final: promedio de las 3 notas, 1 decimal, SOLO cuando las 3 existen
  nota_final numeric(2,1) generated always as (
    case when nota1 is not null and nota2 is not null and nota3 is not null
         then round((nota1 + nota2 + nota3) / 3.0, 1) end) stored,
  actualizado_en timestamptz not null default now(),
  primary key (rut_estudiante, oferta_id),
  foreign key (rut_estudiante, oferta_id)
    references idiomas.inscripcion(rut_estudiante, oferta_id) on update cascade
);

-- ---------------------------------------------------------------------
-- Certificados
-- ---------------------------------------------------------------------
create table if not exists idiomas.certificado (
  rut_estudiante text not null,
  oferta_id bigint not null,
  nombre_completo text,                            -- copia al momento de solicitar (lo llena un trigger)
  curso text,                                      -- idem
  estado text not null default 'solicitado'
    check (estado in ('solicitado', 'pendiente', 'firmado', 'entregado')),
  fecha_solicitada date,
  fecha_pendiente date,
  fecha_firma date,
  fecha_entrega date,
  drive_file_id text,
  drive_url text,
  observacion text,
  actualizado_por uuid references auth.users(id),
  es_demo boolean not null default false,
  actualizado_en timestamptz not null default now(),
  primary key (rut_estudiante, oferta_id),
  foreign key (rut_estudiante, oferta_id)
    references idiomas.inscripcion(rut_estudiante, oferta_id) on update cascade,
  constraint certificado_entregado_con_archivo check (estado <> 'entregado' or drive_file_id is not null)
);

-- ---------------------------------------------------------------------
-- Bitácora de sincronización con Google Sheets (sin datos personales)
-- ---------------------------------------------------------------------
create table if not exists idiomas.sync_log (
  id bigint generated always as identity primary key,
  tabla text not null,
  estado text not null check (estado in ('ok', 'error', 'reintentado')),
  filas int,
  intentos int not null default 1,
  detalle text,                                    -- solo tipo de error, nunca datos
  creado_en timestamptz not null default now(),
  resuelto_en timestamptz
);
create index if not exists sync_log_estado_idx on idiomas.sync_log (estado, tabla);

-- Columnas es_demo añadidas por si la tabla ya existía de una ejecución anterior
alter table idiomas.estudiante add column if not exists es_demo boolean not null default false;
-- Si la tabla existía de una versión previa de este script, se alinean las columnas opcionales
alter table idiomas.estudiante alter column apellido_materno drop not null,
  alter column sexo drop not null, alter column genero drop not null, alter column pronombres drop not null,
  alter column fecha_nacimiento drop not null, alter column carrera drop not null;
