-- =====================================================================
-- VERIFICACIÓN (solo desarrollo, con seed_demo cargado).
-- Todo corre dentro de una transacción que se REVIERTE al final: no deja cambios.
-- Resultado: una tabla con cada prueba y OK / FALLA.
-- =====================================================================
begin;

create temp table _r (n serial, prueba text, ok boolean, detalle text) on commit drop;
grant all on _r to anon, authenticated;
grant usage on sequence _r_n_seq to anon, authenticated;

create or replace function pg_temp.como(p_email text) returns void language plpgsql as $$
begin
  perform set_config('request.jwt.claim.sub',
    coalesce((select id::text from auth.users where email = p_email), ''), true);
end $$;

-- ---------------------------------------------------------------- Estructura
insert into _r (prueba, ok, detalle)
select 'RLS activo en todas las tablas de idiomas', bool_and(c.relrowsecurity),
       string_agg(c.relname, ', ') filter (where not c.relrowsecurity)
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'idiomas' and c.relkind = 'r';

insert into _r (prueba, ok, detalle)
select 'anon: única política = INSERT en solicitud', count(*) = 1 and bool_and(tablename = 'solicitud' and cmd = 'INSERT'),
       string_agg(tablename || ':' || cmd, ', ')
  from pg_policies where schemaname = 'idiomas' and 'anon' = any (roles);

insert into _r (prueba, ok, detalle)
select 'RUT es PK de estudiante y docente', count(*) = 2, null
  from information_schema.key_column_usage k join information_schema.table_constraints t using (constraint_name, table_schema, table_name)
 where t.table_schema = 'idiomas' and t.constraint_type = 'PRIMARY KEY' and k.column_name = 'rut'
   and t.table_name in ('estudiante', 'docente');

insert into _r (prueba, ok, detalle)
select 'FK por RUT con ON UPDATE CASCADE', bool_and(rc.update_rule = 'CASCADE'), count(*)::text || ' FKs revisadas'
  from information_schema.referential_constraints rc
  join information_schema.key_column_usage k on k.constraint_name = rc.constraint_name and k.constraint_schema = rc.constraint_schema
 where rc.constraint_schema = 'idiomas' and k.column_name in ('rut_estudiante', 'rut_docente', 'rut') and k.table_name <> 'perfil';

insert into _r (prueba, ok, detalle)
select 'Los 6 idiomas están en el catálogo', count(*) = 6, string_agg(nombre, ', ') from idiomas.idioma;

-- ---------------------------------------------------------------- Convocatoria abierta -> inicio y Resumen
insert into _r (prueba, ok, detalle)
select 'Resumen muestra ofertas con 0 inscritos', exists (select 1 from idiomas.v_inscritos_vs_minimo where inscritos = 0), null;
insert into _r (prueba, ok, detalle)
select 'Resumen: una oferta bajo y otra sobre el mínimo',
       exists (select 1 from idiomas.v_inscritos_vs_minimo where alcanza_minimo)
       and exists (select 1 from idiomas.v_inscritos_vs_minimo where not alcanza_minimo), null;

do $$
declare n_antes int; n_despues int; v_id bigint;
begin
  select id into v_id from idiomas.convocatoria where es_demo and estado = 'abierta' limit 1;
  set local role anon;
  select count(*) into n_antes from idiomas.ofertas_publicas();
  reset role;
  update idiomas.convocatoria set estado = 'cerrada' where id = v_id;
  set local role anon;
  select count(*) into n_despues from idiomas.ofertas_publicas();
  reset role;
  update idiomas.convocatoria set estado = 'abierta' where id = v_id;
  insert into _r (prueba, ok, detalle) values ('Cerrar convocatoria la saca del inicio público',
    n_antes > 0 and n_despues = 0, n_antes || ' -> ' || n_despues);
end $$;

