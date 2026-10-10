-- =====================================================================
-- Sistema de gestión - Sección de Idiomas UCN Internacional
-- Esquema inicial para Supabase (PostgreSQL)
-- Cómo usarlo: Supabase > SQL Editor > New query > pegar > Run
-- Los valores marcados con "POR CONFIRMAR" dependen de la coordinadora.
-- =====================================================================

-- ---------- 1. Tablas de apoyo (catálogos) ----------

create table tipo_estudiante (
  id      smallint generated always as identity primary key,
  nombre  text not null unique          -- RF-01
);

insert into tipo_estudiante (nombre) values
  ('Estudiante UCN pregrado'),
  ('Estudiante UCN posgrado'),
  ('Egresado'),
  ('Externo');

create table idioma (
  id      smallint generated always as identity primary key,
  nombre  text not null unique          -- Inglés, Francés, etc.
);

create table curso (
  id         bigint generated always as identity primary key,
  idioma_id  smallint not null references idioma(id),
  nivel      text not null,             -- A1, A2, B1...
  nombre     text not null,
  unique (idioma_id, nivel)
);

-- ---------- 2. Personas ----------

create table estudiante (
  id                  bigint generated always as identity primary key,
  tipo_documento      text not null default 'RUT' check (tipo_documento in ('RUT','Pasaporte','Otro')),
  documento           text not null unique,
  nombres             text not null,
  apellido_paterno    text not null,
  apellido_materno    text,
  nombre_social       text,
  correo              text not null unique,
  telefono            text,
  nacionalidad        text,
  unidad_ucn          text,             -- carrera / unidad (si aplica)
  campus              text,
  tipo_estudiante_id  smallint not null references tipo_estudiante(id),  -- RF-01
  creado_en           timestamptz not null default now()
);

create table docente (
  id      bigint generated always as identity primary key,
  nombre  text not null,
  correo  text unique
);

-- Perfil de usuario de la app (RF-06): vincula Supabase Auth con un rol
create table perfil (
  id          uuid primary key references auth.users(id) on delete cascade,
  nombre      text not null,
  rol         text not null check (rol in ('coordinadora','docente','secretaria_general')),
  docente_id  bigint references docente(id)
);

-- ---------- 3. Oferta, inscripción y pago ----------

-- Una "oferta" es un curso dictado en un período (convocatoria)
create table oferta_curso (
  id            bigint generated always as identity primary key,
  curso_id      bigint not null references curso(id),
  periodo       text not null,                         -- ej: '1-2026'
  docente_id    bigint references docente(id),
  cupo_minimo   int not null check (cupo_minimo > 0),  -- POR CONFIRMAR: ¿igual para todos?
  cupo_maximo   int check (cupo_maximo is null or cupo_maximo >= cupo_minimo),
  fecha_inicio  date,
  fecha_termino date,
  estado        text not null default 'convocatoria'
                check (estado in ('convocatoria','abierto','cerrado_sin_cupos','en_curso','finalizado')),
  unique (curso_id, periodo)
);

create table inscripcion (
  id                 bigint generated always as identity primary key,
  estudiante_id      bigint not null references estudiante(id),
  oferta_id          bigint not null references oferta_curso(id),
  estado             text not null default 'pendiente_pago'
                     check (estado in ('pendiente_pago','inscrito','retirado','aprobado','reprobado')),
  fecha_inscripcion  date not null default current_date,
  nota_final         numeric(2,1) check (nota_final between 1.0 and 7.0),
  unique (estudiante_id, oferta_id)
);

create table pago (                                       -- RF-07
  id              bigint generated always as identity primary key,
  inscripcion_id  bigint not null references inscripcion(id) on delete cascade,
  monto           numeric(12,0) not null check (monto >= 0),
  fecha_pago      date,
  estado          text not null default 'pendiente'
                  check (estado in ('pendiente','pagado','devuelto')),  -- 'devuelto': POR CONFIRMAR
  observacion     text
);

-- ---------- 4. Asistencia y notas ----------

