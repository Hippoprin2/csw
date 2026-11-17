// 첫 실행 흐름 상태별 스크린샷 + 확인 (2026-11-17 첫 실행 순서 변경: 가입을 첫 기록 축하 뒤로)
// 사용: node scripts/capture_onboarding.mjs <outdir> [app url=http://localhost:8081]   (mobile에서 npx expo start --web --port 8081)
// ① 인사 → ②③ → ④ 첫 기록 → ⑤ 축하 → ⑥ 가입 시트 → (앱 닫았다 다시 열기 → ⑥) → 가입(연결) → ⑦ 방·선물 → ⑧ 알림 시트
// 그리고 새 익명으로 첫 기록 → 이미 있는 계정으로 로그인 → 첫 기록이 그 계정으로 옮겨짐(바로 방, 선물 없음)
// 웹에선 실제 카카오·이메일 가입을 못 하므로 '연결'은 관리 API로 익명 계정에 이메일을 붙이고(서버 트리거는 실제와 같음)
// 앱이 웹 OAuth 연결에서 돌아올 때와 같은 상태(csw.linkUid + 새 세션)로 다시 엶. 만든 테스트 계정은 끝에 지움.
// 시스템 Chrome 헤드리스 + CDP (외부 패키지 없음, Node 22 WebSocket). 390×844 @2x
import { spawn } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const env = (f, k) => readFileSync(join(ROOT, f), 'utf8').match(new RegExp(`^\\s*${k}\\s*=\\s*(\\S+)`, 'm'))[1];
const URL_ = env('.env.local', 'SUPABASE_URL').replace(/\/$/, '');
const SERVICE = env('.env.local', 'SUPABASE_SERVICE_ROLE_KEY');
const PUB = env('mobile/.env.local', 'EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY');
const REF = URL_.split('//')[1].split('.')[0];
const TOKEN_KEY = `sb-${REF}-auth-token`;

const [outDir, APP = 'http://localhost:8081'] = process.argv.slice(2);
mkdirSync(outDir, { recursive: true });
const W = 390, H = 844, PORT = 9334;
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const made = new Set();
const checks = [];
const check = (name, ok, extra) => { checks.push({ name, ok: !!ok }); console.log((ok ? 'PASS ' : 'FAIL ') + name + (ok || extra === undefined ? '' : `  [${JSON.stringify(extra)}]`)); };

