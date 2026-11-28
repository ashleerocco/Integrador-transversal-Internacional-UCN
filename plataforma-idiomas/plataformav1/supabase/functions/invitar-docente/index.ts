// Edge Function "invitar-docente": envía el acceso a la plataforma a un docente.
//
// - Solo la puede usar la coordinación: se verifica con idiomas.es_coordinacion()
//   usando el JWT de quien llama (verify_jwt = true).
// - La service role key vive solo aquí (variable de entorno de Supabase), nunca en la app.
// - Docente nuevo  → auth.admin.inviteUserByEmail (el docente elige su contraseña).
// - Ya tiene cuenta → correo de recuperación (para reenviar el acceso / olvidó su contraseña).
// - No se generan contraseñas.
//
// Cuerpo: { "rut": "12345678-5" }
import { createClient } from "jsr:@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function responder(cuerpo: Record<string, unknown>, estado = 200) {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: { ...CORS, "Content-Type": "application/json" },
  });
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return responder({ error: "Método no permitido" }, 405);

  const url = Deno.env.get("SUPABASE_URL")!;
  const anon = Deno.env.get("SUPABASE_ANON_KEY")!;
  const servicio = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const authHeader = req.headers.get("Authorization") ?? "";

  // Cliente con la sesión de quien llama: RLS y es_coordinacion() se evalúan como ese usuario
  const usuario = createClient(url, anon, {
    global: { headers: { Authorization: authHeader } },
    db: { schema: "idiomas" },
    auth: { persistSession: false },
  });

  const { data: esCoord, error: errRol } = await usuario.rpc("es_coordinacion");
  if (errRol || esCoord !== true) {
    return responder({ error: "Solo la coordinación puede enviar accesos." }, 403);
  }

  let rut = "";
  try {
    rut = String((await req.json())?.rut ?? "").trim();
  } catch {
    return responder({ error: "Cuerpo inválido: se espera { rut }." }, 400);
  }
  if (!rut) return responder({ error: "Falta el RUT del docente." }, 400);

  const { data: docente, error: errDoc } = await usuario
    .from("docente").select("correo, activo, nombres").eq("rut", rut).maybeSingle();
  if (errDoc) return responder({ error: "No se pudo leer el docente." }, 500);
  if (!docente) return responder({ error: "Docente no encontrado." }, 404);
  if (!docente.activo) return responder({ error: "El docente está inactivo." }, 400);
  if (!docente.correo) return responder({ error: "El docente no tiene correo registrado." }, 400);

  const correo = String(docente.correo).toLowerCase();
  const admin = createClient(url, servicio, { auth: { persistSession: false, autoRefreshToken: false } });

  const { error: errInv } = await admin.auth.admin.inviteUserByEmail(correo, {
    data: { nombre: docente.nombres },
  });
  if (!errInv) return responder({ ok: true, modo: "invitacion", correo });

  // Ya existe una cuenta con ese correo: se reenvía el acceso como "recuperar contraseña"
  const yaExiste = errInv.status === 422 || /already|registered|exists/i.test(errInv.message ?? "");
  if (yaExiste) {
    const { error: errRec } = await admin.auth.resetPasswordForEmail(correo);
    if (!errRec) return responder({ ok: true, modo: "recuperacion", correo });
    return responder({ error: `No se pudo reenviar el acceso: ${errRec.message}` }, 502);
  }
  return responder({ error: `No se pudo enviar la invitación: ${errInv.message}` }, 502);
});
