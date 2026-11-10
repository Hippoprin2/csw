import { Image } from 'expo-image';
import { Image as RNImage, Platform } from 'react-native';
import { useEffect, useMemo, useRef, useState } from 'react';
import { StyleSheet, Text, View, type LayoutChangeEvent } from 'react-native';
import { GestureDetector, usePanGesture, usePinchGesture, useSimultaneousGestures, useCompetingGestures, useTapGesture } from 'react-native-gesture-handler';
import Animated, { useAnimatedStyle, useSharedValue } from 'react-native-reanimated';

import { PET_CLIPS, PET_FPS, PET_YARD_ACTIONS, type ClipKey } from '@/data/petClips';
import { PET_NIGHT } from '@/data/petNight';
import { HIT_CELL, YARD_HIT } from '@/data/yardHit';
import { YARD, YARD_IMG } from '@/data/yard';
import type { Poly, Pt } from '@/data/yardTypes';
import { buildWalk, camBounds, cellPt, findPath, inPoly, lineY, nearestCell, walkable, zoneAt, type WalkMap } from '@/lib/yardGeo';
import type { Pager } from '@/ui/pager';

// 마당 화면 (export README '마당' 절, 참고 구현 design/yard_test/index.html)
// - 큰 캔버스(2160×3100)를 카드 너비 = 1080px 기준으로 줄여 창처럼 보여줌. 끌기 = 둘러보기, 두 손가락 = 줌(0.6~1, 유지), 탭 = 걸어가기
// - 그리는 순서: 타일 → 잠긴 구역 울타리 → ground → pond → (나무·sorted 소품·화단 꽃·단짝·땅 참새를 sort_y 순, 단짝은 sort_line 비교) → 물장구 물 → 나비
// - 밤: 그림마다 같은 그림을 night.overlay 색으로 칠해 그 투명도로 겹침(자기 픽셀에만 = source-atop). night_file 소품은 덮개 없이
// - 단짝: 대기 = garden_idle, 걷기 = 25° 걷기 3방향, 자리 동작 = character manifest yard_actions (in → loop 5~10초 → out / 한 번)
//   동작 클립엔 아이템 가림(홀드아웃)이 들어 있어서 동작 중엔 그 아이템 바로 위에 그림. 연못 물은 덮지 않음(클립이 물높이에서 잘림)
//   클립 전환: 새 클립 첫 프레임이 뜰 때까지 이전 클립을 아래에 남겨 둠(빈 화면 방지), 단계 타이머도 첫 프레임부터 잼

const P = YARD.walk.pet;
const [OR, OG, OB, OA] = YARD.night.overlay;
const TINT = `rgb(${OR},${OG},${OB})`;
const CAM = YARD.camera;
const SPEED = 0.9; // 걷는 속도 (땅 위 단위/초, 1단위 = 400px) — 대표 결정 2026-11-11 (character manifest walk.speed_px_s 360)
const DEPTH = 0.426; // 25° 카메라: 화면 세로 1px = 땅 위 1/0.426px (character manifest walk.depth_factor)
type Face = 'idle' | 'front' | 'side' | 'back';
const FACE_CLIP = { idle: 'garden_idle', front: 'walk_front', side: 'walk_side', back: 'walk_back' } as const;
const END_GRACE_MS = 100;
const LOAD_GIVE_UP_MS = 5000; // 첫 프레임이 이 안에 안 뜨면 뜬 셈 치고 진행 (단짝이 멈춰 있지 않게)
const ACT_ITEM: Record<string, string> = { duck_float: 'pond' }; // 오리 튜브 탭 = 연못 물장구
// 동작 중엔 클립 홀드아웃이 아이템을 가려 주므로 이 아이템들 바로 위에 그림 (화단 뒤에서 냄새 맡기 등)
const ACT_OVER: Record<string, (key: string) => boolean> = {
  sit_bench: (k) => k === 'bench', lie: (k) => k === 'hammock', sniff: (k) => k === 'flower_bed' || k.startsWith('bf'),
};
type Phase = { clip: ClipKey; ms: number; move?: { from: Pt; to: Pt; f0: number; f1: number } };
type Act = { id: string; action: string; stand: Pt; enter?: Pt; seq: Phase[]; i: number; reqAt: number; shownAt: number | null; fire: { i: number; frac: number }; then: null | (() => void) };
const clock = () => performance.now(); // 이벤트 처리용 (렌더 중 호출 아님)
const clipMs = (c: ClipKey) => PET_CLIPS[c].durationMs;

// 자리 동작 순서. 앉기·눕기·물장구 = in → loop(반복 횟수로 5~10초, 루프 끝 = out 시작 자세) → out
function buildSeq(action: string, eat?: ClipKey): { seq: Phase[]; fire: { i: number; frac: number } } {
  const A = PET_YARD_ACTIONS[action];
  if (A.parts.length === 1) return { seq: [{ clip: A.parts[0], ms: clipMs(A.parts[0]) }], fire: { i: 0, frac: action === 'show_fruit' ? 0.55 : 0 } };
  const [cin, cloop, cout] = A.parts, L = clipMs(cloop);
  const hold = L * Math.max(1, Math.ceil((5000 + Math.random() * 5000) / L));
  const seq: Phase[] = [{ clip: cin, ms: clipMs(cin) }];
  let fire = { i: 0, frac: 0 };
  if (eat) { seq.push({ clip: cloop, ms: L }, { clip: eat, ms: clipMs(eat) }); fire = { i: 2, frac: 0 }; }
  seq.push({ clip: cloop, ms: hold }, { clip: cout, ms: clipMs(cout) });
  if (action === 'splash' && A.enter) { // 첫 뜀: 4~15프레임에 연못 가장자리 → 물속, 나올 때 8~19프레임
    seq[0].move = { from: A.enter, to: A.stand, f0: 4, f1: 15 };
    seq[seq.length - 1].move = { from: A.stand, to: A.enter, f0: 8, f1: 19 };
  }
  return { seq, fire };
}

