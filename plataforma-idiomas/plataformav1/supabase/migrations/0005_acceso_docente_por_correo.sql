-- =====================================================================
-- 0005 · Acceso de docentes por correo (sin rol en idiomas.perfil)
--
-- Un usuario es docente si su correo de Supabase Auth (confirmado) coincide,
-- sin distinguir mayúsculas, con un registro de idiomas.docente con activo = true.
-- Desmarcar "Activo" en la pestaña Docentes le quita el acceso de inmediato.
--
-- El docente usa LAS MISMAS tablas que la coordinación (asistencia, nota, sesion):
--   · ve solo sus cursos (oferta.rut_docente) y los alumnos pagados de ellos;
--   · registra y edita asistencia y notas de sus cursos, pero no las borra;
--   · no puede cambiar a qué alumno, curso o fecha pertenece un registro;
--   · no ve convocatorias, pagos, otros cursos ni otros docentes.
-- La coordinación sigue identificándose con idiomas.perfil (sin cambios).
--
-- Se puede ejecutar más de una vez. Requiere 0001–0004.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Identificar al docente
-- ---------------------------------------------------------------------
-- Correo único sin distinguir mayúsculas (y búsqueda rápida por correo)
create unique index if not exists docente_correo_lower_uk on idiomas.docente (lower(correo)) where correo is not null;

-- RUT del docente activo cuyo correo coincide con el del usuario conectado, o null.
-- Se exige además que el correo esté confirmado en Auth: así nadie obtiene acceso
-- registrándose con el correo de un docente sin poder leer ese buzón.
create or replace function idiomas.mi_docente_id()
returns text language sql stable security definer set search_path = '' as $$
  select d.rut
    from idiomas.docente d
    join auth.users u on u.id = auth.uid()
   where d.activo
     and u.email_confirmed_at is not null
     and lower(d.correo) = lower(auth.jwt() ->> 'email')
     and lower(u.email) = lower(d.correo)
   limit 1
$$;

-- Las funciones existentes ahora se apoyan en el correo (antes: perfil.rol = 'docente').
-- Todas las políticas que ya las usan quedan actualizadas sin duplicarlas.
create or replace function idiomas.rut_docente_actual()
returns text language sql stable security definer set search_path = '' as $$
  select idiomas.mi_docente_id()
$$;

create or replace function idiomas.ofertas_docente()
returns setof bigint language sql stable security definer set search_path = '' as $$
  select o.id from idiomas.oferta o
   where o.rut_docente is not null and o.rut_docente = idiomas.mi_docente_id()
$$;

-- Cursos del docente con su nombre y fechas, SIN darle acceso a la tabla convocatoria.
create or replace function idiomas.mis_cursos_docente()
returns table (oferta_id bigint, etiqueta text, estado text, horario_texto text, modalidad text,
               fecha_inicio_curso date, fecha_fin_curso date, alumnos_pagados bigint)
language sql stable security definer set search_path = '' as $$
  select o.id,
         i.nombre || ' ' || o.nivel || ' · ' || s.nombre || ' (' || c.periodo || ')',
         o.estado, o.horario_texto, o.modalidad, c.fecha_inicio_curso, c.fecha_fin_curso,
         (select count(*) from idiomas.estudiante_pagado ep where ep.oferta_id = o.id)
    from idiomas.oferta o
    join idiomas.convocatoria c on c.id = o.convocatoria_id
    join idiomas.idioma i on i.codigo = o.idioma
    join idiomas.sede s on s.codigo = o.sede
   where o.id in (select idiomas.ofertas_docente())
   order by o.id desc
$$;

-- ---------------------------------------------------------------------
-- 2. Políticas RLS del docente
-- ---------------------------------------------------------------------
-- Sin acceso a convocatorias (el nombre y las fechas de sus cursos llegan por mis_cursos_docente)
drop policy if exists docente_ve_sus_convocatorias on idiomas.convocatoria;

-- Asistencia y notas: SELECT / INSERT / UPDATE en sus cursos; sin DELETE.
drop policy if exists docente_gestiona on idiomas.asistencia;
drop policy if exists docente_gestiona on idiomas.nota;
select idiomas._politica(t, 'docente_ve',
  'for select to authenticated using (oferta_id in (select idiomas.ofertas_docente()))')
  from unnest(array['asistencia', 'nota']) t;
select idiomas._politica(t, 'docente_registra', format(
  $p$for insert to authenticated
     with check (oferta_id in (select idiomas.ofertas_docente())
                 and exists (select 1 from idiomas.estudiante_pagado ep
                              where ep.rut = %1$I.rut_estudiante and ep.oferta_id = %1$I.oferta_id))$p$, t))
  from unnest(array['asistencia', 'nota']) t;
select idiomas._politica(t, 'docente_edita', format(
  $p$for update to authenticated
     using (oferta_id in (select idiomas.ofertas_docente()))
     with check (oferta_id in (select idiomas.ofertas_docente())
                 and exists (select 1 from idiomas.estudiante_pagado ep
                              where ep.rut = %1$I.rut_estudiante and ep.oferta_id = %1$I.oferta_id))$p$, t))
  from unnest(array['asistencia', 'nota']) t;

