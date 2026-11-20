// 이메일 가입 화면 캡처 + 실제 메일 확인 (2026-11-20). capture_onboarding.mjs의 도구 부분을 복사함
// 사용: node scripts/capture_email.mjs <outdir> https://csw-app-web.vercel.app
// 시작하기 → 첫 기록 → ⑥ 가입 시트 → 이메일로 계속하기 → Resend 테스트 주소(delivered+…@resend.dev) → 코드 받기
// → Resend API로 받은 메일에서 코드 → 입력 → 방·선물. 같은 계정이 정식 계정이 됐는지 확인, 메일 본문도 캡처. 테스트 계정은 끝에 지움.
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

const RESEND = env('.env.local', 'RESEND_API_KEY').replace(/"/g, '');
async function resendMail(to, since) {
  for (let i = 0; i < 25; i++) {
    await sleep(3000);
    const l = await (await fetch('https://api.resend.com/emails?limit=20', { headers: { Authorization: 'Bearer ' + RESEND } })).json();
    const m = (l.data || []).find((x) => x.to.includes(to) && new Date(x.created_at.replace(' ', 'T').replace(/\+00$/, 'Z')) >= since - 5000);
    if (m) return (await fetch('https://api.resend.com/emails/' + m.id, { headers: { Authorization: 'Bearer ' + RESEND } })).json();
  }
  throw new Error('mail not arrived');
}

// 이메일 가입 화면 캡처 (2026-11-20): ⑥ 가입 시트 → 이메일로 계속하기 → 코드 받기 → 메일 → 코드 입력 → 방
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

  const a = await startToFirstWin('이불 갰다');
  await waitText('첫 기록, 잘 간직할게', 20000);
  await shot('e1_signup_sheet', '⑥ 가입 시트', 900);
  await tap('이메일로 계속하기');
  await waitText('가입 코드를 메일로 보내줄게', 15000);
  check('가입 시트에서 오면 "가입 코드" 문구', true);
  await shot('e2_email', '이메일 입력');
  const addr = `delivered+hlcap${Date.now()}@resend.dev`;
  await type('이메일', addr);
  await shot('e2b_email_typed', '이메일 입력 (입력 후)', 300);
  const t0 = Date.now();
  await tap('코드 받기');
  await waitText('메일함을 확인해줘', 20000);
  check('익명 → 연결 모드 메일 발송', true);
  await shot('e3_code', '코드 입력 화면');
  const m = await resendMail(addr, t0);
  const code = m.subject.match(/(\d{6})/)[1];
  check('메일 제목 = 가입 코드', m.subject.startsWith('Hamalog 가입 코드'), m.subject);
  writeFileSync(join(outDir, 'mail.html'), m.html);
  await type('인증 코드', code);
  await shot('e4_code_typed', '코드 입력 (6자리)', 300);
  await tap('확인');
  await waitText('선물이야! 씨앗 6개', 30000);
  await shot('e5_room', '가입 완료 → 방 · 선물 씨앗', 300);
  const s = await session();
  check('같은 계정이 정식 계정', s.user.id === a.user.id && s.user.is_anonymous === false && s.user.email === addr, s.user);
  // 메일 미리보기 (휴대폰 폭)
  await send('Page.navigate', { url: 'file://' + join(outDir, 'mail.html') });
  await sleep(1500);
  await shot('e6_mail', '받은 메일 (이메일 연결 코드)', 300);
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