// 소품·나무 탭 판정: 그림의 투명한 여백은 빼고 (scripts/gen_yard_hit.py)
function hitSprite(key: string, e: { x: number; y: number; w: number; h: number }, x: number, y: number) {
  if (x < e.x || y < e.y || x >= e.x + e.w || y >= e.y + e.h) return false;
  const H = YARD_HIT[key];
  if (!H) return true;
  const c = Math.min(H.cols - 1, Math.floor(((x - e.x) / e.w) * H.cols)), r = Math.min(H.rows - 1, Math.floor(((y - e.y) / e.h) * H.rows));
  return H.bits[r * H.cols + c] === '1' || HIT_CELL <= 0;
}

const kept = { zoom: 1 }; // 줌 유지 (앱을 켜 둔 동안)
const keepZoom = (z: number) => { kept.zoom = z; };

type Guest = { k: 'perch' } | { k: 'ground'; x: number; y: number } | { k: 'fly'; cx: number; cy: number };
export type YardTap =
  | { kind: 'zone'; zone: number }
  | { kind: 'forest' }
  | { kind: 'fruit'; index: number }
  | { kind: 'item'; id: string };

export type YardSceneHandle = { walkTo: (interactId: string, then?: () => void, opts?: { eat?: ClipKey }) => void };

type Props = {
  zones: number[];          // 산 구역 (1은 항상)
  items: string[];          // 가진 마당 소품 id
  stage: number;            // 추억 나무 단계 1~4
  fruitsHidden: number[];   // 이번에 딴 열매
  night: boolean;
  guests: boolean;          // 이번 방문에 손님이 오는지 (30%)
  active: boolean;          // 지금 보이는 페이지일 때만 움직임
  onTap: (t: YardTap) => void;
  pager?: Pager;            // 왼쪽 끝을 넘겨 끌면 방 페이지가 손가락을 따라 옴
  bubble?: string | null;   // 단짝 말풍선 (밖에서 정함, 예: 먹이기)
  sceneRef?: React.RefObject<YardSceneHandle | null>;
};

function Sprite({ file, x, y, w, h, night, z, lit }: { file: string; x: number; y: number; w: number; h: number; night: boolean; z: number; lit?: boolean }) {
  const box = { position: 'absolute' as const, left: x, top: y, width: w, height: h, zIndex: z };
  return (
    <>
      <Image source={YARD_IMG[file]} style={box} contentFit="fill" loading="eager" />
      {night && !lit && <Image source={YARD_IMG[file]} style={[box, { opacity: OA }]} tintColor={TINT} contentFit="fill" loading="eager" />}
    </>
  );
}

type Static = { y: number; line?: Poly };

function spawnGuests(items: Set<string>, m: WalkMap): Guest[] {
  const kind = Math.random() < 0.5 ? 'sparrow' : 'butterfly';
  if (kind === 'sparrow') {
    if (items.has('bird_feeder') && Math.random() < 0.5) return [{ k: 'perch' }];
    for (let k = 0; k < 300; k++) {
      const x = 100 + Math.random() * 900, y = 600 + Math.random() * 1100;
      if (walkable(m, x, y)) return [{ k: 'ground', x, y }];
    }
    return [];
  }
  const b = YARD.items.find((e) => e.id === 'flower_bed')!;
  return [{ k: 'fly', cx: b.x + b.w * 0.6, cy: b.y - 40 }];
}

