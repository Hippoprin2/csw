// 기록 분류(8종 + 버틴 하루) + 자해 표현 2차 판정 + 남을 해치는 표현 판정(L2, 저장 안 함). 키워드 결과를 보정하는 용도라 실패해도 앱은 키워드 결과로 동작한다.
// 본문만 보내고 사용자 식별자는 OpenAI로 보내지 않는다. 본문은 저장·로그하지 않는다.
const CATEGORIES = ["tidy", "move", "study", "work", "eat", "care", "people", "cheer", "endure"] as const;
const MODEL = Deno.env.get("CLASSIFY_MODEL") ?? "gpt-5.4-nano";

const INSTRUCTIONS = `너는 작은 성취 기록 앱의 분류기다. 사용자가 오늘 해낸 일 한 줄을 주면 JSON으로만 답한다.
category (하나만):
- tidy: 정리·청소·빨래·설거지·집안일
- move: 운동·산책·스트레칭 등 몸 움직이기
- study: 공부·독서·과제(학교 과제 제출 포함)·수업·강의·시험 준비 등 배우기
- work: 출근·회사 일·회의·보고서·메일·알바·마감·엑셀/문서 작업 등 일하기 ("정리"라도 업무 자료면 work)
- eat: 밥·요리·물 마시기 등 잘 먹기
- care: 씻기·잠·약·휴식·병원·명상 등 나 돌보기
- people: 연락·가족·친구·감사·선물 등 사람·마음
- cheer: 위에 안 맞는 그 밖의 모든 승리 (해낸 일)
- endure: 해낸 일이 아니라 힘든 마음·감정을 털어놓은 말 ("힘들다", "지쳤어", "우울해", "오늘 망했어", "아무것도 못 했어"). 해낸 일이 함께 있으면 감정보다 그 일의 분류가 먼저 ("힘들었지만 운동했다" → move, "힘들어서 일찍 잤다" → care, "우울했는데 설거지는 했다" → tidy)
self_harm: 글쓴이가 자해·자살 생각, 계획, 시도, 또는 "살기 싫다/사라지고 싶다" 같은 마음을 드러내면 true.
자살 수단·장소를 떠올리는 말(옥상·다리에 가고 싶다, 약을 모은다 등), 이미 한 자해(칼로 그었다, 상처 냈다), 약을 한꺼번에·많이 먹었다는 말, "나 없어도 된다/사라지고 싶다" 같은 말도 true.
"죽을 만큼 맛있었다", "피곤해 죽겠다", "웃겨 죽는 줄", "죽어라 공부했다", "배고파 죽을 뻔했다"처럼 해낸 일을 강조하는 과장 표현, "책에 밑줄 그었다/선을 그었다/줄을 그었다"처럼 몸이 아닌 것에 그은 말은 false. 애매하면 true.
self_harm은 글쓴이 자신을 해치는 경우만이다. 남(사람·동물)을 죽이고 싶다, 찌르고 싶다, 때리고 싶다는 말은 아무리 격해도 self_harm이 아니라 harm_others다.
harm_others: 글쓴이가 남(사람·동물)을 해치려는 마음·계획(\"죽여버리고 싶다\", \"패버릴 거다\", \"음료에 뭐 탈 거다\", \"다 쓸어버리고 싶다\"), 이미 한 폭력·학대(때렸다, 꼬집었다, 밀쳤다, 물건을 던졌다, 동물을 찼다/굶겼다), 괴롭힘·협박·스토킹·남의 물건 망가뜨리기·신상 퍼뜨리기를 쓰면 true.
\"죽여주는 김치찌개\", 게임·운동·경기(\"보스 잡았다\", \"샌드백 쳤다\", \"상대팀 박살냈다\"), 모기·벌레 잡기, 장난(베개 싸움), \"싸웠지만 사과했다\", \"화났지만 참았다\"는 false.
self_harm이 true거나 harm_others가 true면 category는 반드시 endure.`;

const schema = {
  type: "object",
  additionalProperties: false,
  properties: {
    category: { type: "string", enum: CATEGORIES },
    self_harm: { type: "boolean" },
    harm_others: { type: "boolean" },
  },
  required: ["category", "self_harm", "harm_others"],
};

// 웹 테스트판(csw-app-web.vercel.app·localhost)에서 부를 수 있게 CORS. 앱(네이티브)은 CORS와 무관. 로그인 토큰 검사는 그대로
const WEB_ORIGINS = ["https://csw-app-web.vercel.app", "http://localhost:8081"];
let cors: Record<string, string> = {};
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...cors } });