async function sb(method, path, body, token = PUB, key = PUB) {
  const r = await fetch(URL_ + path, { method, headers: { apikey: key, Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined });
  const t = await r.text();
  let j = null; try { j = t ? JSON.parse(t) : null; } catch { j = t; }
  return [r.status, j];
}
const admin = (m, p, b) => sb(m, p, b, SERVICE, SERVICE);

async function memberSession() { // 이미 있는 계정 (온보딩 끝, 기록 1개)
  const email = `csw-obcap-${Date.now()}@example.com`;
  await admin('POST', '/auth/v1/admin/users', { email, email_confirm: true });
  const [, link] = await admin('POST', '/auth/v1/admin/generate_link', { type: 'magiclink', email });
  const otp = link.email_otp ?? link.properties?.email_otp;
  const [, s] = await sb('POST', '/auth/v1/verify', { type: 'email', email, token: otp });
  made.add(s.user.id);
  await sb('PATCH', `/rest/v1/profiles?id=eq.${s.user.id}`, { pet_name: '두부' }, s.access_token);
  await sb('POST', '/rest/v1/rpc/give_consent', { p_version: '2026-11-18', p_onboard: true }, s.access_token);
  await sb('POST', '/rest/v1/rpc/record_win', { p_text: '예전에 쓴 기록', p_category: 'cheer' }, s.access_token);
  return s;
}

const prof = mkdtempSync(join(tmpdir(), 'csw-obcap-'));
const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${prof}`,
  '--no-first-run', '--hide-scrollbars', `--window-size=${W},${H}`, 'about:blank'], { stdio: 'ignore' });

let ws, seq = 0;
const pending = new Map();
function send(method, params = {}) {
  const id = ++seq;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((res, rej) => pending.set(id, { res, rej, method }));
}
async function ev(expr) {
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + ' ' + (r.exceptionDetails.exception?.description ?? ''));
  return r.result.value;
}
const log = [];
async function shot(name, title, wait = 600) {
  await sleep(wait);
  const { data } = await send('Page.captureScreenshot', { format: 'png' });
  writeFileSync(join(outDir, name + '.png'), Buffer.from(data, 'base64'));
  log.push({ file: name + '.png', title });
  console.log('shot', name);
}
const FIND = `(q) => {
  const vis = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth; };
  let best = null, area = 1e12;
  for (const e of document.querySelectorAll('body *')) {
    const t = (e.getAttribute('aria-label') === q || e.getAttribute('placeholder') === q || (e.innerText || '').trim() === q);
    if (!t || !vis(e)) continue;
    const r = e.getBoundingClientRect(); const a = r.width * r.height;
    if (a < area) { area = a; best = e; }
  }
  if (!best) return null;
  const r = best.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
}`;
const find = (q) => ev(`(${FIND})(${JSON.stringify(q)})`);
const hasText = (q) => ev(`document.body.innerText.includes(${JSON.stringify(q)})`);
async function waitFor(q, ms = 20000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) { const p = await find(q); if (p) return p; await sleep(250); }
  throw new Error('not found: ' + q);
}
async function waitText(q, ms = 20000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) { if (await hasText(q)) return true; await sleep(250); }
  throw new Error('text not found: ' + q);
}
async function tap(q, ms) {
  const p = await waitFor(q, ms);
  for (const type of ['mouseMoved', 'mousePressed', 'mouseReleased'])
    await send('Input.dispatchMouseEvent', { type, x: p.x, y: p.y, button: 'left', clickCount: 1 });
  await sleep(500);
}
async function type(q, text) { await tap(q); await send('Input.insertText', { text }); await sleep(300); }
async function go(path) { await send('Page.navigate', { url: APP + path }); await sleep(2500); }
const session = async () => JSON.parse(await ev(`localStorage.getItem('${TOKEN_KEY}')`));

async function startToFirstWin(text) {
  await go('/');
  await waitFor('시작하기', 30000);
  await tap('시작하기');
  await waitFor('이 이름으로 할래', 30000);
  await tap('이 이름으로 할래');
  await waitFor('모두 동의');
  await tap('모두 동의');
  await tap('시작하기');
  await waitText('오늘 해낸 거 하나만 알려줘', 30000);
  const s = await session();
  made.add(s.user.id);
  await type('오늘 해낸 일', text);
  await tap('기록');
  return s;
}

async function main() {
  let target;
  for (let i = 0; i < 50 && !target; i++) {
    try { target = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find((t) => t.type === 'page'); } catch { await sleep(200); }
  }
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener('open', r));
  ws.addEventListener('message', (m) => { const d = JSON.parse(m.data); const p = pending.get(d.id); if (p) { pending.delete(d.id); d.error ? p.rej(new Error(p.method + ' ' + d.error.message)) : p.res(d.result); } });
  await send('Page.enable'); await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 2, mobile: false });

  // ① 인사
  await go('/');
  await waitFor('시작하기', 30000);
  check('① 로그인 버튼 없음', !(await find('이메일로 계속하기')) && !!(await find('이미 계정이 있어요')));
  await shot('o1_welcome', '① 인사 (시작하기 / 이미 계정이 있어요)');
  await tap('시작하기');
  await waitFor('이 이름으로 할래', 30000);
  const a0 = await session();
  made.add(a0.user.id);
  check('① 시작하기 = 익명 계정', a0.user.is_anonymous === true, a0.user);
  await shot('o2_name', '② 이름');
  await tap('이 이름으로 할래');
  await waitFor('모두 동의');
  await tap('모두 동의');
  await shot('o3_consent', '③ 동의');
  await tap('시작하기');

  // ④ 첫 기록
  await waitText('오늘 해낸 거 하나만 알려줘', 30000);
  check('④ 탭 바·씨앗 칩·공간 전환 없음', !(await find('유리병')) && !(await find('텃밭')) && !(await find('방 보기')));
  await shot('o4_first_win', '④ 첫 기록 (예시 칩)', 2500);
  await type('오늘 해낸 일', '이불 갰다');
  await tap('기록');
  // ⑤ 축하
  await waitText('씨앗', 15000);
  await shot('o5_celebrate', '⑤ 축하 + 씨앗', 300);
  // ⑥ 가입 시트
  await waitText('첫 기록, 잘 간직할게', 15000);
  check('⑥ 무료 날짜·가격 안내', await hasText('까지 무료') && await hasText('월 3,000원 또는 연 24,000원'));
  check('⑥ "나중에" 없음', !(await hasText('나중에')));
  await shot('o6_signup', '⑥ 가입 시트 (필수)', 900);
  const [, ws1] = await sb('GET', '/rest/v1/wins?select=text,category', null, a0.access_token);
  check('익명 계정에 첫 기록 저장', ws1?.length === 1 && ws1[0].text === '이불 갰다', ws1);

  // ⑥에서 앱 닫았다 다시 열기
  await go('/');
  await waitText('첫 기록, 잘 간직할게', 30000);
  await shot('o6b_reopen', '⑥에서 앱 닫았다 다시 열기 → 다시 ⑥ (첫 기록 유지)', 1200);
  check('다시 열면 ⑥', true);

  // 가입(연결) → ⑦ 방·선물 → ⑧ 알림 시트
  const s0 = await session();
  await admin('PUT', `/auth/v1/admin/users/${s0.user.id}`, { email: `csw-oblink-${Date.now()}@example.com`, email_confirm: true });
  const [st1, s1] = await sb('POST', '/auth/v1/token?grant_type=refresh_token', { refresh_token: s0.refresh_token });
  check('연결 뒤 정식 계정', st1 === 200 && s1.user.is_anonymous === false, [st1, s1?.user?.is_anonymous]);
  await ev(`localStorage.setItem('${TOKEN_KEY}', ${JSON.stringify(JSON.stringify({ ...s1, expires_at: Math.floor(Date.now() / 1000) + s1.expires_in }))}); localStorage.setItem('csw.linkUid', ${JSON.stringify(s0.user.id)}); true`);
  await go('/');
  await waitText('선물이야! 씨앗 6개', 30000);
  await shot('o7_room_gift', '⑦ 방 도착 · 선물 씨앗 6개 말풍선', 300);
  await waitText('내일 이 시간쯤 한 번만 물어봐도 될까?', 10000);
  check('⑧ 알림 문구에 무료 끝 안내', await hasText('무료 이용이 끝나기 이틀 전에도 날짜를 알려줄게'));
  await shot('o8_notif', '⑧ 알림 시트 1장', 900);
  const [, p1] = await admin('GET', `/rest/v1/profiles?id=eq.${s0.user.id}&select=trial_ends_at,onboarded_at`);
  // 가입 + 14일인 날의 끝(다음 0시 KST) — 2026-11-18
  const kst = new Date(Date.now() + 9 * 3600000); kst.setUTCHours(0, 0, 0, 0);
  const want = kst.getTime() + 15 * 86400000 - 9 * 3600000;
  check('가입 때 무료 종료일 = 14일째 24시(KST)', new Date(p1[0].trial_ends_at).getTime() === want, p1);
  await tap('괜찮아');

  // 기존 계정 충돌: 새 익명으로 첫 기록 → 이미 있는 계정으로 로그인 → 첫 기록 옮김
  await ev('localStorage.clear(); true');
  const a2 = await startToFirstWin('물 한 잔 마셨다');
  await waitText('첫 기록, 잘 간직할게', 20000);
  const m = await memberSession();
  // 앱이 ⑥에서 '이미 있는 계정'을 만났을 때와 같은 상태: 옮길 익명 토큰(csw.pendingClaim) + 그 계정 세션
  await ev(`localStorage.setItem('csw.pendingClaim', ${JSON.stringify(a2.access_token)}); localStorage.setItem('${TOKEN_KEY}', ${JSON.stringify(JSON.stringify({ ...m, expires_at: Math.floor(Date.now() / 1000) + m.expires_in }))}); true`);
  await go('/');
  await waitText('오늘의 쪽지 2', 30000);
  await shot('o9_claimed', '기존 계정으로 로그인 → 첫 기록 옮겨짐 (바로 방)', 1500);
  check('기존 계정: 선물 말풍선 없음', !(await hasText('선물이야')));
  const [, mw] = await sb('GET', '/rest/v1/wins?select=text&order=created_at', null, m.access_token);
  check('기존 계정에 기록 2개 (옮긴 첫 기록 포함)', mw?.map((w) => w.text).sort().join('|') === ['예전에 쓴 기록', '물 한 잔 마셨다'].sort().join('|'), mw);
  const [sa] = await admin('GET', `/auth/v1/admin/users/${a2.user.id}`);
  check('옮긴 뒤 익명 계정 삭제', sa === 404, sa);
  const [, mp] = await admin('GET', `/rest/v1/profiles?id=eq.${m.user.id}&select=pet_name`);
  check('기존 계정 이름 그대로', mp[0].pet_name === '두부', mp);

  // '이미 계정이 있어요' 화면
  await ev('localStorage.clear(); true');
  await go('/');
  await tap('이미 계정이 있어요', 30000);
  await waitText('다시 만나서 반가워');
  await shot('o10_login', "'이미 계정이 있어요' 화면", 800);

  writeFileSync(join(outDir, 'index.json'), JSON.stringify(log, null, 1));
}

main().then(() => 0, (e) => { console.error('FAIL', e.message); return 1; }).then(async (code) => {
  if (code) try { await shot('zz_last_state', '실패 시점'); } catch {}
  for (const id of made) await admin('DELETE', `/auth/v1/admin/users/${id}`);
  let left = 0;
  for (const id of made) if ((await admin('GET', `/auth/v1/admin/users/${id}`))[0] === 200) left++;
  console.log(`테스트 계정 ${made.size}개 정리, 남은 것 ${left}개`);
  const fails = checks.filter((c) => !c.ok).length;
  console.log(code || fails ? `${fails} FAIL${code ? ' (중단)' : ''}` : `ALL PASS (${checks.length})`);
  chrome.kill(); await sleep(300); rmSync(prof, { recursive: true, force: true }); process.exit(code || fails ? 1 : 0);
});
