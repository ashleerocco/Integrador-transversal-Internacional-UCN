-- =====================================================================
-- SEED DEMO (Grupo B · SOLO DESARROLLO). Datos 100 % ficticios, marcados es_demo.
-- RUT válidos inventados (rango 41.xxx.xxx) y correos @demo.ucn.test.
-- Idempotente: si ya hay datos demo, primero ejecuta reset_demo.sql.
--
-- ABORTA si:
--   · no existe la marca de entorno de desarrollo:
--       insert into idiomas.config (clave, valor) values ('entorno', '"desarrollo"')
--       on conflict (clave) do update set valor = excluded.valor;
--   · hay estudiantes reales (no demo) en idiomas.estudiante, o
--   · el esquema antiguo public.estudiante tiene filas (señal de producción).
-- Los usuarios demo reciben una contraseña ALEATORIA que se muestra al final
-- (no queda ninguna contraseña escrita en el repositorio).
-- =====================================================================

do $$
begin
  if coalesce(idiomas.config_valor('entorno') #>> '{}', '') <> 'desarrollo' then
    raise exception 'SEED ABORTADO: falta la marca idiomas.config.entorno = "desarrollo" (¿es producción?)';
  end if;
  if exists (select 1 from idiomas.estudiante where not es_demo) then
    raise exception 'SEED ABORTADO: hay estudiantes reales en idiomas.estudiante';
  end if;
  if to_regclass('public.estudiante') is not null then
    if exists (select 1 from public.estudiante) then
      raise exception 'SEED ABORTADO: public.estudiante tiene datos (parece producción)';
    end if;
  end if;
  if exists (select 1 from idiomas.convocatoria where es_demo) then
    raise exception 'SEED ABORTADO: ya hay datos demo. Ejecuta reset_demo.sql primero.';
  end if;
end $$;

create temp table _demo_pw as select 'Demo-' || substr(md5(random()::text), 1, 10) || '!' as pw;

-- ---------------------------------------------------------------- Docentes
insert into idiomas.docente (rut, nombres, apellidos, correo, telefono, es_demo) values
  ('41000101-2', 'Carla',   'Docente Uno',  'docente1@demo.ucn.test', '+56 9 1111 0001', true),
  ('41001212-K', 'Matías',  'Docente Dos',  'docente2@demo.ucn.test', '+56 9 1111 0002', true),
  ('41002323-7', 'Hye-jin', 'Docente Tres', 'docente3@demo.ucn.test', '+56 9 1111 0003', true);

-- ---------------------------------------------------------------- Convocatorias
insert into idiomas.convocatoria (nombre, periodo, fecha_apertura, fecha_cierre, fecha_confirmacion,
  fecha_inicio_curso, fecha_fin_curso, fechas_cuotas, estado, es_demo) values
  ('DEMO Cursos Idiomas PIE-UCN 1-2027', '1-2027', current_date - 30, current_date + 20, current_date + 25,
   current_date - 28, current_date + 42,
   array[current_date - 20, current_date + 10, current_date + 40]::date[], 'abierta', true),
  ('DEMO Cursos Idiomas PIE-UCN 2-2027', '2-2027', current_date + 90, current_date + 120, current_date + 125,
   current_date + 130, current_date + 200, '{}', 'borrador', true);

-- ---------------------------------------------------------------- Ofertas (6 idiomas + TOEFL)
with c as (select id from idiomas.convocatoria where nombre = 'DEMO Cursos Idiomas PIE-UCN 1-2027')
insert into idiomas.oferta (convocatoria_id, idioma, nivel, modalidad, sede, dias, hora_inicio, hora_fin, horario_texto,
                            rut_docente, cupo_minimo, cupo_maximo, valor_universal, es_demo)
select c.id, x.* from c, (values
  ('ingles',    'Básico A1',         'Presencial', 'antofagasta', '{1,3}'::smallint[], '19:45'::time, '21:15'::time, null, '41000101-2', 5, 10, null::numeric, true),
  ('ingles',    'Intermedio B1.1',   'Presencial', 'coquimbo',    '{2,4}'::smallint[], '13:00', '14:30', null, '41001212-K', 5, 10, null, true),
  ('ingles',    'Alto Intermedio B2.1', 'Presencial', 'coquimbo', '{}'::smallint[], null, null, 'a convenir lunes, jueves y viernes', null, 5, 10, null, true),
  ('aleman',    'A1.1',              'Virtual',    'virtual',     '{1,3}', '18:00', '19:30', null, '41002323-7', 5, 10, 190000, true),
  ('frances',   'A1.1',              'Virtual',    'virtual',     '{1,3}', '18:00', '19:30', null, '41002323-7', 5, 10, 190000, true),
  ('coreano',   'A1.1',              'Virtual',    'virtual',     '{1,3}', '18:30', '20:00', null, '41002323-7', 5, 10, 190000, true),
  ('italiano',  'A1.1',              'Virtual',    'virtual',     '{2,4}', '13:00', '14:30', null, '41001212-K', 5, 10, 190000, true),
  ('portugues', 'A1.1',              'Virtual',    'virtual',     '{2,4}', '18:00', '19:30', null, '41001212-K', 5, 10, 190000, true),
  ('ingles',    'Preparación TOEFL', 'Virtual',    'virtual',     '{1,3}', '18:00', '19:30', null, '41000101-2', 5, 10, 260000, true)
) as x(idioma, nivel, modalidad, sede, dias, hora_inicio, hora_fin, horario_texto, rut_docente, cmin, cmax, valor, es_demo);

insert into idiomas.oferta_valor (oferta_id, categoria_precio, valor)
select o.id, v.cat, v.valor from idiomas.oferta o
cross join (values ('ucn', 190000), ('egresado_funcionario', 210000), ('externo', 220000)) v(cat, valor)
where o.es_demo and o.valor_universal is null
on conflict do nothing;

create temp table _of as
select id, idioma || '|' || nivel as k from idiomas.oferta where es_demo;

-- ---------------------------------------------------------------- Estudiantes (17, todos los vínculos/géneros/campus)
insert into idiomas.estudiante (rut, tipo_documento, correo, nombres, apellido_paterno, apellido_materno, sexo, genero,
  nombre_social, pronombres, fecha_nacimiento, carrera, campus, campus_otro, nacionalidad, vinculo, vinculo_detalle,
  telefono, salud_tiene_condicion, salud_requerimiento, consentimiento_datos, fecha_consentimiento, origen, es_demo) values
  ('41003434-4','RUT','ana.demo@demo.ucn.test','Ana','Pérez','Rojas','Mujer','Femenino',null,'ella','2003-04-12','Ingeniería Comercial','antofagasta',null,'Chile','pregrado',null,'+56 9 2000 0001',false,null,true,now(),'solicitud',true),
  ('41004545-1','RUT','bruno.demo@demo.ucn.test','Bruno','Soto','Díaz','Hombre','Masculino',null,'él','2001-09-30','Geología','antofagasta',null,'Chile','pregrado',null,'+56 9 2000 0002',false,null,true,now(),'solicitud',true),
  ('41005656-9','RUT','cami.demo@demo.ucn.test','Camila','Muñoz','Vega','Mujer','Otro','Cami','elle','2000-01-20','Periodismo','coquimbo',null,'Chile','pregrado',null,'+56 9 2000 0003',true,'Necesita subtítulos en material audiovisual',true,now(),'solicitud',true),
  ('41006767-6','RUT','diego.demo@demo.ucn.test','Diego','Araya','López','Hombre','Masculino',null,'él','1995-06-02','Magíster en Ingeniería','antofagasta',null,'Chile','posgrado',null,'+56 9 2000 0004',false,null,true,now(),'solicitud',true),
  ('41007878-3','RUT','elena.demo@demo.ucn.test','Elena','Castro','Mora','Mujer','Femenino',null,'ella','1990-11-15','Kinesióloga','antofagasta',null,'Chile','egresado',null,'+56 9 2000 0005',false,null,true,now(),'solicitud',true),
  ('41008989-0','RUT','felipe.demo@demo.ucn.test','Felipe','Rivas','Fuentes','Hombre','Masculino',null,'él','1987-03-08','Arquitecto','coquimbo',null,'Chile','egresado',null,null,false,null,true,now(),'coordinacion',true),
  ('41010100-9','RUT','gabriela.demo@demo.ucn.test','Gabriela','Torres','Silva','Mujer','Femenino',null,'ella','1985-12-01','Diseñadora de modas',null,null,'Colombia','externo',null,'+56 9 2000 0007',false,null,true,now(),'solicitud',true),
  ('41011211-6','RUT','hector.demo@demo.ucn.test','Héctor','Navarro','Pinto','Hombre','Masculino',null,'él','1979-07-19','Tecnólogo médico',null,null,'Chile','externo',null,'+56 9 2000 0008',false,null,true,now(),'solicitud',true),
  ('41012322-3','RUT','ines.demo@demo.ucn.test','Inés','Vargas','Reyes','Prefiero no decirlo','Otro',null,'elle','1998-02-27','Matrona','otro','Sede Calama','Bolivia','externo',null,'+56 9 2000 0009',false,null,true,now(),'solicitud',true),
  ('41013433-0','RUT','javier.demo@demo.ucn.test','Javier','Lagos','Cortés','Hombre','Masculino',null,'él','1975-05-05','Administrativo DGE','antofagasta',null,'Chile','otros','funcionario','+56 9 2000 0010',false,null,true,now(),'solicitud',true),
  ('41014544-8','RUT','karla.demo@demo.ucn.test','Karla','Henríquez','Saavedra','Mujer','Femenino',null,'ella','2002-08-14','Estudiante Universidad de Antofagasta',null,null,'Chile','otros','otra_institucion','+56 9 2000 0011',false,null,true,now(),'solicitud',true),
  ('41015655-5','RUT','luis.demo@demo.ucn.test','Luis','Contreras','Bravo','Hombre','Masculino',null,'él','1969-10-10','Contador auditor',null,null,'Chile','otros','otro',null,false,null,true,now(),'coordinacion',true),
  ('41016766-2','RUT','maria.demo@demo.ucn.test','María','Gallardo','Ortiz','Mujer','Femenino',null,'ella','1993-04-04','Ingeniera en Minas','antofagasta',null,'Chile','egresado',null,'+56 9 2000 0013',true,'Atención con baja audición: sentarse adelante',true,now(),'solicitud',true),
  ('41017877-K','RUT','nicolas.demo@demo.ucn.test','Nicolás','Fernández','Valdés','Hombre','Masculino',null,'él','2004-01-31','Derecho','coquimbo',null,'Chile','pregrado',null,'+56 9 2000 0014',false,null,true,now(),'solicitud',true),
  ('41018988-7','RUT','olivia.demo@demo.ucn.test','Olivia','Sepúlveda','Carrasco','Mujer','Femenino',null,'ella','1999-09-09','Química y Farmacia','antofagasta',null,'Venezuela','posgrado',null,'+56 9 2000 0015',false,null,true,now(),'solicitud',true),
  ('41020099-6','RUT','pablo.demo@demo.ucn.test','Pablo','Morales','Ibáñez','Hombre','Masculino',null,'él','1991-12-24','Profesor de Historia',null,null,'Perú','externo',null,'+56 9 2000 0016',false,null,true,now(),'solicitud',true),
  ('DEMO12345','Pasaporte','quinn.demo@demo.ucn.test','Quinn','Smith','Taylor','Prefiero no decirlo','Otro',null,'they','1996-03-03','Software engineer',null,null,'Estados Unidos','externo',null,'+1 555 0100 200',false,null,true,now(),'solicitud',true);

insert into idiomas.documento_estudiante (rut_estudiante, tipo, drive_file_id, drive_url, estado_archivo)
select e.rut, t.tipo, null, null, 'pendiente_subir' from idiomas.estudiante e
cross join (values ('cedula'), ('licencia')) t(tipo) where e.es_demo
on conflict do nothing;

-- ---------------------------------------------------------------- Inscripciones
-- Inglés A1 Antofagasta: 7 inscritos (SOBRE el mínimo de 5); Inglés B1.1 Coquimbo: 2 (BAJO el mínimo)
insert into idiomas.inscripcion (rut_estudiante, oferta_id, origen, forma_pago, monto_total, es_demo)
select x.rut, o.id, x.origen, x.fp,
       idiomas.precio_oferta(o.id, e.vinculo, e.vinculo_detalle), true
from (values
  ('41003434-4','ingles|Básico A1','solicitud','tres_cuotas'),
  ('41004545-1','ingles|Básico A1','solicitud','contado'),
  ('41007878-3','ingles|Básico A1','solicitud','tres_cuotas'),
  ('41010100-9','ingles|Básico A1','solicitud','contado'),
  ('41011211-6','ingles|Básico A1','solicitud','tres_cuotas'),
  ('41013433-0','ingles|Básico A1','solicitud','unidad_beca'),
  ('41016766-2','ingles|Básico A1','solicitud','tres_cuotas'),
  ('41005656-9','ingles|Intermedio B1.1','solicitud','contado'),
  ('41017877-K','ingles|Intermedio B1.1','solicitud','sindicato'),
  ('41006767-6','aleman|A1.1','solicitud','contado'),
  ('41008989-0','aleman|A1.1','coordinacion','tres_cuotas'),
  ('41018988-7','aleman|A1.1','solicitud','contado'),
  ('41012322-3','frances|A1.1','solicitud','tres_cuotas'),
  ('41014544-8','frances|A1.1','solicitud','contado'),
  ('41015655-5','coreano|A1.1','coordinacion','contado'),
  ('41020099-6','italiano|A1.1','solicitud','contado'),
  ('DEMO12345','ingles|Básico A1','solicitud','contado')
) as x(rut, k, origen, fp)
join _of o on o.k = x.k
join idiomas.estudiante e on e.rut = x.rut;

-- ---------------------------------------------------------------- Solicitudes (3 estados)
insert into idiomas.solicitud (codigo, estado, correo, idioma, modalidad, oferta_id, otro_idioma_nivel, nombres,
  apellido_paterno, apellido_materno, sexo, genero, pronombres, tipo_documento, rut, fecha_nacimiento,
  cedula_estado, licencia_estado, carrera, campus, nacionalidad, vinculo, vinculo_detalle, telefono,
  salud_tiene_condicion, forma_pago, acepta_terminos, consentimiento_datos, revisado_en, motivo_rechazo, es_demo)
select x.codigo, x.estado, x.correo, split_part(x.k, '|', 1), x.modalidad, o.id, x.otro, x.nombres, x.ap, x.am,
       x.sexo, x.genero, x.pron, x.tipo, x.rut, x.fnac::date, 'pendiente_subir', 'pendiente_subir', x.carrera,
       x.campus, 'Chile', x.vinculo, null, '+56 9 3000 0000', false, x.fp, true, true,
       case when x.estado <> 'pendiente' then now() end, x.motivo, true
from (values
  ('DEMO-0001','aceptada','ana.demo@demo.ucn.test','ingles|Básico A1','Presencial',null,'Ana','Pérez','Rojas','Mujer','Femenino','ella','RUT','41003434-4','2003-04-12','Ingeniería Comercial','antofagasta','pregrado','tres_cuotas',null),
  ('DEMO-0002','aceptada','cami.demo@demo.ucn.test','ingles|Intermedio B1.1','Presencial',null,'Camila','Muñoz','Vega','Mujer','Otro','elle','RUT','41005656-9','2000-01-20','Periodismo','coquimbo','pregrado','contado',null),
  ('DEMO-0003','pendiente','rosa.demo@demo.ucn.test','ingles|Intermedio B1.1','Presencial',null,'Rosa','Quiroz','Esquivel','Mujer','Femenino','ella','RUT','41021210-2','1997-05-21','Enfermera','coquimbo','egresado','tres_cuotas',null),
  ('DEMO-0004','pendiente','sergio.demo@demo.ucn.test','portugues|A1.1','Virtual',null,'Sergio','Lazo','Díaz','Hombre','Masculino','él','RUT','41022321-K','1988-02-02','Ingeniero civil',null,'externo','contado',null),
  ('DEMO-0005','pendiente','ana.demo@demo.ucn.test','frances|A1.1','Virtual',null,'Ana','Pérez','Rojas','Mujer','Femenino','ella','RUT','41003434-4','2003-04-12','Ingeniería Comercial','antofagasta','pregrado','contado',null),
  ('DEMO-0006','pendiente','tomas.demo@demo.ucn.test','ingles|__otro__', 'Virtual','Japonés básico','Tomás','Vera','Lillo','Hombre','Masculino','él','RUT','41023432-7','2002-07-07','Ingeniería en Computación','antofagasta','pregrado','contado',null),
  ('DEMO-0007','rechazada','pablo.demo@demo.ucn.test','coreano|A1.1','Virtual',null,'Pablo','Morales','Ibáñez','Hombre','Masculino','él','RUT','41020099-6','1991-12-24','Profesor de Historia',null,'externo','contado','Inscripción duplicada: ya cursa Italiano en el mismo horario')
) as x(codigo, estado, correo, k, modalidad, otro, nombres, ap, am, sexo, genero, pron, tipo, rut, fnac, carrera, campus, vinculo, fp, motivo)
left join _of o on o.k = x.k;
update idiomas.inscripcion i set solicitud_id = s.id from idiomas.solicitud s
 where s.es_demo and s.estado = 'aceptada' and s.rut = i.rut_estudiante and s.oferta_id = i.oferta_id;

-- ---------------------------------------------------------------- Pagos (parciales y totales) -> estudiante_pagado
insert into idiomas.pago (rut_estudiante, oferta_id, fecha, monto, banco, n_transaccion, n_boleta, forma_pago, n_cuota, es_demo)
select x.rut, o.id, current_date + x.dias, x.monto, x.banco, x.tx, x.bol, x.fp, x.cuota, true
from (values
  ('41003434-4','ingles|Básico A1',-35, 63400,'Santander','BG-DEMO-001','C9-D001','tres_cuotas',1),
  ('41003434-4','ingles|Básico A1', -5, 63300,'Santander','BG-DEMO-002','C9-D002','tres_cuotas',2),
  ('41004545-1','ingles|Básico A1',-34,190000,'Banco Estado','8000001','C9-D003','contado',1),
  ('41007878-3','ingles|Básico A1',-33, 70000,'Mercado Pago','108000000001','C9-D004','tres_cuotas',1),
  ('41010100-9','ingles|Básico A1',-33,220000,'Falabella','533900000001','C9-D005','contado',1),
  ('41013433-0','ingles|Básico A1',-32,210000,'Santander','BG-DEMO-006','C9-D006','unidad_beca',1),
  ('41016766-2','ingles|Básico A1',-31, 70000,'Banco Chile','TEF-DEMO-007','C9-D007','tres_cuotas',1),
  ('41005656-9','ingles|Intermedio B1.1',-30,190000,'Santander','BG-DEMO-008','C9-D008','contado',1),
  ('41006767-6','aleman|A1.1',-34,190000,'Coopeuch','DEMO-009','C9-D009','contado',1),
  ('41008989-0','aleman|A1.1',-33, 63400,'Santander','BG-DEMO-010','C9-D010','tres_cuotas',1),
  ('41012322-3','frances|A1.1',-30, 63400,'Banco Estado','8000011','C9-D011','tres_cuotas',1),
  ('41015655-5','coreano|A1.1',-29,190000,'Caja Los Andes','DEMO-012','C9-D012','contado',1)
) as x(rut, k, dias, monto, banco, tx, bol, fp, cuota)
join _of o on o.k = x.k;
-- un pago anulado (devolución) para probar el recálculo
insert into idiomas.pago (rut_estudiante, oferta_id, fecha, monto, banco, n_boleta, forma_pago, n_cuota, estado, motivo_anulacion, es_demo)
select '41014544-8', id, current_date - 28, 190000, 'Santander', 'C9-D013', 'contado', 1, 'anulado', 'Transferencia devuelta (demo)', true
from _of where k = 'frances|A1.1';

-- ---------------------------------------------------------------- Sesiones y asistencia
select idiomas.generar_sesiones(id) from _of;
-- una sesión suspendida (feriado) en Inglés A1
update idiomas.sesion s set suspendida = true, motivo = 'Feriado (demo)'
 where s.oferta_id = (select id from _of where k = 'ingles|Básico A1')
   and s.fecha = (select min(fecha) from idiomas.sesion where oferta_id = s.oferta_id and fecha > current_date - 14);
insert into idiomas.asistencia (rut_estudiante, oferta_id, fecha, estado)
select ep.rut, ep.oferta_id, s.fecha,
       case when s.suspendida then 'S'
            when (abs(hashtext(ep.rut || s.fecha::text)) % 10) = 0 then 'A'
            when (abs(hashtext(ep.rut || s.fecha::text)) % 10) = 1 then 'J'
            else 'P' end
  from idiomas.estudiante_pagado ep
  join idiomas.sesion s on s.oferta_id = ep.oferta_id and s.fecha < current_date
 where ep.oferta_id in (select id from _of);

-- ---------------------------------------------------------------- Notas (completas e incompletas)
insert into idiomas.nota (rut_estudiante, oferta_id, nota1, nota2, nota3, porcentaje1, porcentaje2, porcentaje3)
select x.rut, o.id, x.n1, x.n2, x.n3, x.p1, x.p2, x.p3
from (values
  ('41003434-4','ingles|Básico A1', 6.3, 6.0, 5.9, 96, 87, 85),
  ('41004545-1','ingles|Básico A1', 6.9, 6.6, 5.9, 98, 95, 85),
  ('41007878-3','ingles|Básico A1', 5.0, 7.0, 6.5, 72, 100, 93),
  ('41010100-9','ingles|Básico A1', 5.5, 6.2, 6.1, 78, 89, 88),
  ('41013433-0','ingles|Básico A1', 4.9, 4.2, null, 70, 63, null),   -- incompleta
  ('41016766-2','ingles|Básico A1', 6.6, null, null, 94, null, null), -- incompleta
  ('41006767-6','aleman|A1.1',     7.0, 7.0, 6.1, 100, 100, 88)
) as x(rut, k, n1, n2, n3, p1, p2, p3)
join _of o on o.k = x.k;

-- ---------------------------------------------------------------- Certificados (4 estados)
select idiomas.cambiar_estado_certificado('41003434-4', (select id from _of where k = 'ingles|Básico A1'), 'solicitado');
select idiomas.cambiar_estado_certificado('41004545-1', (select id from _of where k = 'ingles|Básico A1'), 'pendiente');
select idiomas.cambiar_estado_certificado('41007878-3', (select id from _of where k = 'ingles|Básico A1'), 'firmado');
-- "entregado" exige archivo: id ficticio (la descarga mostrará un aviso amable en la demo)
select idiomas.cambiar_estado_certificado('41010100-9', (select id from _of where k = 'ingles|Básico A1'), 'entregado',
                                          'DEMO-SIN-ARCHIVO', 'https://drive.google.com/demo-sin-archivo');
update idiomas.certificado set es_demo = true where oferta_id in (select id from _of);

-- ---------------------------------------------------------------- Usuarios de prueba por rol (Supabase Auth)
do $$
declare
  u record; v_pw text := (select pw from _demo_pw); v_id uuid;
  completo boolean := exists (select 1 from information_schema.columns
                               where table_schema = 'auth' and table_name = 'users' and column_name = 'encrypted_password');
begin
  for u in select * from (values
      ('coordinacion@demo.ucn.test', 'Coordinación (demo)', 'coordinacion', null, null),
      ('docente1@demo.ucn.test', 'Carla Docente Uno (demo)', 'docente', '41000101-2', null),
      ('alumno@demo.ucn.test', 'Gabriela Torres (demo)', 'alumno', null, '41010100-9')
    ) t(email, nombre, rol, rut_doc, rut_est) loop
    v_id := gen_random_uuid();
    if completo then
      insert into auth.users (instance_id, id, aud, role, email, encrypted_password, email_confirmed_at,
                              raw_app_meta_data, raw_user_meta_data, created_at, updated_at,
                              confirmation_token, recovery_token, email_change, email_change_token_new)
      values ('00000000-0000-0000-0000-000000000000', v_id, 'authenticated', 'authenticated', u.email,
              extensions.crypt(v_pw, extensions.gen_salt('bf')), now(),
              '{"provider":"email","providers":["email"]}', jsonb_build_object('demo', true), now(), now(), '', '', '', '');
      insert into auth.identities (id, user_id, provider_id, identity_data, provider, created_at, updated_at, last_sign_in_at)
      values (gen_random_uuid(), v_id, v_id::text, jsonb_build_object('sub', v_id::text, 'email', u.email), 'email', now(), now(), now());
    else
      insert into auth.users (id, email) values (v_id, u.email);  -- entorno de prueba local sin Auth completo
    end if;
    insert into idiomas.perfil (id, nombre, rol, rut_docente, rut_estudiante, es_demo)
    values (v_id, u.nombre, u.rol, u.rut_doc, u.rut_est, true);
  end loop;
end $$;

select 'Usuarios demo: coordinacion@demo.ucn.test, docente1@demo.ucn.test, alumno@demo.ucn.test' as usuarios,
       pw as contrasena_generada_en_esta_ejecucion from _demo_pw;
