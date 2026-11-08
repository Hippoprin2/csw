// 기록 분류(7종) + 자해 표현 2차 판정. 키워드 결과를 보정하는 용도라 실패해도 앱은 키워드 결과로 동작한다.
// 본문만 보내고 사용자 식별자는 OpenAI로 보내지 않는다. 본문은 저장·로그하지 않는다.
const CATEGORIES = ["tidy", "move", "study", "eat", "care", "people", "cheer"] as const;
const MODEL = Deno.env.get("CLASSIFY_MODEL") ?? "gpt-5.4-nano";

const INSTRUCTIONS = `너는 작은 성취 기록 앱의 분류기다. 사용자가 오늘 해낸 일 한 줄을 주면 JSON으로만 답한다.
category (하나만):
- tidy: 정리·청소·빨래·설거지·집안일
- move: 운동·산책·스트레칭 등 몸 움직이기
- study: 공부·독서·업무·과제·일
- eat: 밥·요리·물 마시기 등 잘 먹기
- care: 씻기·잠·약·휴식·병원·명상 등 나 돌보기
- people: 연락·가족·친구·감사·선물 등 사람·마음
- cheer: 위에 안 맞는 그 밖의 모든 승리
self_harm: 글쓴이가 자해·자살 생각, 계획, 시도, 또는 "살기 싫다/사라지고 싶다" 같은 마음을 드러내면 true.
자살 수단·장소를 떠올리는 말(옥상·다리에 가고 싶다, 약을 모은다 등), 이미 한 자해(칼로 그었다, 상처 냈다), 약을 한꺼번에·많이 먹었다는 말, "나 없어도 된다/사라지고 싶다" 같은 말도 true.
"죽을 만큼 맛있었다", "피곤해 죽겠다", "웃겨 죽는 줄" 같은 과장 표현은 false. 애매하면 true.`;

const schema = {
  type: "object",
  additionalProperties: false,
  properties: {
    category: { type: "string", enum: CATEGORIES },
    self_harm: { type: "boolean" },
  },
  required: ["category", "self_harm"],
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

Deno.serve(async (req) => {
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
        max_output_tokens: 60,
        store: false,
        text: { format: { type: "json_schema", name: "win", strict: true, schema } },
      }),
    });
    if (!r.ok) return json({ error: "upstream", status: r.status }, 502);
    const data = await r.json();
    const out = data.output?.find((o: { type: string }) => o.type === "message")?.content?.[0]?.text;
    const parsed = JSON.parse(out);
    if (!CATEGORIES.includes(parsed.category)) throw new Error("bad category");
    return json({ category: parsed.category, self_harm: !!parsed.self_harm });
  } catch (e) {
    return json({ error: "failed", detail: String(e).slice(0, 80) }, 502);
  } finally {
    clearTimeout(timer);
  }
});
