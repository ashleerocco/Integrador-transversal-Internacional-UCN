-- =====================================================================
-- 0004 · Permisos y Row Level Security (Grupo A). Idempotente.
--   · RLS activo en TODAS las tablas del esquema idiomas.
--   · anon: SOLO el INSERT de la solicitud pública (+ EXECUTE de las funciones
--     públicas de lectura mínima). Ninguna otra política para anon.
--   · coordinacion: todo. docente: sus ofertas (por su RUT). alumno: lo suyo (por su RUT).
-- =====================================================================

grant usage on schema idiomas to anon, authenticated, service_role;

-- Privilegios de tabla (el RLS decide las filas)
revoke all on all tables in schema idiomas from anon;
grant select, insert, update, delete on all tables in schema idiomas to authenticated;
grant all on all tables in schema idiomas to service_role;
grant insert on idiomas.solicitud to anon;
grant usage, select on all sequences in schema idiomas to authenticated, service_role;

-- Funciones: por defecto nadie; luego se habilita lo necesario
revoke execute on all functions in schema idiomas from public, anon;
grant execute on all functions in schema idiomas to authenticated, service_role;
grant execute on function idiomas.convocatorias_publicas(), idiomas.ofertas_publicas(),
  idiomas.catalogos_publicos(), idiomas.proxima_convocatoria() to anon;
-- las usan los triggers/CHECK que corren durante el INSERT público
grant execute on function idiomas.normalizar_documento(text, text), idiomas.rut_valido(text),
  idiomas.documento_valido(text, text), idiomas.es_coordinacion(), idiomas.config_valor(text)
  to anon;

alter default privileges in schema idiomas revoke execute on functions from public;

-- ---------------------------------------------------------------------
-- Activar RLS en todas las tablas del esquema
-- ---------------------------------------------------------------------
do $$
declare t record;
begin
  for t in select tablename from pg_tables where schemaname = 'idiomas' loop
    execute format('alter table idiomas.%I enable row level security', t.tablename);
  end loop;
end $$;

-- Helper: (re)crear una política sin errores al ejecutar dos veces
create or replace function idiomas._politica(p_tabla text, p_nombre text, p_def text)
returns void language plpgsql set search_path = '' as $$
begin
  execute format('drop policy if exists %I on idiomas.%I', p_nombre, p_tabla);
  execute format('create policy %I on idiomas.%I %s', p_nombre, p_tabla, p_def);
end $$;
revoke execute on function idiomas._politica(text, text, text) from public, anon, authenticated;

-- ---------------------------------------------------------------------
-- Coordinación: acceso total a todo el esquema
-- ---------------------------------------------------------------------
do $$
declare t record;
begin
  for t in select tablename from pg_tables where schemaname = 'idiomas' loop
    perform idiomas._politica(t.tablename, 'coordinacion_total',
      'for all to authenticated using ((select idiomas.es_coordinacion())) with check ((select idiomas.es_coordinacion()))');
  end loop;
end $$;

-- ---------------------------------------------------------------------
-- Catálogos y config: lectura para cualquier usuario con sesión
-- ---------------------------------------------------------------------
select idiomas._politica(t, 'leer_catalogo', 'for select to authenticated using (true)')
  from unnest(array['idioma', 'categoria_precio', 'vinculo_ucn', 'vinculo_detalle', 'campus',
                    'sede', 'forma_pago', 'estado_asistencia', 'config']) t;

-- ---------------------------------------------------------------------
-- Público (anon): SOLO insertar una solicitud pendiente
-- ---------------------------------------------------------------------
select idiomas._politica('solicitud', 'publico_inserta_solicitud',
  $p$for insert to anon with check (
       estado = 'pendiente' and revisado_por is null and revisado_en is null
       and motivo_rechazo is null and not es_demo
       and acepta_terminos and consentimiento_datos)$p$);

-- ---------------------------------------------------------------------
-- Perfil: cada usuario ve el suyo
-- ---------------------------------------------------------------------
select idiomas._politica('perfil', 'ver_mi_perfil', 'for select to authenticated using (id = (select auth.uid()))');