create table sesion (
  id         bigint generated always as identity primary key,
  oferta_id  bigint not null references oferta_curso(id) on delete cascade,
  numero     int not null,
  fecha      date,
  unique (oferta_id, numero)
);

create table asistencia (                                 -- RF-04
  id              bigint generated always as identity primary key,
  sesion_id       bigint not null references sesion(id) on delete cascade,
  inscripcion_id  bigint not null references inscripcion(id) on delete cascade,
  estado          text not null check (estado in ('P','A','J')),  -- Presente, Ausente, Justificado
  unique (sesion_id, inscripcion_id)
);
-- POR CONFIRMAR: en el Excel 1-2026 aparece también la letra "S" en una misma
-- sesión para todos los estudiantes. Parece una sesión sin clase o de evaluación.

create table nota (                                       -- RF-05
  id              bigint generated always as identity primary key,
  inscripcion_id  bigint not null references inscripcion(id) on delete cascade,
  numero          smallint not null check (numero between 1 and 3),
  porcentaje      numeric(5,2) check (porcentaje between 0 and 100),
  nota            numeric(2,1) not null check (nota between 1.0 and 7.0),
  unique (inscripcion_id, numero)
);

-- ---------- 5. Certificados ----------

create table certificado (                                -- RF-09
  id                bigint generated always as identity primary key,
  inscripcion_id    bigint not null unique references inscripcion(id) on delete cascade,
  cumple_requisitos boolean not null default false,
  estado            text not null default 'pendiente'
                    check (estado in ('pendiente','solicitado','firmado','entregado')),
  fecha_solicitud   date,
  fecha_firma       date,
  fecha_entrega     date,
  observacion       text
);

-- ---------- 6. Vistas para la app y los indicadores ----------

-- % de asistencia por inscripción (RF-04).
-- POR CONFIRMAR: aquí solo cuenta 'P'; si 'J' debe contar como asistencia, agrégalo.
create view v_asistencia_inscripcion as
select
  i.id as inscripcion_id,
  count(a.id) as sesiones_registradas,
  count(a.id) filter (where a.estado = 'P') as presentes,
  round(100.0 * count(a.id) filter (where a.estado = 'P') / nullif(count(a.id), 0), 1) as porcentaje_asistencia
from inscripcion i
left join asistencia a on a.inscripcion_id = i.id
group by i.id;

-- Inscritos vs. cupo mínimo por oferta (RF-03)
create view v_inscritos_vs_minimo as
select
  o.id as oferta_id,
  c.nombre as curso,
  o.periodo,
  o.cupo_minimo,
  count(i.id) filter (where i.estado in ('inscrito','aprobado','reprobado')) as inscritos,
  (count(i.id) filter (where i.estado in ('inscrito','aprobado','reprobado'))) >= o.cupo_minimo as alcanza_minimo
from oferta_curso o
join curso c on c.id = o.curso_id
left join inscripcion i on i.oferta_id = o.id
group by o.id, c.nombre, o.periodo, o.cupo_minimo;

-- ---------- 7. Seguridad ----------
-- Se activa RLS en todas las tablas. Sin políticas, la clave pública (anon) no
-- puede leer ni escribir nada. La app Streamlit usa la clave de servicio guardada
-- en st.secrets (NUNCA en GitHub). Las políticas por rol se agregan después.
alter table tipo_estudiante enable row level security;
alter table idioma          enable row level security;
alter table curso           enable row level security;
alter table estudiante      enable row level security;
alter table docente         enable row level security;
alter table perfil          enable row level security;
alter table oferta_curso    enable row level security;
alter table inscripcion     enable row level security;
alter table pago            enable row level security;
alter table sesion          enable row level security;
alter table asistencia      enable row level security;
alter table nota            enable row level security;
alter table certificado     enable row level security;

-- Índices útiles para consultas frecuentes
create index on inscripcion (oferta_id);
create index on asistencia (inscripcion_id);
create index on pago (inscripcion_id);
