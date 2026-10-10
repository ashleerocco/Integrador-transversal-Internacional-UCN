-- =====================================================================
-- Datos de PRUEBA (100% ficticios) - Sección de Idiomas
-- Ejecutar DESPUÉS de supabase_schema_idiomas.sql
-- Contenido: 2 idiomas, 3 cursos, 2 docentes, 2 ofertas, 10 estudiantes,
--            11 inscripciones, pagos, 6 sesiones con asistencia, notas y certificados.
-- No usa ningún dato real del Excel de la coordinadora.
-- =====================================================================

-- (Opcional) Para BORRAR todos los datos de prueba y volver a empezar,
-- descomenta y ejecuta solo este bloque. No borra tipo_estudiante.
-- truncate certificado, nota, asistencia, sesion, pago, inscripcion,
--          oferta_curso, estudiante, docente, curso, idioma restart identity cascade;

-- ---------- Idiomas y cursos ----------
insert into idioma (nombre) values ('Inglés'), ('Francés');

insert into curso (idioma_id, nivel, nombre)
select id, 'A1', nombre || ' A1' from idioma;

insert into curso (idioma_id, nivel, nombre)
select id, 'A2', nombre || ' A2' from idioma where nombre = 'Inglés';

-- ---------- Docentes ----------
insert into docente (nombre, correo) values
  ('Docente Prueba Uno', 'docente1@example.com'),
  ('Docente Prueba Dos', 'docente2@example.com');

-- ---------- Ofertas (curso + período) ----------
-- Inglés A1: finalizado, alcanza el mínimo
insert into oferta_curso (curso_id, periodo, docente_id, cupo_minimo, cupo_maximo, fecha_inicio, fecha_termino, estado)
select c.id, '1-2026', d.id, 6, 20, date '2026-04-06', date '2026-07-27', 'finalizado'
from curso c
join docente d on d.correo = 'docente1@example.com'
where c.nombre = 'Inglés A1';

-- Francés A1: pocos inscritos, NO alcanza el mínimo
insert into oferta_curso (curso_id, periodo, docente_id, cupo_minimo, cupo_maximo, fecha_inicio, fecha_termino, estado)
select c.id, '1-2026', d.id, 6, 20, date '2026-04-06', date '2026-07-27', 'cerrado_sin_cupos'
from curso c
join docente d on d.correo = 'docente2@example.com'
where c.nombre = 'Francés A1';

-- ---------- Estudiantes (ficticios, 4 tipos) ----------
insert into estudiante
  (tipo_documento, documento, nombres, apellido_paterno, apellido_materno, nombre_social,
   correo, telefono, nacionalidad, unidad_ucn, campus, tipo_estudiante_id)
select v.tipo_documento, v.documento, v.nombres, v.apellido_paterno, v.apellido_materno, v.nombre_social,
       v.correo, v.telefono, v.nacionalidad, v.unidad_ucn, v.campus, t.id
from (values
  ('Otro',      'PRUEBA-001', 'Ana',     'Soto',     'Rojas',   null,    'est01@example.com', '+56 9 0000 0001', 'Chilena',    'Ingeniería Civil',  'Casa Central', 'Estudiante UCN pregrado'),
  ('Otro',      'PRUEBA-002', 'Bruno',   'Vega',     'Mora',    null,    'est02@example.com', '+56 9 0000 0002', 'Chilena',    'Enfermería',        'Casa Central', 'Estudiante UCN pregrado'),
  ('Otro',      'PRUEBA-003', 'Carla',   'Pinto',    'Díaz',    'Cami',  'est03@example.com', '+56 9 0000 0003', 'Chilena',    'Derecho',           'Casa Central', 'Estudiante UCN pregrado'),
  ('Otro',      'PRUEBA-004', 'Diego',   'Lara',     'Núñez',   null,    'est04@example.com', '+56 9 0000 0004', 'Chilena',    'Magíster en Datos', 'Casa Central', 'Estudiante UCN posgrado'),
  ('Otro',      'PRUEBA-005', 'Elena',   'Muñoz',    'Silva',   null,    'est05@example.com', '+56 9 0000 0005', 'Chilena',    null,                null,           'Egresado'),
  ('Otro',      'PRUEBA-006', 'Felipe',  'Araya',    'Cortés',  null,    'est06@example.com', '+56 9 0000 0006', 'Chilena',    null,                null,           'Egresado'),
  ('Otro',      'PRUEBA-007', 'Gabriela','Ríos',     'Tapia',   null,    'est07@example.com', '+56 9 0000 0007', 'Chilena',    null,                null,           'Externo'),
  ('Pasaporte', 'PA-TEST-008','Hugo',    'Ramírez',  'Castro',  null,    'est08@example.com', '+56 9 0000 0008', 'Colombiana', null,                null,           'Externo'),
  ('Otro',      'PRUEBA-009', 'Irene',   'Campos',   'Fuentes', null,    'est09@example.com', '+56 9 0000 0009', 'Chilena',    null,                null,           'Externo'),
  ('Otro',      'PRUEBA-010', 'Javier',  'Bravo',    'Olivares',null,    'est10@example.com', '+56 9 0000 0010', 'Chilena',    null,                null,           'Externo')
) as v(tipo_documento, documento, nombres, apellido_paterno, apellido_materno, nombre_social,
       correo, telefono, nacionalidad, unidad_ucn, campus, tipo)
