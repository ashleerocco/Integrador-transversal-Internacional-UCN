-- =====================================================================
-- 0002 · Catálogos reales y configuración (Grupo A). Idempotente.
-- Fuente: formulario "Cursos Idiomas PIE-UCN 1-2026" y planilla
-- "Pagos Cursos de Idiomas 2025.xlsx". ON CONFLICT ... DO NOTHING para no
-- pisar cambios hechos después por la coordinación.
-- =====================================================================

alter table idiomas.vinculo_detalle add column if not exists es_ucn boolean not null default false;

insert into idiomas.idioma (codigo, nombre, codigo_proyecto, codigo_proyecto_por_confirmar, orden) values
  ('ingles',    'Inglés',    '20104063', false, 1),
  ('aleman',    'Alemán',    '20104064', false, 2),
  ('frances',   'Francés',   '20104077', false, 3),
  ('coreano',   'Coreano',   '20104167', false, 4),
  ('italiano',  'Italiano',  '20104168', false, 5),
  -- La planilla repite 20104063 (Inglés) en la hoja de Portugués: se guarda tal cual y se marca
  ('portugues', 'Portugués', '20104063', true,  6)
on conflict (codigo) do nothing;

insert into idiomas.categoria_precio (codigo, nombre, orden) values
  ('ucn', 'Estudiantes UCN/CEDUC', 1),
  ('egresado_funcionario', 'Egresados/ALUMNI/Funcionarios UCN/estudiantes de otras instituciones', 2),
  ('externo', 'Externos', 3)
on conflict (codigo) do nothing;

insert into idiomas.vinculo_ucn (codigo, nombre, es_ucn, requiere_detalle, categoria_precio, orden) values
  ('pregrado', 'Estudiante UCN de pregrado', true,  false, 'ucn', 1),
  ('posgrado', 'Estudiante UCN de posgrado', true,  false, 'ucn', 2),
  ('egresado', 'Egresado/a',                 false, false, 'egresado_funcionario', 3),
  ('externo',  'Externo/a',                  false, false, 'externo', 4),
  ('otros',    'Otros',                      false, true,  null, 5)   -- el precio sale del detalle
on conflict (codigo) do nothing;

insert into idiomas.vinculo_detalle (codigo, nombre, categoria_precio, es_ucn, orden) values
  ('funcionario',      'Funcionario/Académico',           'egresado_funcionario', true,  1),
  ('otra_institucion', 'Estudiante de otra institución',  'egresado_funcionario', false, 2),
  ('otro',             'Otro',                            'externo',              false, 3)
on conflict (codigo) do nothing;

insert into idiomas.campus (codigo, nombre, orden) values
  ('antofagasta', 'Casa Central - Antofagasta', 1),
  ('coquimbo',    'Campus Guayacán - Coquimbo', 2),
  ('otro',        'Otro', 3)
on conflict (codigo) do nothing;

insert into idiomas.sede (codigo, nombre, orden) values
  ('antofagasta', 'Antofagasta', 1),
  ('coquimbo',    'Coquimbo', 2),
  ('virtual',     'Virtual', 3)
on conflict (codigo) do nothing;

insert into idiomas.forma_pago (codigo, nombre, num_cuotas, orden) values
  ('contado',      'Al contado / 1 pago', 1, 1),
  ('tres_cuotas',  'Tres cuotas', 3, 2),
  ('unidad_beca',  'Pago unidad de origen / Beca adjudicada', 1, 3),
  ('sindicato',    'Sindicatos UCN', 1, 4)
on conflict (codigo) do nothing;

-- S = sesión suspendida (aparece en toda la columna de una fecha en la planilla
-- "TODOS LOS CURSOS 1-2026"); no cuenta para el porcentaje.
insert into idiomas.estado_asistencia (codigo, nombre, cuenta_para_porcentaje, cuenta_como_presente) values
  ('P', 'Presente',    true,  true),
  ('A', 'Ausente',     true,  false),
  ('J', 'Justificado', true,  false),
  ('S', 'Suspendida',  false, false)
on conflict (codigo) do nothing;

insert into idiomas.config (clave, valor, descripcion) values
  ('cabecera_formulario', to_jsonb(
     'Cada nivel consta de 50 horas pedagógicas. 2 sesiones a la semana con docente (90 min) + LMS UCN (Moodle o Cambridge One).'::text),
     'Texto principal de la cabecera del formulario'),
  ('cabecera_detalle', to_jsonb(
     'Cursos grupales con un mínimo de 5 y un máximo de 10 participantes por nivel. Al finalizar el curso se entrega constancia de participación con la cantidad de horas cursadas y el nivel alcanzado.'::text),
     'Segundo párrafo de la cabecera'),
  ('correo_contacto', to_jsonb('idiomas.pie@ucn.cl'::text), 'Correo de consultas'),
  ('web', to_jsonb('https://idiomaspie.ucn.cl'::text), 'Sitio web de la sección'),
  ('calendly_url', to_jsonb('https://calendly.com/jocelyn-moraleda'::text), 'Cita informativa virtual'),
  ('mineduc_url', to_jsonb('https://certificados.mineduc.cl/mvc/home/index'::text), 'Ayuda para descargar la licencia de Enseñanza Media'),
  ('regla_ingreso_pagado', to_jsonb('primer_pago'::text),
     'Cuándo entra un alumno a "Estudiantes pagados": primer_pago (primera cuota pagada) | pago_total'),
  ('limite_solicitudes_24h', to_jsonb(3), 'Máximo de solicitudes por correo o RUT en 24 horas (anti-spam)'),
  ('certificado_nota_minima', 'null'::jsonb, 'Nota mínima para certificado. null = desactivado'),
  ('certificado_asistencia_minima', 'null'::jsonb, 'Asistencia mínima (%) para certificado. null = desactivado')
on conflict (clave) do nothing;
