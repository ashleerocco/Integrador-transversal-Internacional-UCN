-- =====================================================================
-- Pruebas de acceso de docentes (migración 0005) · SOLO DESARROLLO (requiere seed_demo)
--
-- Simula la sesión de cada usuario (rol authenticated + JWT) como lo haría la API,
-- así que prueba RLS "llamando directamente", no solo la interfaz.
-- NO deja cambios: todo ocurre en un bloque que termina con una excepción
-- (se revierte entero) cuyo mensaje es el informe. Debe decir 0 FALLAS.
-- =====================================================================
do $$
declare
  inf text := '';
  fallas int := 0;
  coord uuid; d1 uuid; d2 uuid; nadie uuid; d3_sin_confirmar uuid;
  rut_d1 text; rut_d2 text;
  of1 bigint; of2 bigint;           -- un curso de docente1 y uno de docente2, ambos con alumnos pagados
  al1 text; al1b text; al2 text;    -- alumnos pagados de of1 (dos) y de of2
  f date := date '2099-01-05';      -- fecha de prueba (no choca con datos reales)
  n int; n2 int;
begin
  -- ---------- preparar (como administrador) ----------
  select p.id into coord from idiomas.perfil p where p.rol = 'coordinacion' limit 1;
  select rut into rut_d1 from idiomas.docente where lower(correo) = 'docente1@demo.ucn.test';
  select rut into rut_d2 from idiomas.docente where lower(correo) = 'docente2@demo.ucn.test';
  select id into d1 from auth.users where lower(email) = 'docente1@demo.ucn.test';
  -- docente2 no tiene cuenta en la demo: se crea una confirmada (se revierte al final)
  insert into auth.users (id, email, email_confirmed_at, aud, role)
  values (gen_random_uuid(), 'docente2@demo.ucn.test', now(), 'authenticated', 'authenticated') returning id into d2;
  insert into auth.users (id, email, email_confirmed_at, aud, role)
  values (gen_random_uuid(), 'nadie@demo.ucn.test', now(), 'authenticated', 'authenticated') returning id into nadie;
  -- docente3 con correo SIN confirmar: no debe obtener acceso
  insert into auth.users (id, email, aud, role)
  values (gen_random_uuid(), 'docente3@demo.ucn.test', 'authenticated', 'authenticated') returning id into d3_sin_confirmar;

  select o.id into of1 from idiomas.oferta o where o.rut_docente = rut_d1
     and exists (select 1 from idiomas.estudiante_pagado ep where ep.oferta_id = o.id having count(*) >= 2) limit 1;
  select o.id into of2 from idiomas.oferta o where o.rut_docente = rut_d2
     and exists (select 1 from idiomas.estudiante_pagado ep where ep.oferta_id = o.id) limit 1;
  select rut into al1 from idiomas.estudiante_pagado where oferta_id = of1 order by rut limit 1;
  select rut into al1b from idiomas.estudiante_pagado where oferta_id = of1 order by rut offset 1 limit 1;
  select rut into al2 from idiomas.estudiante_pagado where oferta_id = of2 order by rut limit 1;
  if coord is null or d1 is null or of1 is null or of2 is null or al1b is null then
    raise exception 'Faltan datos de la demo (¿se cargó seed_demo.sql?)';
  end if;
  -- La asistencia exige que la fecha sea una sesión del curso (FK a sesion): se crean las de prueba,
  -- así los rechazos de abajo se deben al permiso y no a una sesión inexistente.
  insert into idiomas.sesion (oferta_id, fecha) values (of1, f), (of1, f + 7), (of1, f + 14), (of2, f), (of2, f + 1)
    on conflict do nothing;
  insert into idiomas.asistencia (rut_estudiante, oferta_id, fecha, estado) values (al2, of2, f, 'P');
  insert into idiomas.nota (rut_estudiante, oferta_id, nota1) values (al2, of2, 5.0)
    on conflict (rut_estudiante, oferta_id) do update set nota1 = 5.0;

  -- ======================= docente1 =======================
  perform set_config('request.jwt.claims', json_build_object('sub', d1, 'email', 'docente1@demo.ucn.test', 'role', 'authenticated')::text, true);
  set local role authenticated;

  if idiomas.mi_docente_id() = rut_d1 then inf := inf || E'\nOK    1. mi_docente_id() reconoce a docente1 por su correo';
  else fallas := fallas + 1; inf := inf || E'\nFALLA 1. mi_docente_id() no reconoce a docente1'; end if;

  select count(*) into n from idiomas.oferta where rut_docente is distinct from rut_d1;
  if n = 0 and exists (select 1 from idiomas.oferta where id = of1) then inf := inf || E'\nOK    2. docente1 ve solo sus cursos (ninguno de docente2)';
  else fallas := fallas + 1; inf := inf || format(E'\nFALLA 2. docente1 ve %s curso(s) ajenos', n); end if;

  select count(*) into n from idiomas.convocatoria;
  if n = 0 then inf := inf || E'\nOK    3. docente1 no ve convocatorias';
  else fallas := fallas + 1; inf := inf || format(E'\nFALLA 3. docente1 ve %s convocatoria(s)', n); end if;

  select (select count(*) from idiomas.pago) + (select count(*) from idiomas.docente where rut <> rut_d1) into n;
  if n = 0 then inf := inf || E'\nOK    4. docente1 no ve pagos ni datos de otros docentes';
  else fallas := fallas + 1; inf := inf || format(E'\nFALLA 4. docente1 ve %s pago(s)/docente(s) ajenos', n); end if;

  select count(*) into n from idiomas.mis_cursos_docente() where oferta_id = of1;
  if n = 1 and not exists (select 1 from idiomas.mis_cursos_docente() where oferta_id = of2)
  then inf := inf || E'\nOK    5. «Mis cursos» lista sus cursos con nombre y fechas';
  else fallas := fallas + 1; inf := inf || E'\nFALLA 5. mis_cursos_docente() incorrecto'; end if;

  begin
    insert into idiomas.asistencia (rut_estudiante, oferta_id, fecha, estado) values (al1, of1, f, 'A');
    update idiomas.asistencia set estado = 'P' where rut_estudiante = al1 and oferta_id = of1 and fecha = f;
    insert into idiomas.nota (rut_estudiante, oferta_id, nota1) values (al1, of1, 6.5)
      on conflict (rut_estudiante, oferta_id) do update set nota1 = 6.5;
    inf := inf || E'\nOK    6. docente1 registra y edita asistencia y notas de su curso';
  exception when others then
    fallas := fallas + 1; inf := inf || E'\nFALLA 6. docente1 no pudo registrar en su curso: ' || sqlerrm;
  end;

  select count(*) into n from idiomas.asistencia where oferta_id = of2;
  select count(*) + n into n from idiomas.nota where oferta_id = of2;
  if n = 0 then inf := inf || E'\nOK    7. docente1 NO lee asistencia ni notas de otro curso';
  else fallas := fallas + 1; inf := inf || format(E'\nFALLA 7. docente1 lee %s registro(s) de otro curso', n); end if;

  begin
    insert into idiomas.asistencia (rut_estudiante, oferta_id, fecha, estado) values (al2, of2, f + 1, 'P');
    fallas := fallas + 1; inf := inf || E'\nFALLA 8. docente1 pudo INSERTAR asistencia en otro curso';
  exception when insufficient_privilege then inf := inf || E'\nOK    8. docente1 NO puede insertar asistencia en otro curso';
    when others then fallas := fallas + 1; inf := inf || E'\nFALLA 8. error inesperado: ' || sqlerrm;
  end;
  begin
    insert into idiomas.nota (rut_estudiante, oferta_id, nota2) values (al2, of2, 1.0)
      on conflict (rut_estudiante, oferta_id) do update set nota2 = 1.0;
    fallas := fallas + 1; inf := inf || E'\nFALLA 9. docente1 pudo modificar notas de otro curso';
  exception when insufficient_privilege then inf := inf || E'\nOK    9. docente1 NO puede insertar ni modificar notas de otro curso';
    when others then fallas := fallas + 1; inf := inf || E'\nFALLA 9. error inesperado: ' || sqlerrm;
  end;
  update idiomas.asistencia set estado = 'A' where oferta_id = of2;
  get diagnostics n = row_count;
  if n = 0 then inf := inf || E'\nOK   10. docente1 NO puede actualizar asistencia de otro curso (0 filas)';
  else fallas := fallas + 1; inf := inf || format(E'\nFALLA 10. docente1 actualizó %s fila(s) ajenas', n); end if;

  delete from idiomas.asistencia where rut_estudiante = al1 and oferta_id = of1 and fecha = f;
  get diagnostics n = row_count;
  delete from idiomas.nota where rut_estudiante = al1 and oferta_id = of1;
  get diagnostics n2 = row_count;
  if n = 0 and n2 = 0 then inf := inf || E'\nOK   11. docente1 NO puede borrar asistencia ni notas (ni de su curso)';
  else fallas := fallas + 1; inf := inf || E'\nFALLA 11. docente1 pudo borrar registros'; end if;

  begin
    update idiomas.asistencia set fecha = f + 7 where rut_estudiante = al1 and oferta_id = of1 and fecha = f;
    fallas := fallas + 1; inf := inf || E'\nFALLA 12. docente1 pudo cambiar la fecha de un registro';
  exception when others then
    if sqlerrm <> 'NO_PUEDE_CAMBIAR_ALUMNO_CURSO_O_FECHA' then
      fallas := fallas + 1; inf := inf || E'\nFALLA 12. error inesperado al cambiar la fecha: ' || sqlerrm;
    else
      begin
        update idiomas.nota set rut_estudiante = al1b where rut_estudiante = al1 and oferta_id = of1;
        fallas := fallas + 1; inf := inf || E'\nFALLA 12. docente1 pudo cambiar el alumno de una nota';
      exception when others then
        if sqlerrm = 'NO_PUEDE_CAMBIAR_ALUMNO_CURSO_O_FECHA' then
          inf := inf || E'\nOK   12. docente1 NO puede cambiar alumno, curso ni fecha de un registro';
        else fallas := fallas + 1; inf := inf || E'\nFALLA 12. error inesperado al cambiar el alumno: ' || sqlerrm; end if;
      end;
    end if;
  end;

  begin
    perform idiomas.generar_sesiones(of2);
    fallas := fallas + 1; inf := inf || E'\nFALLA 13. docente1 pudo generar sesiones en otro curso';
  exception when others then
    if sqlerrm <> 'SIN_PERMISO_CURSO' then
      fallas := fallas + 1; inf := inf || E'\nFALLA 13. error inesperado: ' || sqlerrm;
    end if;
    begin
      perform idiomas.generar_sesiones(of1);
      inf := inf || E'\nOK   13. generar_sesiones: sí en su curso, no en uno ajeno';
    exception when others then
      fallas := fallas + 1; inf := inf || E'\nFALLA 13. docente1 no pudo generar sesiones en su curso: ' || sqlerrm;
    end;
  end;

  -- Correo en otro formato de mayúsculas: sigue reconociéndolo
  perform set_config('request.jwt.claims', json_build_object('sub', d1, 'email', 'Docente1@DEMO.ucn.test', 'role', 'authenticated')::text, true);
  if idiomas.mi_docente_id() = rut_d1 then inf := inf || E'\nOK   14. el correo se compara sin distinguir mayúsculas';
  else fallas := fallas + 1; inf := inf || E'\nFALLA 14. el correo distingue mayúsculas'; end if;

  -- ======================= coordinación =======================
  reset role;
  perform set_config('request.jwt.claims', json_build_object('sub', coord, 'email', 'coordinacion@demo.ucn.test', 'role', 'authenticated')::text, true);
  set local role authenticated;
  select count(*) into n from idiomas.asistencia
   where rut_estudiante = al1 and oferta_id = of1 and fecha = f and estado = 'P' and actualizado_por = 'docente1@demo.ucn.test';
  if n = 1 and exists (select 1 from idiomas.nota where rut_estudiante = al1 and oferta_id = of1 and nota1 = 6.5)
  then inf := inf || E'\nOK   15. la coordinación ve lo que registró docente1 (y quién lo registró)';
  else fallas := fallas + 1; inf := inf || E'\nFALLA 15. la coordinación no ve lo registrado por docente1'; end if;

  begin
    update idiomas.asistencia set estado = 'J' where rut_estudiante = al2 and oferta_id = of2 and fecha = f;
    get diagnostics n = row_count;
    select count(*) into n2 from idiomas.oferta;
    if n = 1 and n2 = (select count(*) from idiomas.v_oferta) and n2 > 1
    then inf := inf || E'\nOK   16. la coordinación sigue viendo y editando todo';
    else fallas := fallas + 1; inf := inf || E'\nFALLA 16. la coordinación perdió acceso'; end if;
  exception when others then
    fallas := fallas + 1; inf := inf || E'\nFALLA 16. la coordinación no pudo editar: ' || sqlerrm;
  end;

  -- ======================= usuarios sin acceso de docente =======================
  reset role;
  perform set_config('request.jwt.claims', json_build_object('sub', nadie, 'email', 'nadie@demo.ucn.test', 'role', 'authenticated')::text, true);
  set local role authenticated;
  select (select count(*) from idiomas.oferta) + (select count(*) from idiomas.asistencia) + (select count(*) from idiomas.nota)
         + (select count(*) from idiomas.mis_cursos_docente()) into n;
  if idiomas.mi_docente_id() is null and n = 0 then inf := inf || E'\nOK   17. un usuario no docente no ve cursos, asistencia ni notas';
  else fallas := fallas + 1; inf := inf || format(E'\nFALLA 17. usuario no docente ve %s registro(s)', n); end if;

  reset role;
  perform set_config('request.jwt.claims', json_build_object('sub', d3_sin_confirmar, 'email', 'docente3@demo.ucn.test', 'role', 'authenticated')::text, true);
  set local role authenticated;
  if idiomas.mi_docente_id() is null and (select count(*) from idiomas.oferta) = 0
  then inf := inf || E'\nOK   18. una cuenta con el correo del docente SIN confirmar no obtiene acceso';
  else fallas := fallas + 1; inf := inf || E'\nFALLA 18. un correo sin confirmar obtuvo acceso de docente'; end if;

  -- docente2 (cuenta confirmada) ve los suyos y no los de docente1
  reset role;
  perform set_config('request.jwt.claims', json_build_object('sub', d2, 'email', 'docente2@demo.ucn.test', 'role', 'authenticated')::text, true);
  set local role authenticated;
  if exists (select 1 from idiomas.oferta where id = of2) and not exists (select 1 from idiomas.oferta where id = of1)
     and not exists (select 1 from idiomas.asistencia where oferta_id = of1)
  then inf := inf || E'\nOK   19. docente2 ve sus cursos y no los de docente1';
  else fallas := fallas + 1; inf := inf || E'\nFALLA 19. docente2 ve datos de docente1'; end if;

  -- ======================= desactivar a docente1 =======================
  reset role;
  update idiomas.docente set activo = false where rut = rut_d1;
  perform set_config('request.jwt.claims', json_build_object('sub', d1, 'email', 'docente1@demo.ucn.test', 'role', 'authenticated')::text, true);
  set local role authenticated;
  select (select count(*) from idiomas.oferta) + (select count(*) from idiomas.asistencia) + (select count(*) from idiomas.nota) into n;
  begin
    insert into idiomas.asistencia (rut_estudiante, oferta_id, fecha, estado) values (al1, of1, f + 14, 'P');
    fallas := fallas + 1; inf := inf || E'\nFALLA 20. docente1 inactivo aún puede registrar asistencia';
  exception when insufficient_privilege then
    if idiomas.mi_docente_id() is null and n = 0 then inf := inf || E'\nOK   20. al desmarcar «Activo», docente1 pierde todo el acceso';
    else fallas := fallas + 1; inf := inf || format(E'\nFALLA 20. docente1 inactivo aún ve %s registro(s)', n); end if;
    when others then fallas := fallas + 1; inf := inf || E'\nFALLA 20. error inesperado: ' || sqlerrm;
  end;
  reset role;

  raise exception using message = format(E'INFORME (todo revertido, no quedó ningún cambio)%s\n\n%s FALLA(S)', inf, fallas);
end $$;