join tipo_estudiante t on t.nombre = v.tipo;

-- ---------- Inscripciones ----------
-- Inglés A1 (est01..est08): 6 aprobados, 1 reprobado, 1 retirado
insert into inscripcion (estudiante_id, oferta_id, estado, fecha_inscripcion)
select e.id, o.id, v.estado, date '2026-03-20'
from (values
  ('est01@example.com', 'aprobado'),
  ('est02@example.com', 'aprobado'),
  ('est03@example.com', 'aprobado'),
  ('est04@example.com', 'aprobado'),
  ('est05@example.com', 'aprobado'),
  ('est06@example.com', 'aprobado'),
  ('est07@example.com', 'reprobado'),
  ('est08@example.com', 'retirado')
) as v(correo, estado)
join estudiante e on e.correo = v.correo
join oferta_curso o on o.curso_id = (select id from curso where nombre = 'Inglés A1') and o.periodo = '1-2026';

-- Francés A1 (est09, est10, est03): solo 2 inscritos confirmados, 1 pendiente de pago
insert into inscripcion (estudiante_id, oferta_id, estado, fecha_inscripcion)
select e.id, o.id, v.estado, date '2026-03-22'
from (values
  ('est09@example.com', 'inscrito'),
  ('est10@example.com', 'inscrito'),
  ('est03@example.com', 'pendiente_pago')
) as v(correo, estado)
join estudiante e on e.correo = v.correo
join oferta_curso o on o.curso_id = (select id from curso where nombre = 'Francés A1') and o.periodo = '1-2026';

-- ---------- Pagos ----------
insert into pago (inscripcion_id, monto, fecha_pago, estado, observacion)
select i.id,
       35000,
       case when i.estado = 'pendiente_pago' then null else date '2026-03-25' end,
       case when i.estado = 'pendiente_pago' then 'pendiente'
            when i.estado = 'retirado'       then 'devuelto'
            else 'pagado' end,
       'Dato de prueba'
from inscripcion i;

-- ---------- Sesiones y asistencia (Inglés A1, 6 clases) ----------
insert into sesion (oferta_id, numero, fecha)
select o.id, n, date '2026-04-06' + (n - 1) * 7
from oferta_curso o
join curso c on c.id = o.curso_id
cross join generate_series(1, 6) as n
where c.nombre = 'Inglés A1';

-- Mezcla determinista de P (presente), A (ausente) y J (justificado)
insert into asistencia (sesion_id, inscripcion_id, estado)
select s.id, i.id,
       case when (i.id + s.numero) % 7  = 0 then 'A'
            when (i.id + s.numero) % 11 = 0 then 'J'
            else 'P' end
from sesion s
join inscripcion i on i.oferta_id = s.oferta_id;

-- ---------- Notas (3 por estudiante que terminó el curso) ----------
insert into nota (inscripcion_id, numero, porcentaje, nota)
select i.id, n, round(g.nota * 100 / 7.0, 2), g.nota
from inscripcion i
cross join generate_series(1, 3) as n
cross join lateral (
  select round((4.0 + ((i.id * 3 + n) % 30) / 10.0)::numeric, 1) as nota
) g
where i.estado in ('aprobado', 'reprobado');

-- El reprobado tiene notas bajas
update nota
set nota = 3.2, porcentaje = round(3.2 * 100 / 7.0, 2)
where inscripcion_id in (select id from inscripcion where estado = 'reprobado');

-- Nota final = promedio de las 3 notas
update inscripcion i
set nota_final = x.prom
from (
  select inscripcion_id, round(avg(nota), 1) as prom
  from nota
  group by inscripcion_id
) x
where x.inscripcion_id = i.id;

-- ---------- Certificados (solo aprobados, en distintos estados) ----------
insert into certificado
  (inscripcion_id, cumple_requisitos, estado, fecha_solicitud, fecha_firma, fecha_entrega, observacion)
select id, true,
       case rn when 1 then 'entregado' when 2 then 'firmado' when 3 then 'solicitado' else 'pendiente' end,
       case when rn <= 3 then date '2026-08-03' end,
       case when rn <= 2 then date '2026-09-01' end,
       case when rn = 1  then date '2026-09-08' end,
       'Dato de prueba'
from (
  select id, row_number() over (order by id) as rn
  from inscripcion
  where estado = 'aprobado'
) t;

-- ---------- Verificación (ejecútalas por separado para revisar) ----------
-- select * from v_inscritos_vs_minimo;          -- Inglés A1: alcanza_minimo = true; Francés A1: false
-- select * from v_asistencia_inscripcion;       -- % de asistencia por inscripción
-- select e.nombres, t.nombre as tipo from estudiante e join tipo_estudiante t on t.id = e.tipo_estudiante_id;
