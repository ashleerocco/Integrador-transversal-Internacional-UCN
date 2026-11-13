-- =====================================================================
-- 0003 · Funciones, triggers y vistas (Grupo A). Idempotente.
-- Reglas de negocio que viven en la BD (no solo en pantalla):
--   · normalización del RUT/pasaporte y del correo
--   · anti-spam y anti-duplicados del formulario público
--   · aceptar solicitud = upsert estudiante por RUT + inscripción
--   · pago -> estudiante_pagado (trigger), recálculo al anular
--   · asistencia/notas/certificados solo para estudiantes pagados
--   · nota final = columna generada (0001); certificado: orden de estados y fechas
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Identidad del usuario conectado (base de las políticas RLS)
-- ---------------------------------------------------------------------
create or replace function idiomas.rol_actual() returns text
language sql stable security definer set search_path = '' as $$
  select rol from idiomas.perfil where id = auth.uid()
$$;

create or replace function idiomas.es_coordinacion() returns boolean
language sql stable security definer set search_path = '' as $$
  select coalesce((select rol = 'coordinacion' from idiomas.perfil where id = auth.uid()), false)
$$;

create or replace function idiomas.rut_docente_actual() returns text
language sql stable security definer set search_path = '' as $$
  select rut_docente from idiomas.perfil where id = auth.uid() and rol = 'docente'
$$;

create or replace function idiomas.rut_estudiante_actual() returns text
language sql stable security definer set search_path = '' as $$
  select rut_estudiante from idiomas.perfil where id = auth.uid() and rol = 'alumno'
$$;

create or replace function idiomas.ofertas_docente() returns setof bigint
language sql stable security definer set search_path = '' as $$
  select o.id from idiomas.oferta o
   where o.rut_docente is not null
     and o.rut_docente = (select p.rut_docente from idiomas.perfil p where p.id = auth.uid() and p.rol = 'docente')
$$;

create or replace function idiomas.config_valor(p_clave text) returns jsonb
language sql stable security definer set search_path = '' as $$
  select valor from idiomas.config where clave = p_clave
$$;

-- ---------------------------------------------------------------------
-- 2. Normalización y sellos de tiempo
-- ---------------------------------------------------------------------
create or replace function idiomas.trg_actualizado_en() returns trigger
language plpgsql set search_path = '' as $$
begin new.actualizado_en := now(); return new; end $$;

create or replace function idiomas.trg_normalizar_persona() returns trigger
language plpgsql set search_path = '' as $$
begin
  new.rut := idiomas.normalizar_documento(new.rut, new.tipo_documento);
  if new.correo is not null then new.correo := lower(trim(new.correo)); end if;
  if tg_table_name in ('estudiante', 'solicitud') then
    if new.fecha_nacimiento > current_date - interval '10 years' then
      raise exception 'FECHA_NACIMIENTO_INVALIDA' using errcode = '22023',
        hint = 'La fecha de nacimiento no es coherente (debe tener al menos 10 años).';
    end if;
    if new.vinculo <> 'otros' then new.vinculo_detalle := null; end if;
    if not new.salud_tiene_condicion then new.salud_requerimiento := null; end if;
  end if;
  return new;
end $$;

drop trigger if exists normalizar on idiomas.estudiante;
create trigger normalizar before insert or update on idiomas.estudiante
  for each row execute function idiomas.trg_normalizar_persona();
drop trigger if exists normalizar on idiomas.docente;
create trigger normalizar before insert or update on idiomas.docente
  for each row execute function idiomas.trg_normalizar_persona();
drop trigger if exists normalizar on idiomas.solicitud;
create trigger normalizar before insert or update on idiomas.solicitud
  for each row execute function idiomas.trg_normalizar_persona();

drop trigger if exists actualizado on idiomas.estudiante;
create trigger actualizado before update on idiomas.estudiante
  for each row execute function idiomas.trg_actualizado_en();
drop trigger if exists actualizado on idiomas.nota;
create trigger actualizado before update on idiomas.nota
  for each row execute function idiomas.trg_actualizado_en();
drop trigger if exists actualizado on idiomas.asistencia;
create trigger actualizado before update on idiomas.asistencia
  for each row execute function idiomas.trg_actualizado_en();

-- ---------------------------------------------------------------------
-- 3. Formulario público: anti-spam, anti-duplicado y coherencia de la oferta
--    (security definer: el rol anon no puede leer la tabla, pero el trigger sí)
-- ---------------------------------------------------------------------
create or replace function idiomas.trg_solicitud_validar() returns trigger
language plpgsql security definer set search_path = '' as $$
declare
  v_limite int := coalesce((idiomas.config_valor('limite_solicitudes_24h'))::text::int, 3);
  v_n int;
  v_ok boolean;
