-- Campos compartidos por las solicitudes públicas y los registros de coordinación.
-- La migración es aditiva; unidad_ucn se conserva por compatibilidad con consultas existentes.
ALTER TABLE public.estudiante
    ADD COLUMN IF NOT EXISTS carrera text,
    ADD COLUMN IF NOT EXISTS ocupacion text,
    ADD COLUMN IF NOT EXISTS cedula_path text,
    ADD COLUMN IF NOT EXISTS licencia_media_path text,
    ADD COLUMN IF NOT EXISTS consentimiento_datos boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS fecha_consentimiento timestamptz;

ALTER TABLE public.solicitud_inscripcion
    ADD COLUMN IF NOT EXISTS genero text,
    ADD COLUMN IF NOT EXISTS nombre_social text,
    ADD COLUMN IF NOT EXISTS pronombres text,
    ADD COLUMN IF NOT EXISTS carrera text,
    ADD COLUMN IF NOT EXISTS ocupacion text,
    ADD COLUMN IF NOT EXISTS nacionalidad text,
    ADD COLUMN IF NOT EXISTS condicion_salud text,
    ADD COLUMN IF NOT EXISTS cedula_path text,
    ADD COLUMN IF NOT EXISTS licencia_media_path text,
    ADD COLUMN IF NOT EXISTS consentimiento_datos boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS fecha_consentimiento timestamptz;

-- Copia sin borrar ni modificar unidad_ucn: pantallas antiguas pueden seguir usándola.
UPDATE public.estudiante
SET carrera = unidad_ucn
WHERE carrera IS NULL AND unidad_ucn IS NOT NULL;

-- Conserva los IDs antiguos referenciados y sólo agrega vínculos que falten.
INSERT INTO public.tipo_estudiante (nombre)
SELECT opciones.nombre
FROM (VALUES
    ('Estudiante de pregrado'),
    ('Estudiante de posgrado'),
    ('Egresado/a'),
    ('Externo/a'),
    ('Otros')
) AS opciones(nombre)
WHERE NOT EXISTS (
    SELECT 1 FROM public.tipo_estudiante actual WHERE actual.nombre = opciones.nombre
);

-- Storage privado: coordinación puede gestionar; cada estudiante autenticado sólo lee
-- documentos cuyo RUT coincide con el suyo y con el correo de su sesión.
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'documentos_estudiantes', 'documentos_estudiantes', false, 5242880,
    ARRAY['application/pdf', 'image/jpeg', 'image/png']
)
ON CONFLICT (id) DO UPDATE SET
    public = false,
    file_size_limit = 5242880,
    allowed_mime_types = ARRAY['application/pdf', 'image/jpeg', 'image/png'];

ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS documentos_estudiantes_coordinacion_lectura ON storage.objects;
CREATE POLICY documentos_estudiantes_coordinacion_lectura
ON storage.objects FOR SELECT TO authenticated
USING (
    bucket_id = 'documentos_estudiantes'
    AND EXISTS (
        SELECT 1 FROM public.perfil p
        WHERE p.id = auth.uid() AND p.rol = 'coordinadora'
    )
);

DROP POLICY IF EXISTS documentos_estudiantes_coordinacion_escritura ON storage.objects;
CREATE POLICY documentos_estudiantes_coordinacion_escritura
ON storage.objects FOR ALL TO authenticated
USING (
    bucket_id = 'documentos_estudiantes'
    AND EXISTS (
        SELECT 1 FROM public.perfil p
        WHERE p.id = auth.uid() AND p.rol = 'coordinadora'
    )
)
WITH CHECK (
    bucket_id = 'documentos_estudiantes'
    AND EXISTS (
        SELECT 1 FROM public.perfil p
        WHERE p.id = auth.uid() AND p.rol = 'coordinadora'
    )
);

DROP POLICY IF EXISTS documentos_estudiantes_lectura_propia ON storage.objects;
CREATE POLICY documentos_estudiantes_lectura_propia
ON storage.objects FOR SELECT TO authenticated
USING (
    bucket_id = 'documentos_estudiantes'
    AND EXISTS (
        SELECT 1 FROM public.estudiante e
        WHERE e.documento = CASE
            WHEN (storage.foldername(name))[1] = 'solicitudes'
                THEN (storage.foldername(name))[2]
            ELSE (storage.foldername(name))[1]
        END
        AND lower(e.correo) = lower(auth.jwt() ->> 'email')
    )
);

-- El formulario anónimo sólo puede cargar archivos dentro de solicitudes/. No hay
-- política SELECT, por lo que una sesión anónima nunca puede leerlos ni firmarlos.
DROP POLICY IF EXISTS documentos_estudiantes_carga_solicitud_publica ON storage.objects;
CREATE POLICY documentos_estudiantes_carga_solicitud_publica
ON storage.objects FOR INSERT TO anon
WITH CHECK (
    bucket_id = 'documentos_estudiantes'
    AND (storage.foldername(name))[1] = 'solicitudes'
);

-- Mantiene el patrón actual del formulario público: INSERT únicamente en solicitudes.
ALTER TABLE public.solicitud_inscripcion ENABLE ROW LEVEL SECURITY;
REVOKE SELECT, UPDATE, DELETE ON public.solicitud_inscripcion FROM anon;
GRANT INSERT ON public.solicitud_inscripcion TO anon;
DROP POLICY IF EXISTS solicitud_inscripcion_publica_insertar ON public.solicitud_inscripcion;
CREATE POLICY solicitud_inscripcion_publica_insertar
ON public.solicitud_inscripcion FOR INSERT TO anon
WITH CHECK (
    estado = 'pendiente'
    AND acepta_datos IS TRUE
    AND consentimiento_datos IS TRUE
    AND EXISTS (
        SELECT 1 FROM public.oferta_curso o
        WHERE o.id = oferta_id AND o.estado = 'convocatoria'
    )
);

COMMENT ON COLUMN public.estudiante.unidad_ucn IS
    'Campo legado conservado; carrera tiene su propia columna desde 2026-11-11.';
