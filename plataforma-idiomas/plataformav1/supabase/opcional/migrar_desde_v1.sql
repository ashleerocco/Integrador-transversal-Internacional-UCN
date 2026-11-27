-- =====================================================================
-- OPCIONAL · Copia los datos de la versión anterior (esquema `public`) al
-- esquema nuevo `idiomas`. NO borra ni modifica nada de `public`.
-- Idempotente: volver a ejecutarlo no duplica (ON CONFLICT / mapas).
-- Ejecutar DESPUÉS de 0001-0004, desde el SQL Editor (rol postgres).
--
-- Antes de ejecutar:
--   1. Los docentes antiguos no tienen RUT. Completa idiomas._mapa_docente
--      (docente_id antiguo -> RUT) o quedarán sin migrar (se informa).
--   2. Revisa el reporte al final: SELECT * FROM idiomas._migracion_reporte;
--
-- Observación de la revisión (nov-2026): los 10 estudiantes de producción
-- tienen documentos con formato de prueba (no son RUT válidos) y correos de
-- prueba. Este script los migra como "Pasaporte" (sin guiones); si son solo
-- datos de ensayo, conviene NO migrarlos.
-- =====================================================================

create table if not exists idiomas._mapa_docente (docente_id bigint primary key, rut text not null);
create table if not exists idiomas._mapa_oferta (oferta_curso_id bigint primary key, oferta_id bigint not null);
create table if not exists idiomas._migracion_reporte (
  id bigint generated always as identity primary key, entidad text, id_antiguo text, resultado text, detalle text,
  creado_en timestamptz default now());
alter table idiomas._mapa_docente enable row level security;
alter table idiomas._mapa_oferta enable row level security;
alter table idiomas._migracion_reporte enable row level security;
drop policy if exists coordinacion_total on idiomas._migracion_reporte;
create policy coordinacion_total on idiomas._migracion_reporte for all to authenticated
  using ((select idiomas.es_coordinacion())) with check ((select idiomas.es_coordinacion()));

truncate idiomas._migracion_reporte;  -- el reporte corresponde a la última ejecución

-- Documento antiguo -> clave nueva (RUT válido o pasaporte alfanumérico)
create or replace function idiomas._doc_v1(p_doc text, out tipo text, out rut text)
language plpgsql immutable set search_path = '' as $$
begin
  rut := idiomas.normalizar_documento(p_doc, 'RUT');
  if idiomas.rut_valido(rut) then tipo := 'RUT'; return; end if;
  rut := upper(regexp_replace(coalesce(p_doc, ''), '[^A-Za-z0-9]', '', 'g'));
  if rut ~ '^[A-Z0-9]{5,20}$' then tipo := 'Pasaporte'; else tipo := null; rut := null; end if;
end $$;

do $$
declare
  r record; v_doc record; v_conv bigint; v_oferta bigint; v_idioma text; v_rut_doc text; v_n int;