-- ---------------------------------------------------------------- Formulario público (anon)
do $$
declare v_of bigint; v_err text; v_lee int;
begin
  select id into v_of from idiomas.oferta where es_demo and idioma = 'portugues';
  set local role anon;
  insert into idiomas.solicitud (codigo, correo, idioma, modalidad, oferta_id, nombres, apellido_paterno, apellido_materno,
    sexo, genero, pronombres, tipo_documento, rut, fecha_nacimiento, carrera, nacionalidad, vinculo,
    salud_tiene_condicion, forma_pago, acepta_terminos, consentimiento_datos)
  values ('TEST-0001', 'Prueba@Demo.UCN.test', 'portugues', 'Virtual', v_of, 'Prueba', 'Uno', 'Dos', 'Mujer', 'Femenino',
          'ella', 'RUT', '41.024.543-4', '2000-01-01', 'Prueba', 'Chile', 'externo', false, 'contado', true, true);
  insert into _r (prueba, ok) values ('anon puede enviar una solicitud (RUT se normaliza)', true);
  begin
    insert into idiomas.solicitud (codigo, correo, idioma, modalidad, oferta_id, nombres, apellido_paterno, apellido_materno,
      sexo, genero, pronombres, tipo_documento, rut, fecha_nacimiento, carrera, nacionalidad, vinculo,
      salud_tiene_condicion, forma_pago, acepta_terminos, consentimiento_datos)
    values ('TEST-0002', 'otra@demo.ucn.test', 'portugues', 'Virtual', v_of, 'Prueba', 'Uno', 'Dos', 'Mujer', 'Femenino',
            'ella', 'RUT', '41024543-4', '2000-01-01', 'Prueba', 'Chile', 'externo', false, 'contado', true, true);
    v_err := 'se aceptó el duplicado';
  exception when others then v_err := sqlerrm;
  end;
  insert into _r (prueba, ok, detalle) values ('Duplicado misma persona + oferta rechazado', v_err = 'SOLICITUD_DUPLICADA', v_err);
  begin
    select count(*) into v_lee from idiomas.solicitud;
    v_err := v_lee || ' filas visibles';
  exception when insufficient_privilege then v_err := 'sin permiso';
  end;
  insert into _r (prueba, ok, detalle) values ('anon no puede leer solicitudes', v_err = 'sin permiso', v_err);
  begin
    perform 1 from idiomas.estudiante limit 1;
    v_err := 'pudo leer';
  exception when insufficient_privilege then v_err := 'sin permiso';
  end;
  insert into _r (prueba, ok, detalle) values ('anon no puede leer estudiantes', v_err = 'sin permiso', v_err);
  reset role;
  insert into _r (prueba, ok, detalle)
  select 'RUT normalizado en la solicitud', rut = '41024543-4', null from idiomas.solicitud where codigo = 'TEST-0001';
end $$;

-- ---------------------------------------------------------------- Coordinación: aceptar sin duplicar
do $$
declare v_id bigint; n_est_antes int; n_est_despues int; n_ins int;
begin
  perform pg_temp.como('coordinacion@demo.ucn.test');
  set local role authenticated;
  select count(*) into n_est_antes from idiomas.estudiante;
  select id into v_id from idiomas.solicitud where codigo = 'DEMO-0005';  -- Ana, ya es estudiante, pide Francés
  perform idiomas.aceptar_solicitud(v_id);
  select count(*) into n_est_despues from idiomas.estudiante;
  select count(*) into n_ins from idiomas.inscripcion i join idiomas.oferta o on o.id = i.oferta_id
   where i.rut_estudiante = '41003434-4' and o.idioma = 'frances';
  insert into _r (prueba, ok, detalle) values ('Aceptar a estudiante existente no lo duplica y lo inscribe',
    n_est_antes = n_est_despues and n_ins = 1, n_est_antes || '/' || n_est_despues);
  -- solicitud nueva (persona nueva) -> aparece en Estudiantes
  select id into v_id from idiomas.solicitud where codigo = 'TEST-0001';
  perform idiomas.aceptar_solicitud(v_id);
  insert into _r (prueba, ok) select 'Aceptar persona nueva la crea en Estudiantes',
    exists (select 1 from idiomas.estudiante where rut = '41024543-4');
  reset role;
end $$;

-- ---------------------------------------------------------------- Pagos -> estudiantes pagados
do $$
declare v_of bigint; v_pid bigint; v_antes boolean; v_despues boolean; v_anulado boolean;
begin
  perform pg_temp.como('coordinacion@demo.ucn.test');
  set local role authenticated;
  select id into v_of from idiomas.oferta where es_demo and idioma = 'portugues';
  v_antes := exists (select 1 from idiomas.estudiante_pagado where rut = '41024543-4');
  insert into idiomas.pago (rut_estudiante, oferta_id, fecha, monto, forma_pago, n_cuota)
  values ('41024543-4', v_of, current_date, 60000, 'tres_cuotas', 1) returning id into v_pid;
  v_despues := exists (select 1 from idiomas.estudiante_pagado where rut = '41024543-4' and oferta_id = v_of and estado_pago = 'parcial');
  perform idiomas.anular_pago(v_pid, 'prueba');
  v_anulado := not exists (select 1 from idiomas.estudiante_pagado where rut = '41024543-4');
  insert into _r (prueba, ok, detalle) values ('Pago agrega a Estudiantes pagados; anular lo recalcula',
    not v_antes and v_despues and v_anulado, format('%s/%s/%s', v_antes, v_despues, v_anulado));
  reset role;
end $$;

-- ---------------------------------------------------------------- Notas
insert into _r (prueba, ok, detalle)
select 'Nota final = promedio de 3 notas (1 decimal) y nula si falta una',
       bool_and(case when nota1 is not null and nota2 is not null and nota3 is not null
                     then nota_final = round((nota1 + nota2 + nota3) / 3.0, 1) else nota_final is null end), null
  from idiomas.nota;