begin
  -- Quien entra por la API sin ser coordinación (anon o usuario común) solo puede crear
  -- solicitudes "limpias". El SQL Editor/seed (rol postgres) no pasa por aquí.
  if coalesce(current_setting('role', true), 'none') in ('anon', 'authenticated')
     and not idiomas.es_coordinacion() then
    new.estado := 'pendiente';
    new.motivo_rechazo := null; new.revisado_por := null; new.revisado_en := null;
    new.es_demo := false;
    new.fecha_consentimiento := now();
  end if;

  if new.codigo is null then
    new.codigo := 'SOL-' || upper(substr(md5(random()::text || clock_timestamp()::text), 1, 8));
  end if;

  -- Límite de envíos por correo o RUT
  select count(*) into v_n from idiomas.solicitud s
   where s.creado_en > now() - interval '24 hours'
     and (s.rut = new.rut or lower(s.correo) = lower(new.correo));
  if v_n >= v_limite then
    raise exception 'LIMITE_SOLICITUDES' using errcode = 'P0001',
      hint = 'Se alcanzó el máximo de envíos por día para este correo o documento.';
  end if;

  -- Duplicado: misma persona + misma oferta con solicitud vigente
  if new.oferta_id is not null and exists (
      select 1 from idiomas.solicitud s
       where s.rut = new.rut and s.oferta_id = new.oferta_id and s.estado in ('pendiente', 'aceptada')) then
    raise exception 'SOLICITUD_DUPLICADA' using errcode = 'P0001',
      hint = 'Ya existe una solicitud vigente para esta persona en este curso.';
  end if;

  -- La oferta debe pertenecer a una convocatoria abierta y coincidir con idioma y modalidad
  if new.oferta_id is not null then
    select (c.estado = 'abierta' and o.estado in ('abierta', 'confirmada')
            and o.idioma = new.idioma and o.modalidad = new.modalidad)
      into v_ok
      from idiomas.oferta o join idiomas.convocatoria c on c.id = o.convocatoria_id
     where o.id = new.oferta_id;
    if not coalesce(v_ok, false) and not idiomas.es_coordinacion() then
      raise exception 'OFERTA_NO_DISPONIBLE' using errcode = 'P0001',
        hint = 'El curso elegido ya no está disponible.';
    end if;
  end if;
  return new;
end $$;

drop trigger if exists validar on idiomas.solicitud;
create trigger validar before insert on idiomas.solicitud
  for each row execute function idiomas.trg_solicitud_validar();

-- ---------------------------------------------------------------------
-- 4. Precio, inscripción y aceptación de solicitudes
-- ---------------------------------------------------------------------
create or replace function idiomas.precio_oferta(p_oferta_id bigint, p_vinculo text, p_detalle text)
returns numeric language sql stable set search_path = '' as $$
  select coalesce(
    (select valor_universal from idiomas.oferta where id = p_oferta_id),
    (select ov.valor from idiomas.oferta_valor ov
      where ov.oferta_id = p_oferta_id
        and ov.categoria_precio = coalesce(
              (select categoria_precio from idiomas.vinculo_ucn where codigo = p_vinculo),
              (select categoria_precio from idiomas.vinculo_detalle where codigo = p_detalle),
              'externo')))
$$;

-- Crea o actualiza al estudiante por RUT y lo inscribe. Corre con los permisos
-- de quien llama (security invoker): solo coordinación pasa las políticas RLS.
create or replace function idiomas.inscribir_estudiante(
  p_datos jsonb, p_oferta_id bigint, p_forma_pago text, p_origen text, p_solicitud_id bigint default null)
returns text language plpgsql set search_path = '' as $$
declare
  v_tipo text := coalesce(p_datos->>'tipo_documento', 'RUT');
  v_rut text := idiomas.normalizar_documento(p_datos->>'rut', v_tipo);