begin
  -- 1. Docentes con RUT mapeado
  for r in select d.*, m.rut from public.docente d left join idiomas._mapa_docente m on m.docente_id = d.id loop
    if r.rut is null then
      insert into idiomas._migracion_reporte (entidad, id_antiguo, resultado, detalle)
      values ('docente', r.id, 'omitido', 'Sin RUT en idiomas._mapa_docente');
      continue;
    end if;
    begin
      insert into idiomas.docente (rut, nombres, apellidos, correo)
      values (r.rut, split_part(r.nombre, ' ', 1), coalesce(nullif(substr(r.nombre, length(split_part(r.nombre, ' ', 1)) + 2), ''), '-'), r.correo)
      on conflict (rut) do nothing;
    exception when others then
      insert into idiomas._migracion_reporte (entidad, id_antiguo, resultado, detalle) values ('docente', r.id, 'error', sqlerrm);
    end;
  end loop;

  -- 2. Estudiantes
  for r in select e.*, t.nombre as tipo_nombre from public.estudiante e join public.tipo_estudiante t on t.id = e.tipo_estudiante_id loop
    select * into v_doc from idiomas._doc_v1(r.documento);
    if v_doc.rut is null then
      insert into idiomas._migracion_reporte (entidad, id_antiguo, resultado, detalle)
      values ('estudiante', r.id, 'omitido', 'Documento no convertible a RUT/pasaporte');
      continue;
    end if;
    begin
      insert into idiomas.estudiante (rut, tipo_documento, correo, nombres, apellido_paterno, apellido_materno,
        sexo, genero, nombre_social, pronombres, carrera, campus, campus_otro, nacionalidad, vinculo,
        telefono, salud_tiene_condicion, salud_requerimiento, origen, creado_en)
      values (v_doc.rut, v_doc.tipo, r.correo, r.nombres, r.apellido_paterno, r.apellido_materno,
        case when r.sexo is null then null when r.sexo in ('Mujer', 'Hombre') then r.sexo else 'Prefiero no decirlo' end,
        case when r.genero is null then null when r.genero in ('Femenino', 'Masculino') then r.genero else 'Otro' end,
        r.nombre_social, r.pronombres, coalesce(r.carrera, r.unidad_ucn),
        case when r.campus ilike '%antofagasta%' then 'antofagasta' when r.campus ilike '%coquimbo%' then 'coquimbo'
             when r.campus is not null then 'otro' end,
        case when r.campus is not null and r.campus not ilike '%antofagasta%' and r.campus not ilike '%coquimbo%' then r.campus end,
        coalesce(r.nacionalidad, 'Chile'),
        case r.tipo_nombre when 'Estudiante UCN pregrado' then 'pregrado' when 'Estudiante UCN posgrado' then 'posgrado'
             when 'Egresado' then 'egresado' else 'externo' end,
        r.telefono, r.condicion_salud is not null, r.condicion_salud, 'migracion', r.creado_en)
      on conflict (rut) do nothing;
      insert into idiomas._migracion_reporte (entidad, id_antiguo, resultado, detalle)
      values ('estudiante', r.id, 'ok', v_doc.tipo || case when r.cedula_path is not null or r.licencia_media_path is not null
                                   then '; tiene documentos en Storage: subirlos a Drive' else '' end);
    exception when others then
      insert into idiomas._migracion_reporte (entidad, id_antiguo, resultado, detalle) values ('estudiante', r.id, 'error', sqlerrm);
    end;
  end loop;

  -- 3. Convocatorias (una "migrada" por período) y ofertas
  for r in select o.*, c.nombre as curso_nombre, c.nivel as curso_nivel, i.nombre as idioma_nombre
             from public.oferta_curso o join public.curso c on c.id = o.curso_id left join public.idioma i on i.id = c.idioma_id loop
    if exists (select 1 from idiomas._mapa_oferta where oferta_curso_id = r.id) then continue; end if;
    select codigo into v_idioma from idiomas.idioma
     where lower(nombre) = lower(coalesce(r.idioma_nombre, split_part(r.curso_nombre, ' ', 1)));
    if v_idioma is null then
      insert into idiomas._migracion_reporte (entidad, id_antiguo, resultado, detalle) values ('oferta', r.id, 'omitido', 'Idioma no reconocido');
      continue;
    end if;
    select id into v_conv from idiomas.convocatoria where nombre = 'Migrada v1 ' || r.periodo;
    if v_conv is null then
      insert into idiomas.convocatoria (nombre, periodo, fecha_apertura, fecha_cierre, fecha_inicio_curso, fecha_fin_curso, estado)
      values ('Migrada v1 ' || r.periodo, r.periodo, coalesce(r.fecha_inicio, current_date), coalesce(r.fecha_inicio, current_date),
              r.fecha_inicio, r.fecha_termino, 'cerrada')
      returning id into v_conv;
    end if;
    select rut into v_rut_doc from idiomas._mapa_docente where docente_id = r.docente_id
       and exists (select 1 from idiomas.docente d where d.rut = idiomas._mapa_docente.rut);
    insert into idiomas.oferta (convocatoria_id, idioma, nivel, modalidad, sede, rut_docente, cupo_minimo, cupo_maximo,
                                valor_universal, num_sesiones_plan, estado)
    values (v_conv, v_idioma, coalesce(r.curso_nivel, r.curso_nombre),
            case when r.modalidad in ('Online', 'Virtual') then 'Virtual' else 'Presencial' end,
            case when r.modalidad in ('Online', 'Virtual') then 'virtual' else 'antofagasta' end,
            v_rut_doc, r.cupo_minimo, greatest(coalesce(r.cupo_maximo, 10), r.cupo_minimo), r.valor, r.num_sesiones,
            case r.estado when 'convocatoria' then 'abierta' when 'cerrado_sin_cupos' then 'no_se_dicta'
                          when 'finalizado' then 'finalizada' else 'confirmada' end)
    returning id into v_oferta;
    insert into idiomas._mapa_oferta values (r.id, v_oferta);
  end loop;

  -- docente asignado si el mapa se completó después de una ejecución anterior
  update idiomas.oferta o set rut_docente = m.rut
    from idiomas._mapa_oferta mo join public.oferta_curso oc on oc.id = mo.oferta_curso_id
    join idiomas._mapa_docente m on m.docente_id = oc.docente_id
   where o.id = mo.oferta_id and o.rut_docente is null and exists (select 1 from idiomas.docente d where d.rut = m.rut);

  -- 4. Inscripciones
  for r in select i.*, e.documento, mo.oferta_id as nueva_oferta, o.valor
             from public.inscripcion i join public.estudiante e on e.id = i.estudiante_id
             join idiomas._mapa_oferta mo on mo.oferta_curso_id = i.oferta_id
             join public.oferta_curso o on o.id = i.oferta_id loop
    select * into v_doc from idiomas._doc_v1(r.documento);
    if v_doc.rut is null then
      insert into idiomas._migracion_reporte (entidad, id_antiguo, resultado, detalle)
      values ('inscripcion', r.id, 'omitido', 'Estudiante no migrado');
      continue;
    end if;
    begin
      insert into idiomas.inscripcion (rut_estudiante, oferta_id, estado, origen, monto_total, fecha_inscripcion)
      values (v_doc.rut, r.nueva_oferta, case when r.estado = 'retirado' then 'retirado' else 'inscrito' end,
              'migracion', r.valor, r.fecha_inscripcion)
      on conflict do nothing;
    exception when others then
      insert into idiomas._migracion_reporte (entidad, id_antiguo, resultado, detalle) values ('inscripcion', r.id, 'error', sqlerrm);
    end;
  end loop;

  -- 5. Pagos: pagado -> confirmado, devuelto -> anulado, pendiente -> no es un pago (se informa)
  for r in select p.*, e.documento, mo.oferta_id as nueva_oferta, i.fecha_inscripcion
             from public.pago p join public.inscripcion i on i.id = p.inscripcion_id
             join public.estudiante e on e.id = i.estudiante_id
             join idiomas._mapa_oferta mo on mo.oferta_curso_id = i.oferta_id loop
    if r.estado = 'pendiente' or r.monto <= 0 then
      insert into idiomas._migracion_reporte (entidad, id_antiguo, resultado, detalle) values ('pago', r.id, 'omitido', 'Pago pendiente o monto 0');
      continue;
    end if;
    if exists (select 1 from idiomas.pago where observacion like '[v1 pago ' || r.id || ']%') then continue; end if;
    select * into v_doc from idiomas._doc_v1(r.documento);
    begin
      insert into idiomas.pago (rut_estudiante, oferta_id, fecha, monto, banco, estado, motivo_anulacion, observacion)
      values (v_doc.rut, r.nueva_oferta, coalesce(r.fecha_pago, r.fecha_inscripcion), r.monto, r.banco,
              case when r.estado = 'devuelto' then 'anulado' else 'confirmado' end,
              case when r.estado = 'devuelto' then 'Devuelto (v1)' end,
              '[v1 pago ' || r.id || '] ' || coalesce(r.observacion, '')
                || case when r.comprobante_path is not null then ' · comprobante en Storage: subir a Drive' else '' end);
    exception when others then
      insert into idiomas._migracion_reporte (entidad, id_antiguo, resultado, detalle) values ('pago', r.id, 'error', sqlerrm);
    end;
  end loop;

  -- 6. Sesiones y asistencia (solo sesiones con fecha; solo alumnos pagados)
  insert into idiomas.sesion (oferta_id, fecha, numero)
  select mo.oferta_id, s.fecha, s.numero from public.sesion s join idiomas._mapa_oferta mo on mo.oferta_curso_id = s.oferta_id
   where s.fecha is not null on conflict do nothing;
  get diagnostics v_n = row_count;
  insert into idiomas._migracion_reporte (entidad, resultado, detalle) values ('sesion', 'ok', v_n || ' sesiones');

  for r in select a.*, s.fecha, e.documento, mo.oferta_id as nueva_oferta
             from public.asistencia a join public.sesion s on s.id = a.sesion_id
             join public.inscripcion i on i.id = a.inscripcion_id join public.estudiante e on e.id = i.estudiante_id
             join idiomas._mapa_oferta mo on mo.oferta_curso_id = s.oferta_id where s.fecha is not null loop
    select * into v_doc from idiomas._doc_v1(r.documento);
    begin
      insert into idiomas.asistencia (rut_estudiante, oferta_id, fecha, estado)
      values (v_doc.rut, r.nueva_oferta, r.fecha, r.estado) on conflict do nothing;
    exception when others then
      insert into idiomas._migracion_reporte (entidad, id_antiguo, resultado, detalle) values ('asistencia', r.id, 'omitido', sqlerrm);
    end;
  end loop;

  -- 7. Notas: una fila por evaluación -> una fila por alumno (la nota final la calcula la BD)
  for r in select n.inscripcion_id, e.documento, mo.oferta_id as nueva_oferta,
                  max(n.nota) filter (where numero = 1) n1, max(n.nota) filter (where numero = 2) n2, max(n.nota) filter (where numero = 3) n3,
                  max(n.porcentaje) filter (where numero = 1) p1, max(n.porcentaje) filter (where numero = 2) p2, max(n.porcentaje) filter (where numero = 3) p3
             from public.nota n join public.inscripcion i on i.id = n.inscripcion_id
             join public.estudiante e on e.id = i.estudiante_id join idiomas._mapa_oferta mo on mo.oferta_curso_id = i.oferta_id
            group by n.inscripcion_id, e.documento, mo.oferta_id loop
    select * into v_doc from idiomas._doc_v1(r.documento);
    begin
      insert into idiomas.nota (rut_estudiante, oferta_id, nota1, nota2, nota3, porcentaje1, porcentaje2, porcentaje3)
      values (v_doc.rut, r.nueva_oferta, r.n1, r.n2, r.n3, r.p1, r.p2, r.p3) on conflict do nothing;
    exception when others then
      insert into idiomas._migracion_reporte (entidad, id_antiguo, resultado, detalle) values ('nota', r.inscripcion_id, 'omitido', sqlerrm);
    end;
  end loop;

  -- 8. Certificados (los PDF estaban en Storage: un "entregado" sin archivo en Drive queda "firmado")
  for r in select c.*, e.documento, mo.oferta_id as nueva_oferta
             from public.certificado c join public.inscripcion i on i.id = c.inscripcion_id
             join public.estudiante e on e.id = i.estudiante_id join idiomas._mapa_oferta mo on mo.oferta_curso_id = i.oferta_id loop
    if r.estado = 'pendiente' then
      insert into idiomas._migracion_reporte (entidad, id_antiguo, resultado, detalle) values ('certificado', r.id, 'omitido', 'Aún no solicitado en v1');
      continue;
    end if;
    select * into v_doc from idiomas._doc_v1(r.documento);
    begin
      insert into idiomas.certificado (rut_estudiante, oferta_id, estado, fecha_solicitada, fecha_firma, fecha_entrega, observacion)
      values (v_doc.rut, r.nueva_oferta, case when r.estado = 'entregado' then 'firmado' else r.estado end,
              r.fecha_solicitud, r.fecha_firma, null,
              concat_ws(' · ', r.observacion, case when r.estado = 'entregado'
                then 'Entregado en v1 el ' || r.fecha_entrega || '; subir el PDF a Drive para marcarlo entregado' end))
      on conflict do nothing;
    exception when others then
      insert into idiomas._migracion_reporte (entidad, id_antiguo, resultado, detalle) values ('certificado', r.id, 'omitido', sqlerrm);
    end;
  end loop;

  -- 9. Perfiles (usuarios de Auth existentes)
  insert into idiomas.perfil (id, nombre, rol, rut_docente, rut_estudiante)
  select * from (
    select p.id, p.nombre,
           case p.rol when 'coordinadora' then 'coordinacion' when 'docente' then 'docente' else 'alumno' end as rol,
           (select m.rut from idiomas._mapa_docente m join idiomas.docente d on d.rut = m.rut
             where m.docente_id = p.docente_id) as rut_docente,
           (select x.rut from public.estudiante e cross join lateral idiomas._doc_v1(e.documento) x
             where e.id = p.estudiante_id and exists (select 1 from idiomas.estudiante ne where ne.rut = x.rut)) as rut_estudiante
      from public.perfil p) q
   where q.rol = 'coordinacion' or (q.rol = 'docente' and q.rut_docente is not null)
      or (q.rol = 'alumno' and q.rut_estudiante is not null)
  on conflict (id) do nothing;
end $$;

select entidad, resultado, count(*) from idiomas._migracion_reporte group by 1, 2 order by 1, 2;
