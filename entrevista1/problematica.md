# Problemática del Proyecto

**Proyecto:** Sistema de Gestión Integral para el Área de Idiomas — Dirección de Relaciones Internacionales UCN
**Asignatura:** Integrador Transversal — Ingeniería en Información y Control de Gestión
**Socio comunitario:** Área de Idiomas, Dirección de Relaciones Internacionales, Universidad Católica del Norte

---

## 1. Contexto organizacional

El área de Idiomas de la Dirección de Relaciones Internacionales (DRI) de la UCN tiene como misión reducir la brecha idiomática de la comunidad universitaria (estudiantes, docentes, funcionarios) y generar recursos, a través del cobro de cursos, que financien becas de movilidad estudiantil. A diferencia del área de movilidad estudiantil —que se encuentra consolidada—, el área de Idiomas presenta baja visibilidad institucional y procesos de gestión poco estructurados.

## 2. Descripción de la problemática

El área de Idiomas **no cuenta con un sistema de información centralizado** para gestionar el ciclo completo de sus cursos. Actualmente, la información se encuentra fragmentada en múltiples fuentes desconectadas entre sí:

- Un formulario de inscripción (**Google Form / JotForm**) que genera una planilla inicial.
- Un **archivo Excel** donde los docentes registran manualmente asistencia y notas.
- Un **archivo Excel independiente** para el registro de pagos.
- Plataformas de aprendizaje externas y no integradas (**Cambridge One** para inglés, **campus virtual** para otros idiomas).

Esta fragmentación obliga a la coordinadora del área a cruzar manualmente distintos archivos para obtener una visión completa del estado de cada estudiante (inscripción, asistencia, notas y pago), lo que genera ineficiencia operativa y riesgo de pérdida de información.

## 3. Delimitación

El proyecto se enfocará específicamente en el proceso de **gestión de cursos de idiomas** dictados por el área (inscripción, seguimiento de asistencia y notas, registro de pagos y emisión de información para certificados), dejando fuera de alcance los procesos de movilidad estudiantil, convenios internacionales y otras funciones de la DRI que ya cuentan con procedimientos consolidados.

## 4. Fundamentación

La evidencia recogida durante el levantamiento de información con la coordinadora del área respalda la problemática identificada:

- Sobre la dispersión de los datos, la coordinadora señaló que la información "*está todo disperso*" y que "*si se pierde ese Excel, se pierde toda la información*", evidenciando la ausencia de respaldo y de un repositorio único de datos.
- Respecto a la falta de integración entre asistencia y un sistema formal, indicó que "*la asistencia está en el mismo Excel, pero no es un sistema*", lo que confirma que el registro actual depende de archivos ofimáticos sin lógica de base de datos ni trazabilidad.
- En cuanto a la necesidad de una solución, expresó el deseo de contar con "*una sola plataforma donde se pudiera visualizar claramente*" el número de estudiantes, su avance (asistencia), notas y pagos, de manera que "*todo eso esté en un solo lugar*".

Estas evidencias muestran que el problema no es la falta de datos, sino la **ausencia de una arquitectura de información integrada** que permita registrar, consultar y visualizar de forma coherente el ciclo completo de los cursos de idiomas.

## 5. Impacto de la problemática

| Ámbito afectado | Efecto observado |
|---|---|
| Gestión operativa | Cruce manual de múltiples Excel para obtener información completa de un estudiante |
| Continuidad de la información | Riesgo de pérdida total de datos si se corrompe o extravía un archivo |
| Emisión de certificados | Demoras de aproximadamente un mes entre el término del curso y la firma del secretario general, por falta de datos consolidados y accesibles |
| Seguimiento a estudiantes | Ausencia de seguimiento durante el período de convocatoria, generando incertidumbre en los inscritos |
| Toma de decisiones | Falta de indicadores visuales (cantidad de estudiantes UCN, egresados, externos) para apoyar la gestión del área |

## 6. Problemática priorizada

> **La falta de un sistema de información integrado que centralice la inscripción, el seguimiento de asistencia y notas, y el registro de pagos de los cursos de idiomas, genera ineficiencia operativa, pérdida de trazabilidad y demoras en procesos clave como la emisión de certificados, dificultando la gestión y toma de decisiones del área.**

## 7. Alineación con la solución propuesta

Esta problemática es abordable mediante una solución de Sistemas de Información Administrativos, consistente con la arquitectura sugerida por la asignatura:

- **Aplicación (Streamlit):** ingreso y consulta de inscripciones, asistencia, notas y pagos.
- **Base de datos central (Supabase):** almacenamiento estructurado y único de la información, eliminando la dependencia de archivos Excel dispersos.
- **Dashboard de gestión (Data Studio):** visualización de indicadores clave (N° de estudiantes por categoría, estado de pagos, avance de asistencia) para apoyar la toma de decisiones de la coordinadora.
- **Repositorio GitHub:** documentación y control de versiones del desarrollo.

---
*Documento elaborado a partir del levantamiento de información realizado con el socio comunitario (Área de Idiomas, DRI-UCN). Sujeto a validación y ajustes durante el desarrollo del proyecto.*