export function YardScene({ zones, items, stage, fruitsHidden, night, guests, active, onTap, pager, bubble, sceneRef }: Props) {
  const [size, setSize] = useState({ cw: 0, ch: 0 });
  const own = new Set([1, ...zones]);
  const ownItems = new Set(items);
  const zonesKey = [...own].sort().join(',');
  const itemsKey = [...ownItems].sort().join(',');

  // 걷기 지도 (구역·소품이 바뀔 때만)
  const walkRef = useRef<{ key: string; m: WalkMap } | null>(null);
  const getWalk = () => {
    const key = zonesKey + '|' + itemsKey;
    if (walkRef.current?.key !== key) walkRef.current = { key, m: buildWalk(own, ownItems) };
    return walkRef.current.m;
  };

  const [guestList, setGuestList] = useState<Guest[] | null>(null);
  // 단짝 클립 두 겹: cur(지금 원하는 것) 위, base(마지막으로 화면에 뜬 것) 아래 — cur 첫 프레임이 뜨면 base = cur
  type Layer = { clip: ClipKey; n: number };
  const [cur, setCur] = useState<Layer>({ clip: 'garden_idle', n: 0 });
  const [base, setBase] = useState<Layer>({ clip: 'garden_idle', n: 0 });
  const nRef = useRef(0);
  const curRef = useRef<Layer>(cur);
  const [petZ, setPetZ] = useState(() => moverZFrom(statics0(stage, items), YARD.walk.home[0], YARD.walk.home[1]));
  const guestRef = useRef<Guest[]>([]);
  useEffect(() => { guestRef.current = guestList ?? []; }, [guestList]);

  // 움직이는 값 (화면 = UI 스레드 shared value, 계산은 JS 루프)
  const camX = useSharedValue(0), camY = useSharedValue(0), scale = useSharedValue(1);
  const petX = useSharedValue(YARD.walk.home[0]), petY = useSharedValue(YARD.walk.home[1]), petDir = useSharedValue(1);
  const flyX = useSharedValue(0), flyY = useSharedValue(0), flyOpen = useSharedValue(0);

  const G = useRef({
    cam: { x: 0, y: 0 }, zoom: kept.zoom, s: 1, vw: 1080, vh: 1860, started: false,
    pet: { x: YARD.walk.home[0], y: YARD.walk.home[1], dir: 1, face: 'side' as Face, t: 0, state: 'idle' as 'idle' | 'walk' | 'act', path: [] as Pt[], act: null as null | Act, until: 0, walks: 0 },
    dragging: false, lastDrag: -1e9, glide: null as null | { t0: number; x: number; y: number }, glided: true,
    panStart: { x: 0, y: 0 }, pinchStart: 1, over: 0,
  });

  // 정렬 대상 (나무·sorted 소품·화단 꽃) → zIndex
  const tree = YARD.tree.find((t) => t.stage === stage) ?? YARD.tree[0];
  const sorted = YARD.items.filter((e) => e.layer === 'sorted' && ownItems.has(e.id));
  const flowers = ownItems.has('flower_bed') ? YARD.bed_flowers.filter((b) => b.flower === (b.spot === 1 ? 'sunflower' : 'tulip')) : [];
  const statics: (Static & { key: string })[] = [
    { key: 'tree', y: tree.sort_y },
    ...sorted.map((e) => ({ key: e.id, y: e.sort_y, line: e.sort_line })),
    ...flowers.map((b) => ({ key: `bf${b.spot}`, y: b.sort_y })),
  ].sort((a, b) => a.y - b.y);
  const zOf = (key: string) => 100 + statics.findIndex((s) => s.key === key) * 2;
  // 단짝·땅 참새: 앞에 서는 소품들 중 가장 뒤의 것 바로 다음
  const moverZ = (fx: number, fy: number) => {
    let after = -1;
    statics.forEach((o, i) => { if (o.line ? fy > lineY(o.line, fx) : fy > o.y) after = i; });
    return 101 + after * 2;
  };
  const staticsRef = useRef(statics);
  useEffect(() => { staticsRef.current = statics; });

  function view() {
    const g = G.current;
    g.s = (size.cw / 1080) * g.zoom; g.vw = size.cw / g.s; g.vh = size.ch / g.s;
  }
  function zoomFloor() {
    const [x0, y0, x1, y1] = camBounds(own);
    return Math.min(1, Math.max(CAM.zoom_min, 1080 / (x1 - x0), (size.ch * 1080) / size.cw / (y1 - y0)));
  }
  function clamp() {
    const g = G.current, [x0, y0, x1, y1] = camBounds(own);
    g.cam.x = x1 - x0 <= g.vw ? x0 + (x1 - x0 - g.vw) / 2 : Math.min(Math.max(g.cam.x, x0), x1 - g.vw);
    g.cam.y = y1 - y0 <= g.vh ? y0 : Math.min(Math.max(g.cam.y, y0), y1 - g.vh);
  }
  function push() {
    const g = G.current;
    camX.value = g.cam.x; camY.value = g.cam.y; scale.value = g.s;
  }
  function setZoom(z: number, ax?: number, ay?: number) {
    const g = G.current, oldW = g.vw, oldH = g.vh;
    g.zoom = Math.min(1, Math.max(zoomFloor(), z));
    keepZoom(g.zoom);
    view();
    if (ax !== undefined && ay !== undefined) {
      g.cam.x = ax - ((ax - g.cam.x) * g.vw) / oldW;
      g.cam.y = ay - ((ay - g.cam.y) * g.vh) / oldH;
    }
    clamp(); push();
  }
  const petCenter = (): Pt => [G.current.pet.x + P.feet_to_center[0], G.current.pet.y + P.feet_to_center[1]];

  function showClip(c: ClipKey) {
    if (curRef.current.clip === c && G.current.pet.state !== 'act') return; // 걷기·대기는 같은 클립이면 그대로 (동작 단계는 매번 처음부터)
    const l = { clip: c, n: ++nRef.current };
    curRef.current = l; setCur(l);
  }
  function onShown(l: Layer) {
    setBase(l);
    const a = G.current.pet.act;
    if (a && G.current.pet.state === 'act' && curRef.current.n === l.n && a.shownAt === null) a.shownAt = clock();
  }
  function startAct(a: Act) {
    const pet = G.current.pet;
    pet.state = 'act'; pet.act = a; a.i = 0; a.reqAt = clock(); a.shownAt = null;
    [pet.x, pet.y] = a.seq[0].move ? a.seq[0].move.from : a.stand;
    showClip(a.seq[0].clip);
  }
  function makeAct(id: string, eat?: ClipKey): Act | null {
    const v = YARD.walk.interact[id];
    if (!v) return null;
    const A = PET_YARD_ACTIONS[v.action];
    if (!A) return null;
    const { seq, fire } = buildSeq(v.action, eat);
    return { id, action: v.action, stand: A.stand, enter: A.enter, seq, i: 0, reqAt: 0, shownAt: null, fire, then: null };
  }
  // 걷기 시작. 자리 동작 중이면 지금 동작을 자연스럽게 마치고(루프는 한 바퀴 끝에서 out) 출발
  function goTo(pt: Pt, a?: Act | null, then?: () => void) {
    const g = G.current, pet = g.pet;
    // 다른 곳을 누르면 하던 동작은 바로 멈추고 출발 (대표 결정 2026-11-11). 물장구 중이면 연못 가장자리에서 나옴
    const prev = pet.act;
    if (prev && prev !== a) {
      if (pet.state === 'act') { [pet.x, pet.y] = prev.enter ?? prev.stand; pet.state = 'idle'; }
      // 못 끝낸 콜백: 열매 카드는 그래도 열어 줌(열매는 이미 땄음), 먹이기는 안 먹은 걸로 (바구니 그대로)
      if (prev.then && prev.action === 'show_fruit') prev.then();
      prev.then = null; pet.act = null;
    }
    const m = getWalk();
    const target = a ? (a.enter ?? a.stand) : pt;
    let path = findPath(m, [pet.x, pet.y], target);
    if (a && !a.enter) path = path.concat([a.stand]); // 자리가 소품 발치 안쪽일 수 있음: 마지막 한 걸음은 직접
    pet.path = path; pet.act = a ?? null;
    if (a) a.then = then ?? null;
    if (!path.length && a) { startAct(a); return; }
    pet.state = path.length ? 'walk' : 'idle';
    pet.until = clock() + 4000;
  }
  function walkToInteract(id: string, then?: () => void, opts?: { eat?: ClipKey }) {
    const pet = G.current.pet;
    // 이미 매트에 앉아 있으면 그 자리에서 먹기만 끼워 넣음 (루프 한 바퀴 끝에서)
    if (opts?.eat && pet.state === 'act' && pet.act?.id === id && pet.act.action === 'sit_eat') {
      const A = pet.act, ph = A.seq[A.i], last = A.seq.length - 1;
      if (A.i > 0 && A.i < last && ph.clip === A.seq[last - 1].clip) {
        const L = clipMs(ph.clip), el = A.shownAt === null ? 0 : clock() - A.shownAt;
        ph.ms = Math.max(L, Math.ceil((el + 1) / L) * L);
        const hold = L * Math.ceil(6000 / L);
        A.seq = [...A.seq.slice(0, A.i + 1), { clip: opts.eat, ms: clipMs(opts.eat) }, { clip: ph.clip, ms: hold }, A.seq[last]];
        A.fire = { i: A.i + 1, frac: 0 }; A.then = then ?? null;
        return;
      }
    }
    const a = makeAct(id, opts?.eat);
    if (a) goTo(a.stand, a, then);
  }
  useEffect(() => {
    if (sceneRef) sceneRef.current = { walkTo: walkToInteract };
  });

  function randomWalkable(): Pt {
    const g = G.current, m = getWalk();
    for (let k = 0; k < 400; k++) {
      const x = g.cam.x + Math.random() * g.vw, y = g.cam.y + Math.random() * g.vh;
      if (walkable(m, x, y)) return [x, y];
    }
    return cellPt(m, nearestCell(m, g.pet.x, g.pet.y));
  }

  // 카드 크기가 정해지면 시작: 단짝 중심으로
  useEffect(() => {
    if (!size.cw) return;
    const g = G.current;
    g.zoom = kept.zoom;
    view();
    g.zoom = Math.min(1, Math.max(zoomFloor(), g.zoom));
    view();
    if (!g.started) {
      g.started = true;
      const m = getWalk();
      if (!walkable(m, g.pet.x, g.pet.y)) [g.pet.x, g.pet.y] = cellPt(m, nearestCell(m, g.pet.x, g.pet.y));
      const [cx, cy] = petCenter();
      g.cam.x = cx - g.vw / 2; g.cam.y = cy - g.vh / 2;
    }
    clamp(); push();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 크기·구역이 바뀔 때만 다시 맞춤
  }, [size.cw, size.ch, zonesKey]);

  // 마당에 들어올 때마다: 하던 것 없이 화면 가운데에서 시작 (대표 결정 2026-11-11). 나갈 때: 그 자리에서 멈춤
  function dropAct() {
    const pet = G.current.pet, A = pet.act;
    if (A?.then && A.action === 'show_fruit') A.then(); // 딴 열매 카드는 열어 줌
    if (A) A.then = null;
    pet.act = null; pet.path = []; pet.state = 'idle';
  }
  useEffect(() => {
    if (!size.cw) return;
    const g = G.current, pet = g.pet;
    dropAct();
    showClip('garden_idle');
    if (!active) return;
    const m = getWalk(), [zx, zy, zw, zh] = YARD.walk.zones['1'].rect;
    g.cam.x = zx + zw / 2 - g.vw / 2; g.cam.y = zy + zh / 2 - g.vh / 2; clamp();
    let fx = g.cam.x + g.vw / 2 - P.feet_to_center[0], fy = g.cam.y + g.vh / 2 - P.feet_to_center[1];
    if (!walkable(m, fx, fy)) [fx, fy] = cellPt(m, nearestCell(m, fx, fy));
    pet.x = fx; pet.y = fy; pet.dir = 1; pet.until = performance.now() + 3000 + Math.random() * 2000;
    const [cx, cy] = petCenter();
    g.cam.x = cx - g.vw / 2; g.cam.y = cy - g.vh / 2; clamp();
    g.glide = null; g.glided = true; g.lastDrag = 0;
    push(); petX.value = pet.x; petY.value = pet.y; petDir.value = 1;
    setPetZ(moverZFrom(staticsRef.current, pet.x, pet.y));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 들어오고 나갈 때만
  }, [active, size.cw]);

  // 밤 클립 미리 받기 (낮 클립은 Pet.tsx가 앱 시작 때 받아 둠)
  useEffect(() => {
    if (!night || Platform.OS === 'web') return;
    try {
      const uris = Object.values(PET_NIGHT).map((r) => RNImage.resolveAssetSource(r)?.uri).filter((u): u is string => !!u);
      Image.prefetch(uris, 'disk').catch(() => {});
    } catch {}
  }, [night]);

  // 손님: 처음 한 번 정함 (30%)
  useEffect(() => {
    if (guestList !== null || !size.cw) return;
    setGuestList(guests ? spawnGuests(ownItems, getWalk()) : []);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [size.cw, guests]);

  // 산 소품이 걷기 막힘을 바꾸면 단짝이 막힌 곳에 서 있지 않게
  useEffect(() => {
    const g = G.current, m = getWalk();
    if (g.started && !walkable(m, g.pet.x, g.pet.y) && g.pet.state !== 'act') [g.pet.x, g.pet.y] = cellPt(m, nearestCell(m, g.pet.x, g.pet.y));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zonesKey, itemsKey]);

  // 프레임 루프: 단짝 걷기·자동 놀기, 카메라 따라가기, 나비
  useEffect(() => {
    if (!active || !size.cw) return;
    let raf = 0, last = performance.now(), lastZ = -1;
    const loop = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000); last = now;
      const g = G.current, pet = g.pet;
      // 단짝
      pet.t += dt;
      if (pet.state === 'walk') {
        const t = pet.path[0];
        if (!t) {
          if (pet.act) startAct(pet.act);
          else { pet.state = 'idle'; pet.until = now + 4000 + Math.random() * 4000; }
        } else {
          // 속도는 땅 위 거리로 (화면 세로 이동은 25° 카메라라 짧아 보임)
          const dx = t[0] - pet.x, dy = t[1] - pet.y, d = Math.hypot(dx, dy / DEPTH), step = SPEED * YARD.px_per_unit * dt;
          if (Math.abs(dx) > 2) pet.dir = dx > 0 ? 1 : -1;
          pet.face = Math.abs(dx) >= Math.abs(dy / DEPTH) ? 'side' : dy > 0 ? 'front' : 'back';
          if (d <= step) { pet.x = t[0]; pet.y = t[1]; pet.path.shift(); } else { pet.x += (dx / d) * step; pet.y += (dy / d) * step; }
        }
      } else if (pet.state === 'act' && pet.act) {
        const A = pet.act, ph = A.seq[A.i];
        if (A.shownAt === null && now - A.reqAt > LOAD_GIVE_UP_MS) A.shownAt = now;
        if (A.shownAt !== null) {
          const el = now - A.shownAt;
          if (ph.move) { // 물장구 뜀: 정해진 프레임 동안 발 위치를 옮김
            const f = (el / 1000) * PET_FPS, k = Math.min(1, Math.max(0, (f - ph.move.f0) / (ph.move.f1 - ph.move.f0)));
            pet.x = ph.move.from[0] + (ph.move.to[0] - ph.move.from[0]) * k; pet.y = ph.move.from[1] + (ph.move.to[1] - ph.move.from[1]) * k;
          }
          if (A.then && A.fire.i === A.i && el >= A.fire.frac * ph.ms) { const f = A.then; A.then = null; f(); }
          if (el >= ph.ms + END_GRACE_MS) {
            if (ph.move) [pet.x, pet.y] = ph.move.to;
            A.i++;
            if (A.i < A.seq.length) { A.reqAt = now; A.shownAt = null; showClip(A.seq[A.i].clip); }
            else {
              if (A.then) { const f = A.then; A.then = null; f(); } // 놓친 콜백(먹기 등)은 끝에서라도
              pet.act = null; pet.state = 'idle'; pet.until = now + 2000 + Math.random() * 3000;
            }
          }
        }
      } else if (pet.state === 'idle' && now > pet.until) {
        pet.walks++;
        const acts = Object.keys(YARD.walk.interact).filter((id) => id === 'pond' || id === 'tree' || ownItems.has(id));
        if (pet.walks % 3 === 0 && acts.length) walkToInteract(acts[Math.floor(Math.random() * acts.length)]);
        else goTo(randomWalkable());
      }
      // 클립: 걷기 = 25° 걷기(왼쪽 = 옆 클립 뒤집기), 서 있기 = 마당 대기, 동작 = 단계 클립(showClip이 바꿈)
      if (pet.state !== 'act') {
        const face: Face = pet.state === 'walk' && pet.path.length ? pet.face : 'idle';
        showClip(FACE_CLIP[face]);
        petDir.value = face === 'idle' || face === 'side' ? pet.dir : 1;
      } else petDir.value = 1;
      petX.value = pet.x; petY.value = pet.y;
      let z = moverZFrom(staticsRef.current, pet.x, pet.y);
      const over = pet.state === 'act' && pet.act ? ACT_OVER[pet.act.action] : undefined;
      if (over) staticsRef.current.forEach((o, i) => { if (over(o.key)) z = Math.max(z, 101 + i * 2); });
      if (z !== lastZ) { lastZ = z; setPetZ(z); }
      // 카메라
      if (!g.dragging) {
        const [pcx, pcy] = petCenter();
        if (now - g.lastDrag < CAM.return_wait_s * 1000) g.glided = false;
        else if (!g.glided) {
          if (!g.glide) g.glide = { t0: now, x: g.cam.x, y: g.cam.y };
          const t = Math.min(1, (now - g.glide.t0) / (CAM.return_s * 1000)), e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
          g.cam.x = pcx - g.vw / 2; g.cam.y = pcy - g.vh / 2; clamp();
          const tx = g.cam.x, ty = g.cam.y;
          g.cam.x = g.glide.x + (tx - g.glide.x) * e; g.cam.y = g.glide.y + (ty - g.glide.y) * e;
          if (t >= 1) { g.glide = null; g.glided = true; }
        } else {
          const f = 1 - Math.pow(1 - CAM.follow_lerp, dt * 60), dz = CAM.dead_zone;
          let ex = pcx - (g.cam.x + g.vw / 2), ey = pcy - (g.cam.y + g.vh / 2);
          ex = Math.abs(ex) > dz ? ex - Math.sign(ex) * dz : 0;
          ey = Math.abs(ey) > dz ? ey - Math.sign(ey) * dz : 0;
          g.cam.x += ex * f; g.cam.y += ey * f; clamp();
        }
        camX.value = g.cam.x; camY.value = g.cam.y;
      }
      // 나비
      const fly = guestRef.current.find((q) => q.k === 'fly');
      if (fly && fly.k === 'fly') {
        flyX.value = fly.cx + Math.sin(pet.t * 0.7) * 120; flyY.value = fly.cy + Math.sin(pet.t * 1.3) * 40;
        flyOpen.value = Math.floor(now / 160) % 2;
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 루프는 G(ref)를 읽음
  }, [active, size.cw, size.ch, itemsKey, zonesKey]);

  function handleTap(x: number, y: number) {
    // 열매
    const fi = tree.fruits.findIndex(([fx, fy], i) => !fruitsHidden.includes(i) && Math.hypot(fx - x, fy - y) < 60);
    if (fi >= 0) { onTap({ kind: 'fruit', index: fi }); return; }
    // 잠긴 구역·문
    const z = zoneAt(x, y);
    if (z && !own.has(z)) {
      onTap(YARD.walk.zones[String(z)].price === null ? { kind: 'forest' } : { kind: 'zone', zone: z });
      return;
    }
    for (const [zs, Z] of Object.entries(YARD.walk.zones)) {
      if (Z.gate && !own.has(Number(zs)) && Math.hypot(Z.gate[0] - x, Z.gate[1] - y) < 110) { onTap({ kind: 'zone', zone: Number(zs) }); return; }
    }
    // 소품·나무 (그림 위, 앞에 있는 것부터). 동작 있는 소품 = 가서 그 동작, 없는 소품 = 옆에 가서 섬
    const cands = [
      ...YARD.items.filter((e) => ownItems.has(e.id)).map((e) => ({ id: e.id, key: e.id, e, sy: e.layer === 'sorted' ? e.sort_y : -1 })),
      { id: 'tree', key: `tree${tree.stage}`, e: tree, sy: tree.sort_y },
    ].sort((a, b) => b.sy - a.sy);
    const it = cands.find((c) => hitSprite(c.key, c.e, x, y));
    if (it) {
      const id = ACT_ITEM[it.id] ?? it.id;
      if (id === 'picnic_mat') { onTap({ kind: 'item', id }); return; } // 먹이기 시트 (먹을 게 없으면 앉기)
      if (YARD.walk.interact[id]) { walkToInteract(id); return; }
      const fb = YARD.walk.item_blocked[it.id];
      if (fb) { // 소품 앞에 서면 가려서 옆으로 (단짝과 가까운 쪽)
        const pet = G.current.pet, m = getWalk();
        const L = fb.reduce((a, q) => (q[0] < a[0] ? q : a)), Rr = fb.reduce((a, q) => (q[0] > a[0] ? q : a));
        const opts = ([[L[0] - 90, L[1] + 10], [Rr[0] + 90, Rr[1] + 10]] as Pt[]).filter((q) => walkable(m, q[0], q[1]))
          .sort((a, b) => Math.hypot(a[0] - pet.x, a[1] - pet.y) - Math.hypot(b[0] - pet.x, b[1] - pet.y));
        const b = fb.reduce((a, q) => (q[1] > a[1] ? q : a));
        goTo(opts[0] ?? [b[0], b[1] + 40]); return;
      }
    }
    if (inPoly(x, y, YARD.walk.blocked.pond)) { walkToInteract('pond'); return; }
    goTo([x, y]);
  }

  // 손가락: 끌기 = 둘러보기, 두 손가락 = 줌, 탭 = 걸어가기/구역·열매
  // 설정 객체는 한 번만 만듦: 단짝이 걷는 동안 다시 그려질 때마다 설정이 바뀌면 끌던 손가락이 끊길 수 있어서 (2026-11-11 "이동 중 방으로 안 넘어감")
  const fx = useRef<{ clamp: typeof clamp; push: typeof push; setZoom: typeof setZoom; handleTap: typeof handleTap; pager?: Pager } | null>(null);
  useEffect(() => {
    fx.current = { clamp: () => clamp(), push: () => push(), setZoom: (z, ax, ay) => setZoom(z, ax, ay), handleTap: (x, y) => handleTap(x, y), pager };
  });
  const pan = usePanGesture(useMemo(() => ({
    minDistance: 8, maxPointers: 1, runOnJS: true,
    onActivate: () => { const g = G.current; g.dragging = true; g.glide = null; g.panStart = { ...g.cam }; g.over = 0; },
    onUpdate: (e: { translationX: number; translationY: number }) => {
      const g = G.current, f = fx.current;
      if (!f || !g.dragging) return; // 손 뗀 뒤 늦게 온 움직임은 무시
      g.cam.x = g.panStart.x - e.translationX / g.s; g.cam.y = g.panStart.y - e.translationY / g.s;
      const want = g.cam.x;
      f.clamp(); f.push();
      // 왼쪽 끝을 넘겨 끈 만큼 방 페이지가 따라 옴 (놓으면 1/4 넘었거나 빠르면 방으로)
      const over = Math.max(0, (g.cam.x - want) * g.s);
      if (f.pager && (over > 0 || g.over > 0)) { g.over = over; f.pager.drag(over); }
    },
    onDeactivate: (e: { velocityX: number; canceled: boolean }) => {
      const g = G.current;
      if (!g.dragging) return;
      g.dragging = false; g.lastDrag = performance.now(); g.glide = null;
      if (fx.current?.pager && g.over > 0) fx.current.pager.end(g.over, e.velocityX, e.canceled);
      g.over = 0;
    },
  }), []));
  const pinch = usePinchGesture(useMemo(() => ({
    runOnJS: true,
    onActivate: () => { const g = G.current; g.dragging = true; g.pinchStart = g.zoom; },
    onUpdate: (e: { scale: number; focalX: number; focalY: number }) => {
      const g = G.current;
      fx.current?.setZoom(g.pinchStart * e.scale, g.cam.x + e.focalX / g.s, g.cam.y + e.focalY / g.s);
    },
    onDeactivate: () => { const g = G.current; g.dragging = false; g.lastDrag = performance.now(); },
  }), []));
  const tap = useTapGesture(useMemo(() => ({
    maxDistance: 8, runOnJS: true,
    onDeactivate: (e: { canceled: boolean; x: number; y: number }) => {
      if (e.canceled) return;
      const g = G.current;
      fx.current?.handleTap(g.cam.x + e.x / g.s, g.cam.y + e.y / g.s);
    },
  }), []));
  const gesture = useCompetingGestures(useSimultaneousGestures(pan, pinch), tap);

  function onLayout(e: LayoutChangeEvent) {
    const { width, height } = e.nativeEvent.layout;
    if (Math.round(width) !== size.cw || Math.round(height) !== size.ch) setSize({ cw: Math.round(width), ch: Math.round(height) });
  }

  const [CW, CH] = YARD.canvas;
  const worldStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: scale.value * (CW / 2 - camX.value) - CW / 2 },
      { translateY: scale.value * (CH / 2 - camY.value) - CH / 2 },
      { scale: scale.value },
    ],
  }));
  const petStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: petX.value + P.feet_to_center[0] - P.w / 2 },
      { translateY: petY.value + P.feet_to_center[1] - P.h / 2 },
      { scaleX: petDir.value },
    ],
  }));
  const bubbleStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: petX.value - 300 }, { translateY: petY.value + P.feet_to_center[1] - P.h * 0.42 - 90 }],
  }));
  const FA = YARD.extras.butterfly_open.anchor ?? [0, 0];
  const flyA = useAnimatedStyle(() => ({
    opacity: flyOpen.value === 1 ? 1 : 0,
    transform: [{ translateX: flyX.value - FA[0] }, { translateY: flyY.value - FA[1] }],
  }));
  const flyB = useAnimatedStyle(() => ({
    opacity: flyOpen.value === 0 ? 1 : 0,
    transform: [{ translateX: flyX.value - FA[0] }, { translateY: flyY.value - FA[1] }],
  }));
  const speech = bubble ?? null;
  const petSrc = (c: ClipKey) => (night ? PET_NIGHT[c] ?? PET_CLIPS[c].source : PET_CLIPS[c].source);
  const layers = base.n === cur.n ? [cur] : [base, cur];
  const perch = guestList?.some((q) => q.k === 'perch') && ownItems.has('bird_feeder');
  const ground = guestList?.find((q) => q.k === 'ground');
  const hasFly = guestList?.some((q) => q.k === 'fly');
  const fly = YARD.extras.butterfly_open, flyClosed = YARD.extras.butterfly_closed;
  const sp = YARD.extras.sparrow_ground;

  return (
    <View style={[st.card, night && { backgroundColor: '#2a3466' }]} onLayout={onLayout} accessibilityLabel="마당">
      {size.cw > 0 && (
        <GestureDetector gesture={gesture}>
          <View style={StyleSheet.absoluteFill}>
            <Animated.View style={[{ position: 'absolute', left: 0, top: 0, width: CW, height: CH }, worldStyle]} pointerEvents="none">
              {YARD.tiles.map((t) => (
                <Image key={t.file} source={YARD_IMG[night ? t.night_file : t.file]} loading="eager" contentFit="fill"
                  style={{ position: 'absolute', left: t.x, top: t.y, width: t.w + 1, height: t.h + 1, zIndex: 0 }} />
              ))}
              {night && <View style={{ position: 'absolute', left: 0, top: 0, width: CW, height: CH, zIndex: 1, backgroundColor: `rgba(${OR},${OG},${OB},${OA})` }} />}
              {Object.entries(YARD.locks).filter(([z]) => !own.has(Number(z))).map(([z, l]) => <Sprite key={`l${z}`} {...l} night={night} z={2} />)}
              {YARD.items.filter((e) => e.layer === 'ground' && ownItems.has(e.id)).map((e) => <Sprite key={e.id} {...e} night={night} z={3} />)}
              {YARD.items.filter((e) => e.layer === 'pond' && ownItems.has(e.id)).map((e) => <Sprite key={e.id} {...e} night={night} z={4} />)}
              <Sprite {...tree} night={night} z={zOf('tree')} />
              {tree.fruits.map(([fx, fy], i) => fruitsHidden.includes(i) ? null : (
                <Sprite key={`f${i}`} file={YARD.fruit.file} x={fx - 40} y={fy - 40} w={80} h={80} night={night} z={zOf('tree')} />
              ))}
              {sorted.map((e) => (
                <View key={e.id} style={{ position: 'absolute', left: 0, top: 0, zIndex: zOf(e.id) }}>
                  {night && e.night_file ? <Sprite {...e} file={e.night_file} night={night} z={0} lit /> : <Sprite {...e} night={night} z={0} />}
                  {e.id === 'bird_feeder' && perch && <Sprite {...YARD.extras.sparrow_perch} night={night} z={0} />}
                </View>
              ))}
              {flowers.map((b) => <Sprite key={`bf${b.spot}`} {...b} night={night} z={zOf(`bf${b.spot}`)} />)}
              {ground && ground.k === 'ground' && (
                <Sprite file={sp.file} x={ground.x - (sp.anchor?.[0] ?? 0)} y={ground.y - (sp.anchor?.[1] ?? 0)} w={sp.w} h={sp.h} night={night} z={moverZ(ground.x, ground.y)} />
              )}
              <Animated.View style={[{ position: 'absolute', left: 0, top: 0, width: P.w, height: P.h, zIndex: petZ }, petStyle]}>
                {layers.map((l) => (
                  <Image key={`${l.clip}-${l.n}-${night ? 'n' : 'd'}`} source={petSrc(l.clip)} style={StyleSheet.absoluteFill} contentFit="contain"
                    loading="eager" autoplay cachePolicy="disk" onDisplay={() => onShown(l)} onLoad={() => onShown(l)} />
                ))}
              </Animated.View>
              {hasFly && (
                <>
                  <Animated.View style={[{ position: 'absolute', left: 0, top: 0, width: fly.w, height: fly.h, zIndex: 950 }, flyA]}>
                    <Sprite file={fly.file} x={0} y={0} w={fly.w} h={fly.h} night={night} z={0} />
                  </Animated.View>
                  <Animated.View style={[{ position: 'absolute', left: 0, top: 0, width: flyClosed.w, height: flyClosed.h, zIndex: 950 }, flyB]}>
                    <Sprite file={flyClosed.file} x={0} y={0} w={flyClosed.w} h={flyClosed.h} night={night} z={0} />
                  </Animated.View>
                </>
              )}
              {speech && (
                <Animated.View style={[st.bubbleWrap, bubbleStyle]}>
                  <Text style={st.bubble}>{speech}</Text>
                </Animated.View>
              )}
            </Animated.View>
          </View>
        </GestureDetector>
      )}
    </View>
  );
}

