// 익명(가입 전) 계정의 첫 기록을 이미 있는 계정으로 옮기기 (2026-11-17 첫 실행 순서 변경, 할 일 5)
// 앱이 ⑥ 가입에서 '이미 있는 계정'으로 로그인하면: Authorization = 그 계정, body.anon_token = 로그인 직전 익명 세션 토큰.
// 두 토큰을 Auth 서버로 각각 확인(소유 확인) → claim_anon_data(service_role 전용)로 옮김 → 익명 계정 삭제
const WEB_ORIGINS = ["https://csw-app-web.vercel.app", "http://localhost:8081"];
const URL_ = Deno.env.get("SUPABASE_URL")!;
const ANON = Deno.env.get("SUPABASE_ANON_KEY") ?? "";
const SERVICE = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";

Deno.serve(async (req) => {
  const origin = req.headers.get("Origin") ?? "";
  const cors: Record<string, string> = WEB_ORIGINS.includes(origin)
    ? {
      "Access-Control-Allow-Origin": origin,
      "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      Vary: "Origin",
    }
    : {};
  const json = (body: unknown, status = 200) =>
    new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...cors } });
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
  if (req.method !== "POST") return json({ error: "method" }, 405);

  let anonToken = "";
  try {
    anonToken = String((await req.json()).anon_token ?? "");
  } catch {
    return json({ error: "bad_json" }, 400);
  }
  const target = await who(req.headers.get("Authorization") ?? "");
  const anon = anonToken ? await who(`Bearer ${anonToken}`) : null;
  if (!target || target.is_anonymous) return json({ error: "bad_target" }, 401);
  if (!anon) return json({ error: "anon_expired" }, 401);
  if (!anon.is_anonymous) return json({ error: "not_anonymous" }, 400);
  if (anon.id === target.id) return json({ moved: 0, target_new: false });

  const r = await fetch(`${URL_}/rest/v1/rpc/claim_anon_data`, {
    method: "POST",
    headers: { apikey: SERVICE, Authorization: `Bearer ${SERVICE}`, "Content-Type": "application/json" },
    body: JSON.stringify({ p_anon: anon.id, p_target: target.id }),
  });
  if (!r.ok) return json({ error: "claim_failed", detail: (await r.text()).slice(0, 200) }, 500);
  const out = await r.json();
  // 옮긴 뒤 익명 계정 삭제 (실패해도 7일 뒤 자동 삭제가 지움)
  await fetch(`${URL_}/auth/v1/admin/users/${anon.id}`, {
    method: "DELETE",
    headers: { apikey: SERVICE, Authorization: `Bearer ${SERVICE}` },
  }).catch(() => {});
  return json(out);
});

async function who(authorization: string): Promise<{ id: string; is_anonymous: boolean } | null> {
  if (!authorization.startsWith("Bearer ")) return null;
  const r = await fetch(`${URL_}/auth/v1/user`, { headers: { apikey: ANON, Authorization: authorization } });
  if (!r.ok) return null;
  const u = await r.json();
  return u?.id ? { id: u.id, is_anonymous: !!u.is_anonymous } : null;
}
