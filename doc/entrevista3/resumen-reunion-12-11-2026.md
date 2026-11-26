# Entrevista 3: Reunión con la coordinadora de Idiomas

| | |
|---|---|
| **Fecha** | Jueves 12 de noviembre de 2026 |
| **Modalidad** | Reunión virtual (videollamada con pantalla compartida) |
| **Socio comunitario** | Sección de Idiomas, Dirección de Relaciones Internacionales UCN |
| **Participantes** | Jocelyn Moraleda (coordinadora de Idiomas), Ashlee Mansilla y Constanza Cid (equipo) |
| **Ausente** | Valentina Restrepo (por trabajo) |
| **Fuente** | Transcripción automática (TurboScribe) de la grabación. Cubre los primeros 30 de los ~33 minutos de la reunión. |

## Objetivo de la reunión

1. Presentar el prototipo de la plataforma integrada (con datos ficticios) y recoger observaciones.
2. Pedir datos para construir los KPI y el dashboard.
3. Validar con la coordinadora el diagrama del proceso actual (AS-IS) y presentar el proceso nuevo (TO-BE).

---

## 1. Revisión del prototipo

### 1.1 Formulario de inscripción
- La coordinadora pidió mantener **todos los campos del formulario actual**, porque ya está validado con otras direcciones de la universidad (género, inclusión, etc.).
- Campos obligatorios que faltan, porque los exige **Educación Continua**:
  - Fecha de nacimiento
  - Nacionalidad
  - Datos de contacto
  - **Condición de salud** (opcional para quien se inscribe). Sirve para que el docente adapte su metodología si alguien lo necesita.

### 1.2 Resumen (inicio de sesión de la coordinadora)
- Muestra a los estudiantes por tipo: egresados, posgrado, pregrado y externos. También compara el mínimo de inscritos con los inscritos actuales, para saber si se puede abrir el curso.
- **Pedidos nuevos:**
  - Agregar un **filtro por campus** (por ejemplo, cuántos egresados son de Antofagasta y cuántos de Coquimbo), igual que el filtro de vínculo con la UCN que ya existe.
  - Agregar un **filtro por género** (hombre/mujer).
  - Motivo: esos datos se usan después en investigaciones y estudios internos.

### 1.3 Solicitudes de inscripción
- Cuando una persona completa el formulario, su información llega sola a la plataforma, con opciones para **aprobar o rechazar** la solicitud.
- Al aprobarla, la persona pasa directamente a la base de datos de estudiantes.
- La coordinadora también puede **registrar a una persona a mano** (si alguien tiene problemas con el formulario). Le gustó mucho esta función.

### 1.4 Cursos
- Al abrir un curso se configuran los grupos mínimo y máximo, el valor y la modalidad.
- **Corrección:** según la definición de la universidad, las modalidades son **presencial, virtual o híbrida**. Hay que cambiar "online" por **"virtual"**.
- Todas las tablas oficiales se pueden **descargar en Excel**.
- El equipo intentará conectar la plataforma con hojas de cálculo nuevas, para que los datos se copien solos. La coordinadora quiere **las dos opciones** (descargar y sincronizar).

### 1.5 Pagos
- Permite registrar el pago y su estado por persona y curso, adjuntar el comprobante (banco, fecha) y filtrar.
- Pendiente:
  - Cambiar el ID para que no sea solo un número correlativo (usar el **RUT**).
  - Conectar la plataforma con el **Drive** que compartió la coordinadora, para que los comprobantes se guarden ahí solos. Por ahora no se pueden subir archivos porque la plataforma no está conectada a nada.

### 1.6 Certificados, asistencia y notas
- **Certificados:** se registra el certificado de cada estudiante, se filtra por estado y se puede descargar en Excel.
- **Asistencia:** se ve por curso, con porcentaje.
- **Notas:** se ven por curso.
- **Rol docente:** ve solo asistencia y notas, nada más.

### 1.7 Accesos y usuarios
- La plataforma está hecha en **Supabase**, donde se crean los roles y usuarios. El equipo le enseñará a la coordinadora a administrarlos.
- Hay muchos docentes (solo en inglés son 13). Por eso se acordó usar **un solo usuario genérico para los docentes**, que filtra por curso o idioma para pasar lista.
- Siguiendo lo que indicó la profesora Carolina en la reunión anterior, por ahora se usarán **solo usuarios de prueba** con correos ficticios.
- **Entrega:** el prototipo se entregará sin costo, mediante un link, para que la sección cargue sus correos reales.
- **Alcance:** el prototipo es parte de la asignatura Integrador Transversal. Las mejoras más avanzadas (por ejemplo, las nuevas solicitudes sobre estudiantes) podrían hacerse como **proyecto de tesis** y eventualmente cobrarse. La coordinadora dijo que le interesa esa opción.

---

## 2. Datos para KPI y dashboard

- La profesora del ramo pidió **KPI específicos del área**, y la base de datos de ejemplo que compartió la coordinadora solo tiene nombre y correo.
- La coordinadora aclaró que eso era solo un ejemplo de un semestre. La sección tiene una base de datos mucho más amplia: el programa existe desde **2011**.
- Se acordó pedir los datos **de 2022 a 2026** (cuatro años, porque habrá varios KPI).
- Para la **presentación del lunes 16/11** hay que mostrar algunos KPI aplicados al área, con sus fórmulas, para demostrar cómo la plataforma mejora el procesamiento de la información (por ejemplo, reduciendo tiempos).

