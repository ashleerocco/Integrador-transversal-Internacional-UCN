-- Comprobantes de pago: la base guarda sólo la ruta del objeto privado.
ALTER TABLE public.pago
    ADD COLUMN IF NOT EXISTS comprobante_path text;

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'comprobantes_pago', 'comprobantes_pago', false, 5242880,
    ARRAY['application/pdf', 'image/jpeg', 'image/png']
)
ON CONFLICT (id) DO UPDATE SET
    public = false,
    file_size_limit = 5242880,
    allowed_mime_types = ARRAY['application/pdf', 'image/jpeg', 'image/png'];

ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS comprobantes_pago_coordinacion_lectura ON storage.objects;
CREATE POLICY comprobantes_pago_coordinacion_lectura
ON storage.objects FOR SELECT TO authenticated
USING (
    bucket_id = 'comprobantes_pago'
    AND EXISTS (
        SELECT 1 FROM public.perfil p
        WHERE p.id = auth.uid() AND p.rol = 'coordinadora'
    )
);

DROP POLICY IF EXISTS comprobantes_pago_coordinacion_escritura ON storage.objects;
CREATE POLICY comprobantes_pago_coordinacion_escritura
ON storage.objects FOR ALL TO authenticated
USING (
    bucket_id = 'comprobantes_pago'
    AND EXISTS (
        SELECT 1 FROM public.perfil p
        WHERE p.id = auth.uid() AND p.rol = 'coordinadora'
    )
)
WITH CHECK (
    bucket_id = 'comprobantes_pago'
    AND EXISTS (
        SELECT 1 FROM public.perfil p
        WHERE p.id = auth.uid() AND p.rol = 'coordinadora'
    )
);
