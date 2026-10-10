# Sistema de gestión – Sección de Idiomas (UCN Internacional)

Prototipo desarrollado en el curso **Integrador Transversal** (Aprendizaje + Servicio).
Centraliza estudiantes, inscripciones, pagos, asistencia, notas y certificados de la
Sección de Idiomas, hoy dispersos en formularios y archivos Excel.

## Tecnologías
- **Base de datos:** Supabase (PostgreSQL)
- **Aplicación:** Streamlit (Python)
- **Diseño:** Figma · **Procesos:** BPMN (Bizagi)

## Estructura
```
app.py                  Página principal (conexión y resumen)
pages/                  Una página por funcionalidad
supabase_client.py      Conexión a Supabase
db/schema.sql           Creación de tablas y vistas
db/seed_datos_prueba.sql  Datos ficticios de prueba
docs/                   BPMN, requerimientos y otros documentos
.streamlit/secrets.toml.example   Plantilla de credenciales
```

## Cómo ejecutarlo
1. Crear el proyecto en Supabase y ejecutar `db/schema.sql` y luego `db/seed_datos_prueba.sql` en el SQL Editor.
2. Copiar `.streamlit/secrets.toml.example` como `.streamlit/secrets.toml` y completar la URL y la clave.
3. Instalar y ejecutar:
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   streamlit run app.py
   ```

## Funcionalidades (requerimientos)
| Estado | Requerimiento |
|---|---|
| ✅ | RF-01 Registrar y consultar estudiantes con su tipo |
| ⬜ | RF-02 Inscripciones y estado |
| ⬜ | RF-07 Pagos |
| ⬜ | RF-04 / RF-05 Asistencia y notas |
| ⬜ | RF-09 Certificados |
| ⬜ | RF-08 Carga desde Excel |
| ✅ | RF-03 Inscritos frente al mínimo (vista en la página principal) |
| ⬜ | RF-06 Acceso por rol |

## Seguridad y datos
- Las credenciales **no** se suben al repositorio (`.streamlit/secrets.toml` está en `.gitignore`).
- Solo se usan **datos ficticios**. No subir datos personales reales de estudiantes.