### Tiempo del proceso manual (dato de partida para los KPI)
- No lo hace la coordinadora, sino una **estudiante ayudante** que va 2 veces por semana, unas 3 horas cada vez.
- Si se dedicara solo a eso, tomaría **una semana**. Repartido en el tiempo, unas **dos semanas**.
- Solo cargar los datos de las personas toma unas **12 horas**, pero el resto del proceso se reparte durante todo el semestre.
- La coordinadora **va a calcularlo con más precisión** y lo enviará.

---

## 3. Validación del proceso actual (AS-IS)

La coordinadora confirmó que el diagrama refleja el proceso, con estas correcciones:

1. **Agregar la "Apertura de convocatoria"** como hito explícito. Los cursos no se abren en cualquier momento, sino **solo dos veces al año** (marzo y agosto).
2. **Distinguir dos tipos de convocatoria:**
   - **Abierta** a todo público (dos veces al año).
   - **Cerrada**, para empresas: la empresa pide una cotización por correo y se abre una convocatoria solo para ella.
3. La persona interesada tiene **dos vías**: enviar un correo de interés o inscribirse directamente en la página de la convocatoria.
4. **Agregar la encuesta de satisfacción** antes de pedir los certificados:
   - En el carril del **participante**: responder la encuesta de satisfacción antes de recibir el certificado.
   - En el carril de la **coordinadora**: enviar la encuesta y **tabular los resultados** antes de pedir los certificados a Secretaría General.

El resto de la secuencia se mantiene: respuesta con plantilla, redirección a la web, formulario, registro en Excel, cierre de convocatoria, cierre o apertura del curso según los inscritos, contratación del docente, clases, registro de asistencia y notas, uso de la plataforma, fin del curso, solicitud y entrega de certificados.

## 4. Presentación del proceso nuevo (TO-BE)

Se mostró el flujo con la plataforma integrada:

1. El estudiante envía su solicitud de inscripción a la plataforma, que crea una **ficha única** y valida los datos.
2. La coordinadora revisa la solicitud y envía la convocatoria.
3. El estudiante confirma la matrícula, paga y envía el comprobante.
4. La coordinadora valida la matrícula y el estado del pago. La plataforma cuenta las matrículas confirmadas.
5. **Decisión: ¿se alcanzó el mínimo de inscritos?**
   - **No:** se avisa del cierre del curso al estudiante y el proceso termina.
   - **Sí:** se confirma el curso y se asigna al docente.
6. El docente registra asistencia y notas por sesión. La plataforma consolida el avance y detecta lo que falta.
7. **Decisión: ¿cumple los criterios de aprobación?**
   - **No:** se informan los requisitos pendientes al participante y el proceso termina.
   - **Sí:** se pide el certificado a Secretaría General, que lo devuelve validado, y la coordinadora lo archiva.
- El proceso interno de Secretaría General quedó fuera del alcance, por ser un proceso externo.

**Observación de la coordinadora:** preguntó qué pasa con los datos de las personas cuyo curso **no se abre**. Quiere que esa información **quede registrada** en la plataforma, para saber quién se interesó pero no llegó a tomar un curso.

---

## 5. Acuerdos y tareas

| # | Tarea | Responsable | Plazo |
|---|---|---|---|
| 1 | Enviar la base de datos histórica 2022–2026 | Coordinadora | 12/11, ~17:00 |
| 2 | Enviar el cálculo de horas que toma el proceso manual | Coordinadora | 12/11, ~17:00 |
| 3 | Agregar al formulario: fecha de nacimiento, nacionalidad, contacto y condición de salud (opcional), manteniendo los campos del formulario actual | Equipo | Antes de la entrega |
| 4 | Agregar filtros por **campus** y **género** en el resumen | Equipo | Antes de la entrega |
| 5 | Cambiar la modalidad "online" por **"virtual"** | Equipo | Antes de la entrega |
| 6 | Usar el RUT como identificador en pagos | Equipo | Antes de la entrega |
| 7 | Conectar con el Drive de la sección (comprobantes) y con hojas de cálculo (exportación automática) | Equipo | Por confirmar |
| 8 | Registrar a las personas inscritas en cursos que no se abrieron | Equipo | Por confirmar |
| 9 | Corregir el diagrama AS-IS: apertura de convocatoria, convocatoria abierta/cerrada y encuesta de satisfacción con su tabulación | Equipo | Antes de la presentación |
| 10 | Preparar los KPI con sus fórmulas para la presentación | Equipo | Lunes 16/11 |
| 11 | Configurar un usuario docente genérico y usuarios de prueba | Equipo | Antes de la entrega |
| 12 | Seguir la comunicación por chat ante cualquier duda | Ambos | Continuo |

## 6. Notas para el equipo

- La mayor prioridad para la coordinadora es la **distinción por vínculo con la UCN** (tipo de estudiante). Ya está implementada y la valoró.
- Los datos por campus y género son importantes para los estudios internos de la sección. Conviene considerarlos también en los KPI.
- Las solicitudes que superan el alcance del ramo quedan anotadas como posibles mejoras para una futura tesis.
