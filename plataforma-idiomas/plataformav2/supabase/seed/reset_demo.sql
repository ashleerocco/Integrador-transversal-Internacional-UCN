-- =====================================================================
-- RESET DEMO (Grupo B · SOLO DESARROLLO). Borra ÚNICAMENTE filas es_demo = true
-- (y los usuarios de Auth @demo.ucn.test). No toca datos reales. Idempotente.
-- =====================================================================
begin;

create temp table _of_demo on commit drop as select id from idiomas.oferta where es_demo;
create temp table _est_demo on commit drop as select rut from idiomas.estudiante where es_demo;

delete from idiomas.certificado where es_demo or (oferta_id in (select id from _of_demo) and rut_estudiante in (select rut from _est_demo));
delete from idiomas.nota where oferta_id in (select id from _of_demo) and rut_estudiante in (select rut from _est_demo);
delete from idiomas.asistencia where oferta_id in (select id from _of_demo) and rut_estudiante in (select rut from _est_demo);
delete from idiomas.pago where es_demo;                           -- el trigger vacía estudiante_pagado
delete from idiomas.estudiante_pagado where oferta_id in (select id from _of_demo) and rut in (select rut from _est_demo);
delete from idiomas.inscripcion where es_demo;
delete from idiomas.solicitud where es_demo;
delete from idiomas.perfil where es_demo;
delete from auth.users where email like '%@demo.ucn.test';
delete from idiomas.documento_estudiante where rut_estudiante in (select rut from _est_demo);
delete from idiomas.estudiante where es_demo;
delete from idiomas.sesion where oferta_id in (select id from _of_demo);
delete from idiomas.oferta where es_demo;                         -- oferta_valor en cascada
delete from idiomas.convocatoria where es_demo;
delete from idiomas.docente where es_demo;

commit;

select (select count(*) from idiomas.estudiante where es_demo) as estudiantes_demo,
       (select count(*) from idiomas.oferta where es_demo) as ofertas_demo,
       (select count(*) from idiomas.estudiante where not es_demo) as estudiantes_reales_intactos;