Deno.serve(async (req) => {
  const origin = req.headers.get("Origin") ?? "";
  cors = WEB_ORIGINS.includes(origin)
    ? {
      "Access-Control-Allow-Origin": origin,
      "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      Vary: "Origin",
    }
    : {};
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
  if (req.method !== "POST") return json({ error: "method" }, 405);
  let text = "";
  try {
    text = String((await req.json()).text ?? "").trim().slice(0, 100);
  } catch {
    return json({ error: "bad_json" }, 400);
  }
  if (!text) return json({ error: "empty" }, 400);

  const key = Deno.env.get("OPENAI_API_KEY");
  if (!key) return json({ error: "not_configured" }, 503);

  // 사용자당 하루 호출 한도 (AI 비용 악용 방지). 넘으면 429 → 앱은 기기 키워드 결과로 저장
  // 하루 기록 상한 50개 + 수정·재시도 여유
  const limit = Number(Deno.env.get("CLASSIFY_DAILY_LIMIT") ?? "80");
  const auth = req.headers.get("Authorization") ?? "";
  const anon = Deno.env.get("SUPABASE_ANON_KEY") ?? "";
  try {
    const u = await fetch(`${Deno.env.get("SUPABASE_URL")}/rest/v1/rpc/bump_classify_usage`, {
      method: "POST",
      headers: { apikey: anon, Authorization: auth, "Content-Type": "application/json" },
      body: "{}",
    });
    if (!u.ok) return json({ error: "usage_check_failed" }, 401);
    if (Number(await u.json()) > limit) return json({ error: "rate_limited" }, 429);
  } catch {
    return json({ error: "usage_check_failed" }, 503);
  }
  // 익명(가입 전) 계정 남발 막기: 같은 IP의 익명 계정 호출을 하루 한도로 (정식 계정은 bump_classify_ip가 0을 돌려줘 안 셈).
  // IP는 소금 친 SHA-256 해시로만 저장. 통신사 공유 IP를 감안해 넉넉히(첫 기록 1~2번이면 충분). 넘으면 429 → 앱은 키워드 분류
  const ip = (req.headers.get("cf-connecting-ip") ?? req.headers.get("x-real-ip") ??
    (req.headers.get("x-forwarded-for") ?? "").split(",")[0]).trim();
  if (ip) {
    const ipLimit = Number(Deno.env.get("CLASSIFY_ANON_IP_DAILY_LIMIT") ?? "40");
    const salt = Deno.env.get("CLASSIFY_IP_SALT") ?? Deno.env.get("SUPABASE_URL") ?? "";
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(salt + ip));
    const ipHash = Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
    try {
      const u = await fetch(`${Deno.env.get("SUPABASE_URL")}/rest/v1/rpc/bump_classify_ip`, {
        method: "POST",
        headers: { apikey: anon, Authorization: auth, "Content-Type": "application/json" },
        body: JSON.stringify({ p_ip_hash: ipHash }),
      });
      if (u.ok && Number(await u.json()) > ipLimit) return json({ error: "rate_limited" }, 429);
    } catch {
      // IP 한도 확인 실패는 막지 않음 (사용자당 한도는 위에서 이미 확인)
    }
  }

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 6000);
  try {
    const r = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      signal: ctrl.signal,
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        model: MODEL,
        instructions: INSTRUCTIONS,
        input: text,
        reasoning: { effort: "none" },
        max_output_tokens: 80,
        store: false,
        text: { format: { type: "json_schema", name: "win", strict: true, schema } },
      }),
    });
    if (!r.ok) return json({ error: "upstream", status: r.status }, 502);
    const data = await r.json();
    const out = data.output?.find((o: { type: string }) => o.type === "message")?.content?.[0]?.text;
    const parsed = JSON.parse(out);
    if (!CATEGORIES.includes(parsed.category)) throw new Error("bad category");
    const selfHarm = !!parsed.self_harm;
    const harmOthers = !selfHarm && !!parsed.harm_others; // 자해 안내가 우선
    // 판정은 응답으로만 돌려주고 어디에도 저장하지 않는다 (L2)
    return json({ category: selfHarm || harmOthers ? "endure" : parsed.category, self_harm: selfHarm, harm_others: harmOthers });
  } catch (e) {
    return json({ error: "failed", detail: String(e).slice(0, 80) }, 502);
  } finally {
    clearTimeout(timer);
  }
});