-- El docente no puede mover un registro a otro alumno, curso o fecha (aunque sean suyos).
-- Solo la coordinación (o el backend, sin usuario) puede cambiar esas columnas,
-- p. ej. al corregir un RUT con ON UPDATE CASCADE.
create or replace function idiomas.trg_claves_fijas()
returns trigger language plpgsql set search_path = '' as $$
begin
  if auth.uid() is null or idiomas.es_coordinacion() then
    return new;
  end if;
  if new.rut_estudiante is distinct from old.rut_estudiante or new.oferta_id is distinct from old.oferta_id
     or (tg_table_name = 'asistencia' and (to_jsonb(new) ->> 'fecha') is distinct from (to_jsonb(old) ->> 'fecha')) then
    raise exception 'NO_PUEDE_CAMBIAR_ALUMNO_CURSO_O_FECHA'
      using hint = 'Solo la coordinación puede cambiar a qué alumno, curso o fecha pertenece un registro.';
  end if;
  return new;
end $$;

drop trigger if exists claves_fijas on idiomas.asistencia;
create trigger claves_fijas before update on idiomas.asistencia
  for each row execute function idiomas.trg_claves_fijas();
drop trigger if exists claves_fijas on idiomas.nota;
create trigger claves_fijas before update on idiomas.nota
  for each row execute function idiomas.trg_claves_fijas();

-- Índice de unión que faltaba (asistencia y estudiante_pagado ya lo tienen)
create index if not exists nota_oferta_idx on idiomas.nota (oferta_id);

-- ---------------------------------------------------------------------
-- 3. Funciones que el docente usa en Asistencia
-- ---------------------------------------------------------------------
-- Antes corrían con los permisos del usuario: generar_sesiones necesitaba leer la
-- convocatoria y suspender_sesion borrar marcas "S". Ahora corren con permisos
-- elevados y validan explícitamente que el curso sea del docente (o coordinación).
create or replace function idiomas.generar_sesiones(p_oferta_id bigint)
returns int language plpgsql security definer set search_path = '' as $$
declare v_n int;
begin
  if not (idiomas.es_coordinacion() or p_oferta_id in (select idiomas.ofertas_docente())) then
    raise exception 'SIN_PERMISO_CURSO';
  end if;
  insert into idiomas.sesion (oferta_id, fecha)
  select o.id, d::date
    from idiomas.oferta o
    join idiomas.convocatoria c on c.id = o.convocatoria_id
    cross join lateral generate_series(c.fecha_inicio_curso, c.fecha_fin_curso, interval '1 day') d
   where o.id = p_oferta_id
     and c.fecha_inicio_curso is not null and c.fecha_fin_curso is not null
     and extract(isodow from d)::smallint = any (o.dias)
  on conflict (oferta_id, fecha) do nothing;
  get diagnostics v_n = row_count;
  -- renumerar en orden cronológico
  update idiomas.sesion s set numero = x.n
    from (select fecha, row_number() over (order by fecha) n from idiomas.sesion where oferta_id = p_oferta_id) x
   where s.oferta_id = p_oferta_id and s.fecha = x.fecha and s.numero is distinct from x.n;
  return v_n;
end $$;

create or replace function idiomas.suspender_sesion(p_oferta_id bigint, p_fecha date, p_suspendida boolean, p_motivo text default null)
returns void language plpgsql security definer set search_path = '' as $$
begin
  if not (idiomas.es_coordinacion() or p_oferta_id in (select idiomas.ofertas_docente())) then
    raise exception 'SIN_PERMISO_CURSO';
  end if;
  update idiomas.sesion set suspendida = p_suspendida, motivo = p_motivo
   where oferta_id = p_oferta_id and fecha = p_fecha;
  if not found then raise exception 'SESION_NO_EXISTE'; end if;
  if p_suspendida then
    insert into idiomas.asistencia (rut_estudiante, oferta_id, fecha, estado)
    select ep.rut, ep.oferta_id, p_fecha, 'S' from idiomas.estudiante_pagado ep where ep.oferta_id = p_oferta_id
    on conflict (rut_estudiante, oferta_id, fecha) do update set estado = 'S';
  else
    delete from idiomas.asistencia where oferta_id = p_oferta_id and fecha = p_fecha and estado = 'S';
  end if;
end $$;

-- ---------------------------------------------------------------------
-- 4. Quién registró cada cambio
-- ---------------------------------------------------------------------
alter table idiomas.asistencia add column if not exists actualizado_por text;
alter table idiomas.nota add column if not exists actualizado_por text;
alter table idiomas.asistencia add column if not exists actualizado_en timestamptz default now();
alter table idiomas.nota add column if not exists actualizado_en timestamptz default now();

create or replace function idiomas.trg_actualizado_por()
returns trigger language plpgsql set search_path = '' as $$
begin
  new.actualizado_por := coalesce(auth.jwt() ->> 'email', 'sistema');
  new.actualizado_en := now();
  return new;
end $$;

drop trigger if exists actualizado_por on idiomas.asistencia;
create trigger actualizado_por before insert or update on idiomas.asistencia
  for each row execute function idiomas.trg_actualizado_por();
drop trigger if exists actualizado_por on idiomas.nota;
create trigger actualizado_por before insert or update on idiomas.nota
  for each row execute function idiomas.trg_actualizado_por();

-- ---------------------------------------------------------------------
-- 5. Permisos de ejecución
-- ---------------------------------------------------------------------
revoke execute on function idiomas.mi_docente_id(), idiomas.mis_cursos_docente(),
  idiomas.trg_claves_fijas(), idiomas.trg_actualizado_por() from public, anon;
grant execute on function idiomas.mi_docente_id(), idiomas.mis_cursos_docente() to authenticated, service_role;
grant execute on function idiomas.generar_sesiones(bigint),
  idiomas.suspender_sesion(bigint, date, boolean, text) to authenticated, service_role;
