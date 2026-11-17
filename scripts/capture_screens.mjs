// capture_screens.py가 부름: node capture_screens.mjs <session.json> <supabase ref> <outdir> <app url>
// 시스템 Chrome 헤드리스 + CDP(외부 패키지 없음, Node 22 WebSocket). 390×844 @2x
import { spawn } from 'node:child_process';
import { readFileSync, writeFileSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const [sessPath, ref, outDir, APP] = process.argv.slice(2);
const session = readFileSync(sessPath, 'utf8');
const W = 390, H = 844, PORT = 9333;
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const prof = mkdtempSync(join(tmpdir(), 'csw-cap-'));
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
async function shot(name, title) {
  await sleep(600);
  const { data } = await send('Page.captureScreenshot', { format: 'png' });
  writeFileSync(join(outDir, name + '.png'), Buffer.from(data, 'base64'));
  log.push({ file: name + '.png', title });
  console.log('shot', name);
}
// 글자(innerText 정확히) 또는 aria-label/placeholder로 화면에 보이는 가장 작은 요소 찾기
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
async function find(q) { return ev(`(${FIND})(${JSON.stringify(q)})`); }
async function waitFor(q, ms = 15000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) { const p = await find(q); if (p) return p; await sleep(300); }
  throw new Error('not found: ' + q);
}
async function tap(q, ms) {
  const p = await waitFor(q, ms);
  for (const type of ['mouseMoved', 'mousePressed', 'mouseReleased'])
    await send('Input.dispatchMouseEvent', { type, x: p.x, y: p.y, button: 'left', clickCount: 1 });
  await sleep(500);
}
async function type(q, text) { await tap(q); await send('Input.insertText', { text }); await sleep(300); }
async function go(path, wait) { await send('Page.navigate', { url: APP + path }); if (wait) await waitFor(wait, 30000); await sleep(2500); }
async function tryTap(q) { if (await find(q)) await tap(q); }
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

  // 1) 로그인 전 — ① 인사(시작하기 / 이미 계정이 있어요). 2026-11-17 첫 실행 순서 변경: 로그인 버튼은 '이미 계정이 있어요'·⑥ 가입 시트로
  //    (시작하기 → 익명 첫 기록 → 가입 흐름은 scripts/capture_onboarding.mjs)
  await go('/', '이미 계정이 있어요');
  await shot('01_auth', '① 인사');
  await tap('이미 계정이 있어요');
  await sleep(800);
  await shot('02_auth_email', '이미 계정이 있어요 (로그인)');

  // 2) 세션 넣고 온보딩 (정식 계정, 온보딩 전 = '이미 계정이 있어요'로 처음 만든 계정)
  await ev(`localStorage.setItem('sb-${ref}-auth-token', ${JSON.stringify(session)}); true`);
  await go('/', '내 이름을 지어줄래?');
  await shot('03_onboarding_name', '온보딩 · 단짝 이름 짓기');
  await tap('이 이름으로 할래');
  await waitFor('시작하기');
  await shot('04_onboarding_notice', '온보딩 · 시작 전 동의');
  await tap('모두 동의');
  await tap('시작하기');

  // 3) 방 — 가입 직후 도착: 선물 말풍선 → 2~3초 뒤 알림 시트 1장 (D5, 첫 기록 직후에서 옮김)
  await waitFor('오늘 해낸 일', 30000);
  await sleep(4000);
  if (await find('괜찮아')) { await shot('06b_room_notif_ask', '방 · 가입 직후 알림 물어보기'); await tap('괜찮아'); }
  await shot('05_room', '방 (홈)');
  await type('오늘 해낸 일', '30분 산책했다');
  await tap('기록');
  await sleep(1800);
  await shot('06_room_celebrate', '방 · 기록 직후 축하');
  await sleep(6000);
  await shot('07_room_after', '방 · 기록 후 목록');

  // 4) 텃밭·마당
  await tap('텃밭'); await sleep(2500); await shot('08_garden', '텃밭');
  await go('/', '오늘 해낸 일'); await tap('마당'); await sleep(3000); await shot('09_yard_locked', '마당 · 잠김 (기록한 날 7일 전)');
  // 마당 열기: python이 테스트 계정 profiles.yard_opened_at을 넣어 줌
  const ok = new Promise((r) => process.stdin.once('data', r));
  console.log('OPEN_YARD'); await ok;
  await go('/', '오늘 해낸 일'); await tap('마당'); await sleep(5000); await shot('09_yard', '마당 · 열림');

  // 5) 탭들
  await go('/jar', '기록 찾기'); await shot('10_jar', '유리병');
  await tap('기록 찾기'); await sleep(1000); await shot('11_jar_search', '유리병 · 기록 찾기');
  await type('찾을 말', '산책'); await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r' }); await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 }); await sleep(2000); await shot('12_jar_search_result', '유리병 · 찾기 결과');
  await go('/jar/1'); await shot('13_jar_detail', '유리병 · 병 하나 보기');
  await go('/shop'); await shot('14_shop', '꾸미기 (상점)');
  await go('/settings'); await shot('15_settings', '설정');
  await go('/help'); await shot('16_help', '도움받을 수 있는 곳');

  writeFileSync(join(outDir, 'index.json'), JSON.stringify(log, null, 1));
}

main().then(() => 0, (e) => { console.error('FAIL', e.message); return 1; }).then(async (code) => {
  if (code) try { await shot('zz_last_state', '실패 시점'); } catch {}
  chrome.kill(); await sleep(300); rmSync(prof, { recursive: true, force: true }); process.exit(code);
});