do $$
declare v_err text;
begin
  begin
    insert into idiomas.nota (rut_estudiante, oferta_id, nota1)
    select '41011211-6', id, 5.0 from idiomas.oferta where es_demo and idioma = 'ingles' and nivel = 'Básico A1';
    v_err := 'se aceptó';
  exception when others then v_err := sqlerrm;
  end;
  insert into _r (prueba, ok, detalle) values ('No se registran notas de alumnos sin pago', v_err = 'ALUMNO_NO_PAGADO', v_err);
  begin
    update idiomas.nota set nota1 = 7.5 where rut_estudiante = '41003434-4';
    v_err := 'se aceptó';
  exception when others then v_err := 'rechazado';
  end;
  insert into _r (prueba, ok, detalle) values ('Notas fuera de 1,0-7,0 rechazadas', v_err = 'rechazado', v_err);
end $$;

-- ---------------------------------------------------------------- Docente
do $$
declare n_of int; n_ajenos int; n_mios int; v_ajena bigint; v_mia bigint;
begin
  select id into v_ajena from idiomas.oferta where es_demo and rut_docente = '41002323-7' limit 1;
  select id into v_mia from idiomas.oferta where es_demo and idioma = 'ingles' and nivel = 'Básico A1';
  perform pg_temp.como('docente1@demo.ucn.test');
  set local role authenticated;
  select count(*) into n_of from idiomas.oferta where rut_docente <> '41000101-2' or rut_docente is null;
  select count(*) into n_ajenos from idiomas.alumnos_de_oferta(v_ajena);
  select count(*) into n_mios from idiomas.alumnos_de_oferta(v_mia);
  reset role;
  insert into _r (prueba, ok, detalle) values ('Docente solo ve sus cursos', n_of = 0, n_of || ' ajenos visibles');
  insert into _r (prueba, ok, detalle) values ('Docente ve solo alumnos pagados de su curso',
    n_ajenos = 0 and n_mios = (select count(*) from idiomas.estudiante_pagado where oferta_id = v_mia),
    format('ajenos=%s mios=%s', n_ajenos, n_mios));
end $$;

-- ---------------------------------------------------------------- Alumno
do $$
declare n_est int; n_cert int;
begin
  perform pg_temp.como('alumno@demo.ucn.test');
  set local role authenticated;
  select count(*) into n_est from idiomas.estudiante;
  select count(*) into n_cert from idiomas.certificado;
  reset role;
  insert into _r (prueba, ok, detalle) values ('Alumno solo ve su propia ficha', n_est = 1, n_est::text);
  insert into _r (prueba, ok, detalle) values ('Alumno ve su certificado entregado', n_cert = 1, n_cert::text);
end $$;

-- ---------------------------------------------------------------- Certificados
insert into _r (prueba, ok, detalle)
select 'Certificados demo en los 4 estados', count(distinct estado) = 4, string_agg(distinct estado, ', ') from idiomas.certificado;
insert into _r (prueba, ok, detalle)
select 'Certificables = solo con notas completas', bool_and(nota_final is not null), count(*)::text from idiomas.v_certificable;

do $$
declare v_of bigint; v_err text;
begin
  select id into v_of from idiomas.oferta where es_demo and idioma = 'ingles' and nivel = 'Básico A1';
  begin
    perform idiomas.cambiar_estado_certificado('41013433-0', v_of, 'solicitado');
    v_err := 'se aceptó';
  exception when others then v_err := sqlerrm;
  end;
  insert into _r (prueba, ok, detalle) values ('Certificado exige notas completas', v_err = 'NOTAS_INCOMPLETAS', v_err);
  begin
    perform idiomas.cambiar_estado_certificado('41007878-3', v_of, 'entregado');
    v_err := 'se aceptó';
  exception when others then v_err := sqlerrm;
  end;
  insert into _r (prueba, ok, detalle) values ('«Entregado» exige PDF', v_err like '%certificado_entregado_con_archivo%', v_err);
  begin
    perform idiomas.cambiar_estado_certificado('41007878-3', v_of, 'solicitado');
    v_err := 'se aceptó';
  exception when others then v_err := sqlerrm;
  end;
  insert into _r (prueba, ok, detalle) values ('Retroceso sin confirmar bloqueado', v_err = 'RETROCESO_NO_CONFIRMADO', v_err);
  perform idiomas.cambiar_estado_certificado('41007878-3', v_of, 'solicitado', null, null, true);
  insert into _r (prueba, ok, detalle) select 'Retroceso confirmado limpia fechas posteriores',
    estado = 'solicitado' and fecha_firma is null and fecha_pendiente is null, null
    from idiomas.certificado where rut_estudiante = '41007878-3';
end $$;

-- ---------------------------------------------------------------- RUT como llave: ON UPDATE CASCADE
do $$
begin
  update idiomas.estudiante set rut = '41025654-1' where rut = '41020099-6';
  insert into _r (prueba, ok) select 'Cambiar un RUT se propaga a inscripción',
    exists (select 1 from idiomas.inscripcion where rut_estudiante = '41025654-1');
end $$;

select n, prueba, case when ok then 'OK' else 'FALLA' end as resultado, detalle from _r order by n;
rollback;