begin
  if not idiomas.es_coordinacion() then
    raise exception 'SOLO_COORDINACION' using errcode = '42501';
  end if;

  insert into idiomas.estudiante as e (
    rut, tipo_documento, correo, nombres, apellido_paterno, apellido_materno, sexo, genero,
    nombre_social, pronombres, fecha_nacimiento, carrera, campus, campus_otro, nacionalidad,
    vinculo, vinculo_detalle, telefono, salud_tiene_condicion, salud_requerimiento,
    consentimiento_datos, fecha_consentimiento, origen, es_demo)
  values (
    v_rut, v_tipo, p_datos->>'correo', p_datos->>'nombres', p_datos->>'apellido_paterno',
    p_datos->>'apellido_materno', p_datos->>'sexo', p_datos->>'genero',
    nullif(p_datos->>'nombre_social', ''), p_datos->>'pronombres',
    (p_datos->>'fecha_nacimiento')::date, p_datos->>'carrera',
    nullif(p_datos->>'campus', ''), nullif(p_datos->>'campus_otro', ''),
    coalesce(nullif(p_datos->>'nacionalidad', ''), 'Chile'),
    p_datos->>'vinculo', nullif(p_datos->>'vinculo_detalle', ''), nullif(p_datos->>'telefono', ''),
    coalesce((p_datos->>'salud_tiene_condicion')::boolean, false),
    nullif(p_datos->>'salud_requerimiento', ''),
    coalesce((p_datos->>'consentimiento_datos')::boolean, false),
    coalesce((p_datos->>'fecha_consentimiento')::timestamptz, now()),
    p_origen, coalesce((p_datos->>'es_demo')::boolean, false))
  on conflict (rut) do update set
    correo = excluded.correo, nombres = excluded.nombres,
    apellido_paterno = excluded.apellido_paterno, apellido_materno = excluded.apellido_materno,
    sexo = excluded.sexo, genero = excluded.genero, nombre_social = excluded.nombre_social,
    pronombres = excluded.pronombres, fecha_nacimiento = excluded.fecha_nacimiento,
    carrera = excluded.carrera, campus = excluded.campus, campus_otro = excluded.campus_otro,
    nacionalidad = excluded.nacionalidad, vinculo = excluded.vinculo,
    vinculo_detalle = excluded.vinculo_detalle, telefono = coalesce(excluded.telefono, e.telefono),
    salud_tiene_condicion = excluded.salud_tiene_condicion,
    salud_requerimiento = excluded.salud_requerimiento,
    consentimiento_datos = excluded.consentimiento_datos or e.consentimiento_datos,
    fecha_consentimiento = coalesce(excluded.fecha_consentimiento, e.fecha_consentimiento);

  -- Documentos (solo id/enlace de Drive)
  if p_datos ? 'cedula_drive_file_id' or p_datos ? 'cedula_estado' then
    insert into idiomas.documento_estudiante (rut_estudiante, tipo, drive_file_id, drive_url, estado_archivo)
    values (v_rut, 'cedula', p_datos->>'cedula_drive_file_id', p_datos->>'cedula_drive_url',
            coalesce(p_datos->>'cedula_estado', 'subido'))
    on conflict (rut_estudiante, tipo) do update set drive_file_id = excluded.drive_file_id,
      drive_url = excluded.drive_url, estado_archivo = excluded.estado_archivo, actualizado_en = now();
  end if;
  if p_datos ? 'licencia_drive_file_id' or p_datos ? 'licencia_estado' then
    insert into idiomas.documento_estudiante (rut_estudiante, tipo, drive_file_id, drive_url, estado_archivo)
    values (v_rut, 'licencia', p_datos->>'licencia_drive_file_id', p_datos->>'licencia_drive_url',
            coalesce(p_datos->>'licencia_estado', 'subido'))
    on conflict (rut_estudiante, tipo) do update set drive_file_id = excluded.drive_file_id,
      drive_url = excluded.drive_url, estado_archivo = excluded.estado_archivo, actualizado_en = now();
  end if;

  if p_oferta_id is not null then
    insert into idiomas.inscripcion (rut_estudiante, oferta_id, origen, solicitud_id, forma_pago, monto_total, es_demo)
    values (v_rut, p_oferta_id, p_origen, p_solicitud_id, p_forma_pago,
            idiomas.precio_oferta(p_oferta_id, p_datos->>'vinculo', p_datos->>'vinculo_detalle'),
            coalesce((p_datos->>'es_demo')::boolean, false))
    on conflict (rut_estudiante, oferta_id) do update
      set estado = 'inscrito', forma_pago = coalesce(excluded.forma_pago, idiomas.inscripcion.forma_pago);
  end if;
  return v_rut;
end $$;

create or replace function idiomas.aceptar_solicitud(p_id bigint, p_oferta_id bigint default null)
returns text language plpgsql set search_path = '' as $$
declare s idiomas.solicitud; v_oferta bigint; v_rut text;
begin
  select * into s from idiomas.solicitud where id = p_id for update;
  if not found then raise exception 'SOLICITUD_NO_EXISTE'; end if;
  if s.estado <> 'pendiente' then raise exception 'SOLICITUD_YA_REVISADA'; end if;
  v_oferta := coalesce(p_oferta_id, s.oferta_id);
  if v_oferta is null then
    raise exception 'FALTA_OFERTA' using hint = 'La solicitud es "Otro (a convenir)": elige el curso al aceptar.';
  end if;
  v_rut := idiomas.inscribir_estudiante(to_jsonb(s), v_oferta, s.forma_pago, 'solicitud', s.id);
  update idiomas.solicitud
     set estado = 'aceptada', oferta_id = v_oferta, revisado_por = auth.uid(), revisado_en = now()
   where id = p_id;
  return v_rut;
end $$;

create or replace function idiomas.rechazar_solicitud(p_id bigint, p_motivo text)
returns void language plpgsql set search_path = '' as $$
begin
  if nullif(trim(p_motivo), '') is null then raise exception 'FALTA_MOTIVO'; end if;
  update idiomas.solicitud
     set estado = 'rechazada', motivo_rechazo = p_motivo, revisado_por = auth.uid(), revisado_en = now()
   where id = p_id and estado = 'pendiente';
  if not found then raise exception 'SOLICITUD_YA_REVISADA'; end if;
end $$;