-- ---------------------------------------------------------------------
-- Docente: sus ofertas y lo que cuelga de ellas
-- ---------------------------------------------------------------------
select idiomas._politica('docente', 'docente_se_ve',
  'for select to authenticated using (rut = (select idiomas.rut_docente_actual()))');
select idiomas._politica('oferta', 'docente_ve_sus_ofertas',
  'for select to authenticated using (id in (select idiomas.ofertas_docente()))');
select idiomas._politica('convocatoria', 'docente_ve_sus_convocatorias',
  'for select to authenticated using (id in (select o.convocatoria_id from idiomas.oferta o where o.id in (select idiomas.ofertas_docente())))');
select idiomas._politica('estudiante_pagado', 'docente_ve_pagados_de_sus_cursos',
  'for select to authenticated using (oferta_id in (select idiomas.ofertas_docente()))');
select idiomas._politica('sesion', 'docente_gestiona_sesiones',
  'for all to authenticated using (oferta_id in (select idiomas.ofertas_docente())) with check (oferta_id in (select idiomas.ofertas_docente()))');

-- asistencia / nota: solo sus cursos y solo alumnos en estudiante_pagado
select idiomas._politica(t, 'docente_gestiona', format(
  $p$for all to authenticated
     using (oferta_id in (select idiomas.ofertas_docente()))
     with check (oferta_id in (select idiomas.ofertas_docente())
                 and exists (select 1 from idiomas.estudiante_pagado ep
                              where ep.rut = %1$I.rut_estudiante and ep.oferta_id = %1$I.oferta_id))$p$, t))
  from unnest(array['asistencia', 'nota']) t;

-- ---------------------------------------------------------------------
-- Alumno: solo sus propios datos (por su RUT)
-- ---------------------------------------------------------------------
select idiomas._politica('estudiante', 'alumno_ve_sus_datos',
  'for select to authenticated using (rut = (select idiomas.rut_estudiante_actual()))');
select idiomas._politica('inscripcion', 'alumno_ve_sus_inscripciones',
  'for select to authenticated using (rut_estudiante = (select idiomas.rut_estudiante_actual()))');
select idiomas._politica('estudiante_pagado', 'alumno_ve_su_pago',
  'for select to authenticated using (rut = (select idiomas.rut_estudiante_actual()))');
select idiomas._politica('pago', 'alumno_ve_sus_pagos',
  'for select to authenticated using (rut_estudiante = (select idiomas.rut_estudiante_actual()))');
select idiomas._politica('nota', 'alumno_ve_sus_notas',
  'for select to authenticated using (rut_estudiante = (select idiomas.rut_estudiante_actual()))');
select idiomas._politica('asistencia', 'alumno_ve_su_asistencia',
  'for select to authenticated using (rut_estudiante = (select idiomas.rut_estudiante_actual()))');
select idiomas._politica('sesion', 'alumno_ve_sesiones_de_sus_cursos',
  'for select to authenticated using (oferta_id in (select i.oferta_id from idiomas.inscripcion i where i.rut_estudiante = (select idiomas.rut_estudiante_actual())))');
select idiomas._politica('certificado', 'alumno_ve_certificado_entregado',
  $p$for select to authenticated using (
       rut_estudiante = (select idiomas.rut_estudiante_actual()) and estado = 'entregado' and drive_file_id is not null)$p$);
select idiomas._politica('oferta', 'alumno_ve_sus_ofertas',
  'for select to authenticated using (id in (select i.oferta_id from idiomas.inscripcion i where i.rut_estudiante = (select idiomas.rut_estudiante_actual())))');
select idiomas._politica('convocatoria', 'alumno_ve_sus_convocatorias',
  'for select to authenticated using (id in (select o.convocatoria_id from idiomas.oferta o join idiomas.inscripcion i on i.oferta_id = o.id where i.rut_estudiante = (select idiomas.rut_estudiante_actual())))');
