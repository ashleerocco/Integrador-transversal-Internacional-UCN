-- Banco asociado a un pago; los pagos existentes quedan con el valor NULL.
ALTER TABLE public.pago
    ADD COLUMN IF NOT EXISTS banco text;