-- ---------------------------------------------------------------------
-- 5. Pagos -> estudiante_pagado
-- ---------------------------------------------------------------------
create or replace function idiomas.recalcular_estudiante_pagado(p_rut text, p_oferta bigint)
returns void language plpgsql security definer set search_path = '' as $$
declare
  v_regla text := coalesce(idiomas.config_valor('regla_ingreso_pagado') #>> '{}', 'primer_pago');
  v_total numeric; v_pagado numeric; v_primero date;
begin
  select monto_total into v_total from idiomas.inscripcion
   where rut_estudiante = p_rut and oferta_id = p_oferta;
  select coalesce(sum(monto), 0), min(fecha) into v_pagado, v_primero
    from idiomas.pago where rut_estudiante = p_rut and oferta_id = p_oferta and estado = 'confirmado';

  if v_pagado > 0 and (v_regla <> 'pago_total' or v_pagado >= coalesce(v_total, 0)) then
    insert into idiomas.estudiante_pagado (rut, oferta_id, monto_total, monto_pagado, estado_pago, fecha_primer_pago)
    values (p_rut, p_oferta, v_total, v_pagado,
            case when v_total is not null and v_pagado >= v_total then 'total' else 'parcial' end, v_primero)
    on conflict (rut, oferta_id) do update set
      monto_total = excluded.monto_total, monto_pagado = excluded.monto_pagado,
      estado_pago = excluded.estado_pago, fecha_primer_pago = excluded.fecha_primer_pago,
      actualizado_en = now();
  else
    -- Sin pagos confirmados: sale de la base. Sus notas/asistencia NO se borran
    -- (quedan en sus tablas) pero deja de aparecer en Asistencia/Notas/Certificados.
    delete from idiomas.estudiante_pagado where rut = p_rut and oferta_id = p_oferta;
  end if;
end $$;

create or replace function idiomas.trg_pago_recalcular() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if tg_op in ('UPDATE', 'DELETE') then
    perform idiomas.recalcular_estudiante_pagado(old.rut_estudiante, old.oferta_id);
  end if;
  if tg_op in ('INSERT', 'UPDATE') then
    perform idiomas.recalcular_estudiante_pagado(new.rut_estudiante, new.oferta_id);
  end if;
  return null;
end $$;

drop trigger if exists recalcular_pagado on idiomas.pago;
create trigger recalcular_pagado after insert or update or delete on idiomas.pago
  for each row execute function idiomas.trg_pago_recalcular();

create or replace function idiomas.trg_inscripcion_monto() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  perform idiomas.recalcular_estudiante_pagado(new.rut_estudiante, new.oferta_id);
  return null;
end $$;

drop trigger if exists recalcular_pagado on idiomas.inscripcion;
create trigger recalcular_pagado after update of monto_total on idiomas.inscripcion
  for each row execute function idiomas.trg_inscripcion_monto();

create or replace function idiomas.anular_pago(p_id bigint, p_motivo text)
returns void language plpgsql set search_path = '' as $$
begin
  if nullif(trim(p_motivo), '') is null then raise exception 'FALTA_MOTIVO'; end if;
  update idiomas.pago set estado = 'anulado', motivo_anulacion = p_motivo
   where id = p_id and estado = 'confirmado';
  if not found then raise exception 'PAGO_NO_ANULABLE'; end if;
end $$;

-- ---------------------------------------------------------------------
-- 6. Asistencia y notas: solo alumnos en estudiante_pagado
-- ---------------------------------------------------------------------
create or replace function idiomas.trg_requiere_pagado() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if not exists (select 1 from idiomas.estudiante_pagado
                  where rut = new.rut_estudiante and oferta_id = new.oferta_id) then
    raise exception 'ALUMNO_NO_PAGADO' using errcode = 'P0001',
      hint = 'Solo se registran alumnos que aparecen en Estudiantes pagados.';
  end if;
  return new;
end $$;

drop trigger if exists requiere_pagado on idiomas.asistencia;
create trigger requiere_pagado before insert on idiomas.asistencia
  for each row execute function idiomas.trg_requiere_pagado();
drop trigger if exists requiere_pagado on idiomas.nota;
create trigger requiere_pagado before insert on idiomas.nota
  for each row execute function idiomas.trg_requiere_pagado();

-- Calendario de sesiones: días del horario entre inicio y fin de la convocatoria
create or replace function idiomas.generar_sesiones(p_oferta_id bigint)
returns int language plpgsql set search_path = '' as $$
declare v_n int;
begin
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

-- Marcar/desmarcar una sesión como suspendida (S para todo el curso)
create or replace function idiomas.suspender_sesion(p_oferta_id bigint, p_fecha date, p_suspendida boolean, p_motivo text default null)
returns void language plpgsql set search_path = '' as $$
begin
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

-- Alumnos de un curso para el docente: solo pagados y solo los datos necesarios
create or replace function idiomas.alumnos_de_oferta(p_oferta_id bigint)
returns table (rut text, nombre_completo text, nombre_social text, pronombres text, estado_pago text)
language sql stable security definer set search_path = '' as $$
  select e.rut,
         e.nombres || ' ' || e.apellido_paterno || ' ' || e.apellido_materno,
         e.nombre_social, e.pronombres, ep.estado_pago
    from idiomas.estudiante_pagado ep
    join idiomas.estudiante e on e.rut = ep.rut
   where ep.oferta_id = p_oferta_id
     and (idiomas.es_coordinacion() or p_oferta_id in (select idiomas.ofertas_docente()))
   order by e.apellido_paterno, e.apellido_materno, e.nombres
$$;

-- ---------------------------------------------------------------------
-- 7. Certificados: requisitos, orden de estados y fechas automáticas
-- ---------------------------------------------------------------------
create or replace function idiomas.orden_estado_certificado(p text) returns int
language sql immutable set search_path = '' as $$
  select case p when 'solicitado' then 1 when 'pendiente' then 2 when 'firmado' then 3 when 'entregado' then 4 end
$$;

create or replace function idiomas.trg_certificado() returns trigger
language plpgsql security definer set search_path = '' as $$
declare
  v_nota numeric; v_min_nota numeric; v_min_asis numeric; v_asis numeric;
  v_retro boolean := coalesce(current_setting('idiomas.permitir_retroceso', true), '') = 'on';
begin
  if tg_op = 'INSERT' then
    if not exists (select 1 from idiomas.estudiante_pagado
                    where rut = new.rut_estudiante and oferta_id = new.oferta_id) then
      raise exception 'ALUMNO_NO_PAGADO' using errcode = 'P0001';
    end if;
    select nota_final into v_nota from idiomas.nota
     where rut_estudiante = new.rut_estudiante and oferta_id = new.oferta_id;
    if v_nota is null then
      raise exception 'NOTAS_INCOMPLETAS' using errcode = 'P0001',
        hint = 'El certificado requiere las 3 notas y la nota final.';
    end if;
    -- Requisitos opcionales (desactivados por defecto: null)
    v_min_nota := nullif(idiomas.config_valor('certificado_nota_minima') #>> '{}', '')::numeric;
    v_min_asis := nullif(idiomas.config_valor('certificado_asistencia_minima') #>> '{}', '')::numeric;
    if v_min_nota is not null and v_nota < v_min_nota then
      raise exception 'NO_CUMPLE_NOTA_MINIMA' using errcode = 'P0001';
    end if;
    if v_min_asis is not null then
      select porcentaje into v_asis from idiomas.v_asistencia_resumen
       where rut_estudiante = new.rut_estudiante and oferta_id = new.oferta_id;
      if coalesce(v_asis, 0) < v_min_asis then
        raise exception 'NO_CUMPLE_ASISTENCIA_MINIMA' using errcode = 'P0001';
      end if;
    end if;
    select e.nombres || ' ' || e.apellido_paterno || ' ' || e.apellido_materno into new.nombre_completo
      from idiomas.estudiante e where e.rut = new.rut_estudiante;
    select i.nombre || ' ' || o.nivel || ' (' || c.periodo || ')' into new.curso
      from idiomas.oferta o join idiomas.idioma i on i.codigo = o.idioma
      join idiomas.convocatoria c on c.id = o.convocatoria_id where o.id = new.oferta_id;
  else
    if idiomas.orden_estado_certificado(new.estado) < idiomas.orden_estado_certificado(old.estado) then
      if not v_retro then
        raise exception 'RETROCESO_NO_CONFIRMADO' using errcode = 'P0001',
          hint = 'Para volver a un estado anterior hay que confirmarlo.';
      end if;
      -- al retroceder se limpian las fechas de los estados posteriores
      if idiomas.orden_estado_certificado(new.estado) < 4 then new.fecha_entrega := null; end if;
      if idiomas.orden_estado_certificado(new.estado) < 3 then new.fecha_firma := null; end if;
      if idiomas.orden_estado_certificado(new.estado) < 2 then new.fecha_pendiente := null; end if;
    end if;
  end if;

  -- Fechas automáticas según el estado (también si se salta un paso)
  if idiomas.orden_estado_certificado(new.estado) >= 1 then new.fecha_solicitada := coalesce(new.fecha_solicitada, current_date); end if;
  if idiomas.orden_estado_certificado(new.estado) >= 2 then new.fecha_pendiente := coalesce(new.fecha_pendiente, current_date); end if;
  if idiomas.orden_estado_certificado(new.estado) >= 3 then new.fecha_firma := coalesce(new.fecha_firma, current_date); end if;
  if idiomas.orden_estado_certificado(new.estado) >= 4 then new.fecha_entrega := coalesce(new.fecha_entrega, current_date); end if;
  new.actualizado_en := now();
  new.actualizado_por := coalesce(auth.uid(), new.actualizado_por);
  return new;
end $$;

drop trigger if exists reglas on idiomas.certificado;

create or replace function idiomas.cambiar_estado_certificado(
  p_rut text, p_oferta_id bigint, p_estado text,
  p_drive_file_id text default null, p_drive_url text default null, p_confirmar_retroceso boolean default false)
returns void language plpgsql set search_path = '' as $$
begin
  if p_confirmar_retroceso then perform set_config('idiomas.permitir_retroceso', 'on', true); end if;
  insert into idiomas.certificado (rut_estudiante, oferta_id, estado, drive_file_id, drive_url)
  values (p_rut, p_oferta_id, p_estado, p_drive_file_id, p_drive_url)
  on conflict (rut_estudiante, oferta_id) do update set
    estado = excluded.estado,
    drive_file_id = coalesce(excluded.drive_file_id, idiomas.certificado.drive_file_id),
    drive_url = coalesce(excluded.drive_url, idiomas.certificado.drive_url);
  perform set_config('idiomas.permitir_retroceso', '', true);
end $$;

-- ---------------------------------------------------------------------
-- 8. Vistas (security_invoker: respetan el RLS de quien consulta)
-- ---------------------------------------------------------------------
create or replace view idiomas.v_oferta with (security_invoker = true) as
select o.id as oferta_id, o.convocatoria_id, c.nombre as convocatoria, c.periodo, c.estado as estado_convocatoria,
       o.idioma, i.nombre as idioma_nombre, o.nivel, o.modalidad, o.sede, s.nombre as sede_nombre,
       o.dias, o.hora_inicio, o.hora_fin, o.horario_texto,
       o.rut_docente, d.nombres || ' ' || d.apellidos as docente,
       o.cupo_minimo, o.cupo_maximo, o.valor_universal, o.estado, o.es_demo,
       c.fecha_inicio_curso, c.fecha_fin_curso,
       i.nombre || ' ' || o.nivel || ' · ' || s.nombre || ' (' || c.periodo || ')' as etiqueta
  from idiomas.oferta o
  join idiomas.convocatoria c on c.id = o.convocatoria_id
  join idiomas.idioma i on i.codigo = o.idioma
  join idiomas.sede s on s.codigo = o.sede
  left join idiomas.docente d on d.rut = o.rut_docente;

-- Inscritos frente al mínimo: TODA oferta de una convocatoria abierta o cerrada aparece,
-- aunque tenga 0 inscritos (LEFT JOIN), sin copias manuales.
create or replace view idiomas.v_inscritos_vs_minimo with (security_invoker = true) as
select v.oferta_id, v.convocatoria, v.periodo, v.estado_convocatoria, v.etiqueta as curso,
       v.idioma_nombre as idioma, v.modalidad, v.sede_nombre as sede, v.estado as estado_oferta,
       v.cupo_minimo, v.cupo_maximo,
       coalesce(i.inscritos, 0) as inscritos,
       coalesce(sp.pendientes, 0) as solicitudes_pendientes,
       coalesce(p.pagados, 0) as pagados,
       greatest(v.cupo_minimo - coalesce(i.inscritos, 0), 0) as faltan,
       coalesce(i.inscritos, 0) >= v.cupo_minimo as alcanza_minimo,
       greatest(v.cupo_maximo - coalesce(i.inscritos, 0), 0) as cupos_disponibles
  from idiomas.v_oferta v
  left join (select oferta_id, count(*) inscritos from idiomas.inscripcion where estado = 'inscrito' group by oferta_id) i
         on i.oferta_id = v.oferta_id
  left join (select oferta_id, count(*) pendientes from idiomas.solicitud where estado = 'pendiente' group by oferta_id) sp
         on sp.oferta_id = v.oferta_id
  left join (select oferta_id, count(*) pagados from idiomas.estudiante_pagado group by oferta_id) p
         on p.oferta_id = v.oferta_id
 where v.estado_convocatoria in ('abierta', 'cerrada');

create or replace view idiomas.v_estudiante with (security_invoker = true) as
select e.rut, e.tipo_documento,
       e.nombres || ' ' || e.apellido_paterno || ' ' || e.apellido_materno as nombre_completo,
       e.nombres, e.apellido_paterno, e.apellido_materno, e.nombre_social, e.pronombres,
       e.correo, e.telefono, e.sexo, e.genero, e.fecha_nacimiento,
       date_part('year', age(e.fecha_nacimiento))::int as edad,
       e.nacionalidad, e.carrera, e.campus, coalesce(ca.nombre || coalesce(': ' || e.campus_otro, ''), '') as campus_nombre,
       e.vinculo, vu.nombre as vinculo_nombre, e.vinculo_detalle, vd.nombre as vinculo_detalle_nombre,
       e.salud_tiene_condicion, e.salud_requerimiento, e.consentimiento_datos, e.fecha_consentimiento,
       e.origen, e.es_demo, e.creado_en,
       (select string_agg(v.etiqueta, ' | ' order by v.oferta_id) from idiomas.inscripcion i
          join idiomas.v_oferta v on v.oferta_id = i.oferta_id
         where i.rut_estudiante = e.rut and i.estado = 'inscrito') as cursos,
       (select array_agg(i.oferta_id) from idiomas.inscripcion i
         where i.rut_estudiante = e.rut and i.estado = 'inscrito') as ofertas,
       (select drive_url from idiomas.documento_estudiante d where d.rut_estudiante = e.rut and d.tipo = 'cedula') as cedula_url,
       (select drive_url from idiomas.documento_estudiante d where d.rut_estudiante = e.rut and d.tipo = 'licencia') as licencia_url
  from idiomas.estudiante e
  join idiomas.vinculo_ucn vu on vu.codigo = e.vinculo
  left join idiomas.vinculo_detalle vd on vd.codigo = e.vinculo_detalle
  left join idiomas.campus ca on ca.codigo = e.campus;

create or replace view idiomas.v_estudiante_pagado with (security_invoker = true) as
select ep.rut, ep.oferta_id, v.etiqueta as curso, v.idioma_nombre as idioma,
       e.nombres || ' ' || e.apellido_paterno || ' ' || e.apellido_materno as nombre_completo,
       e.correo, e.genero, e.vinculo, vu.nombre as vinculo_nombre, e.campus, ca.nombre as campus_nombre,
       ep.monto_total, ep.monto_pagado, greatest(coalesce(ep.monto_total, 0) - ep.monto_pagado, 0) as saldo,
       ep.estado_pago, ep.fecha_primer_pago, ep.actualizado_en
  from idiomas.estudiante_pagado ep
  join idiomas.estudiante e on e.rut = ep.rut
  join idiomas.vinculo_ucn vu on vu.codigo = e.vinculo
  left join idiomas.campus ca on ca.codigo = e.campus
  join idiomas.v_oferta v on v.oferta_id = ep.oferta_id;

create or replace view idiomas.v_pago with (security_invoker = true) as
select p.id, row_number() over (partition by o.idioma, date_trunc('month', p.fecha) order by p.fecha, p.id) as n,
       e.nombres || ' ' || e.apellido_paterno || ' ' || e.apellido_materno as nombre,
       p.banco, p.rut_estudiante as rut, p.fecha, p.monto, p.n_transaccion, p.n_boleta,
       p.forma_pago, fp.nombre as forma_pago_nombre, p.n_cuota, p.oferta_id, v.etiqueta as curso,
       o.idioma, i.nombre as idioma_nombre, i.codigo_proyecto, i.codigo_proyecto_por_confirmar,
       to_char(p.fecha, 'YYYY-MM') as mes, p.estado, p.motivo_anulacion,
       p.comprobante_drive_url, p.comprobante_estado, p.observacion, p.es_demo, p.creado_en
  from idiomas.pago p
  join idiomas.estudiante e on e.rut = p.rut_estudiante
  join idiomas.oferta o on o.id = p.oferta_id
  join idiomas.idioma i on i.codigo = o.idioma
  join idiomas.v_oferta v on v.oferta_id = p.oferta_id
  left join idiomas.forma_pago fp on fp.codigo = p.forma_pago;

create or replace view idiomas.v_pagos_mes with (security_invoker = true) as
select idioma_nombre, codigo_proyecto, mes, count(*) as pagos, sum(monto) as total
  from idiomas.v_pago where estado = 'confirmado'
 group by idioma_nombre, codigo_proyecto, mes;

create or replace view idiomas.v_asistencia_resumen with (security_invoker = true) as
select ep.rut as rut_estudiante, ep.oferta_id,
       count(a.*) filter (where ea.cuenta_para_porcentaje) as sesiones_registradas,
       count(a.*) filter (where a.estado = 'P') as presentes,
       count(a.*) filter (where a.estado = 'A') as ausentes,
       count(a.*) filter (where a.estado = 'J') as justificadas,
       count(a.*) filter (where a.estado = 'S') as suspendidas,
       round(100.0 * count(a.*) filter (where ea.cuenta_como_presente)
             / nullif(count(a.*) filter (where ea.cuenta_para_porcentaje), 0), 1) as porcentaje
  from idiomas.estudiante_pagado ep
  left join idiomas.asistencia a on a.rut_estudiante = ep.rut and a.oferta_id = ep.oferta_id
  left join idiomas.estado_asistencia ea on ea.codigo = a.estado
 group by ep.rut, ep.oferta_id;

-- Alumnos que pueden aparecer en Certificados: pagados con las 3 notas
create or replace view idiomas.v_certificable with (security_invoker = true) as
select ep.rut, ep.oferta_id, ve.curso, ve.nombre_completo, n.nota1, n.nota2, n.nota3, n.nota_final,
       ar.porcentaje as asistencia,
       c.estado, c.fecha_solicitada, c.fecha_pendiente, c.fecha_firma, c.fecha_entrega,
       c.drive_file_id, c.drive_url, c.observacion
  from idiomas.estudiante_pagado ep
  join idiomas.v_estudiante_pagado ve on ve.rut = ep.rut and ve.oferta_id = ep.oferta_id
  join idiomas.nota n on n.rut_estudiante = ep.rut and n.oferta_id = ep.oferta_id and n.nota_final is not null
  left join idiomas.v_asistencia_resumen ar on ar.rut_estudiante = ep.rut and ar.oferta_id = ep.oferta_id
  left join idiomas.certificado c on c.rut_estudiante = ep.rut and c.oferta_id = ep.oferta_id;

create or replace view idiomas.v_solicitud with (security_invoker = true) as
select s.*, s.nombres || ' ' || s.apellido_paterno || ' ' || s.apellido_materno as nombre_completo,
       i.nombre as idioma_nombre, v.etiqueta as curso, vu.nombre as vinculo_nombre,
       fp.nombre as forma_pago_nombre, ca.nombre as campus_nombre
  from idiomas.solicitud s
  join idiomas.idioma i on i.codigo = s.idioma
  join idiomas.vinculo_ucn vu on vu.codigo = s.vinculo
  join idiomas.forma_pago fp on fp.codigo = s.forma_pago
  left join idiomas.v_oferta v on v.oferta_id = s.oferta_id
  left join idiomas.campus ca on ca.codigo = s.campus;

create or replace view idiomas.v_nota with (security_invoker = true) as
select n.*, v.etiqueta as curso, v.idioma_nombre as idioma
  from idiomas.nota n join idiomas.v_oferta v on v.oferta_id = n.oferta_id;

-- Ahora que existe v_asistencia_resumen, se crea el trigger de certificado
create trigger reglas before insert or update on idiomas.certificado
  for each row execute function idiomas.trg_certificado();

-- ---------------------------------------------------------------------
-- 9. Funciones públicas (sin login). NO son políticas: exponen solo lo
--    mínimo de las convocatorias/ofertas abiertas y los catálogos.
-- ---------------------------------------------------------------------
create or replace function idiomas.convocatorias_publicas()
returns table (id bigint, nombre text, periodo text, fecha_apertura date, fecha_cierre date,
               fecha_confirmacion date, fecha_inicio_curso date, fecha_fin_curso date, fechas_cuotas date[])
language sql stable security definer set search_path = '' as $$
  select id, nombre, periodo, fecha_apertura, fecha_cierre, fecha_confirmacion,
         fecha_inicio_curso, fecha_fin_curso, fechas_cuotas
    from idiomas.convocatoria where estado = 'abierta' order by fecha_apertura
$$;

create or replace function idiomas.proxima_convocatoria()
returns table (nombre text, periodo text, fecha_apertura date)
language sql stable security definer set search_path = '' as $$
  select nombre, periodo, fecha_apertura from idiomas.convocatoria
   where estado = 'borrador' and fecha_apertura >= current_date
   order by fecha_apertura limit 1
$$;

create or replace function idiomas.ofertas_publicas()
returns table (oferta_id bigint, convocatoria_id bigint, idioma text, idioma_nombre text, nivel text,
               modalidad text, sede text, sede_nombre text, dias smallint[], hora_inicio time, hora_fin time,
               horario_texto text, valor_universal numeric, valores jsonb, cupos_disponibles int)
language sql stable security definer set search_path = '' as $$
  select o.id, o.convocatoria_id, o.idioma, i.nombre, o.nivel, o.modalidad, o.sede, s.nombre,
         o.dias, o.hora_inicio, o.hora_fin, o.horario_texto, o.valor_universal,
         (select jsonb_object_agg(ov.categoria_precio, ov.valor) from idiomas.oferta_valor ov where ov.oferta_id = o.id),
         greatest(o.cupo_maximo - (select count(*) from idiomas.inscripcion x
                                    where x.oferta_id = o.id and x.estado = 'inscrito'), 0)::int
    from idiomas.oferta o
    join idiomas.convocatoria c on c.id = o.convocatoria_id
    join idiomas.idioma i on i.codigo = o.idioma
    join idiomas.sede s on s.codigo = o.sede
   where c.estado = 'abierta' and o.estado in ('abierta', 'confirmada')
   order by i.orden, o.modalidad, s.orden, o.nivel
$$;

create or replace function idiomas.catalogos_publicos() returns jsonb
language sql stable security definer set search_path = '' as $$
  select jsonb_build_object(
    'idioma', (select jsonb_agg(to_jsonb(x) order by x.orden) from (select codigo, nombre, orden from idiomas.idioma where activo) x),
    'vinculo_ucn', (select jsonb_agg(to_jsonb(x) order by x.orden) from idiomas.vinculo_ucn x),
    'vinculo_detalle', (select jsonb_agg(to_jsonb(x) order by x.orden) from idiomas.vinculo_detalle x),
    'campus', (select jsonb_agg(to_jsonb(x) order by x.orden) from idiomas.campus x),
    'sede', (select jsonb_agg(to_jsonb(x) order by x.orden) from idiomas.sede x),
    'forma_pago', (select jsonb_agg(to_jsonb(x) order by x.orden) from idiomas.forma_pago x),
    'categoria_precio', (select jsonb_agg(to_jsonb(x) order by x.orden) from idiomas.categoria_precio x),
    'config', (select jsonb_object_agg(clave, valor) from idiomas.config
                where clave in ('cabecera_formulario', 'cabecera_detalle', 'correo_contacto', 'web',
                                'calendly_url', 'mineduc_url')))
$$;