function statics0(stage: number, items: string[]): Static[] {
  const own = new Set(items);
  const tree = YARD.tree.find((t) => t.stage === stage) ?? YARD.tree[0];
  return [
    { y: tree.sort_y },
    ...YARD.items.filter((e) => e.layer === 'sorted' && own.has(e.id)).map((e) => ({ y: e.sort_y, line: e.sort_line })),
    ...(own.has('flower_bed') ? YARD.bed_flowers.filter((b) => b.flower === (b.spot === 1 ? 'sunflower' : 'tulip')).map((b) => ({ y: b.sort_y })) : []),
  ].sort((a, b) => a.y - b.y);
}

function moverZFrom(statics: Static[], fx: number, fy: number) {
  let after = -1;
  statics.forEach((o, i) => { if (o.line ? fy > lineY(o.line, fx) : fy > o.y) after = i; });
  return 101 + after * 2;
}

const st = StyleSheet.create({
  card: { flex: 1, marginHorizontal: 16, marginBottom: 12, borderRadius: 26, overflow: 'hidden', backgroundColor: '#cde8f5' },
  bubbleWrap: { position: 'absolute', left: 0, top: 0, width: 600, alignItems: 'center', zIndex: 1000 },
  bubble: { backgroundColor: 'rgba(255,255,255,0.95)', borderRadius: 32, paddingHorizontal: 24, paddingVertical: 10, fontSize: 40, fontWeight: '700', color: '#3a3530', overflow: 'hidden' },
});
