import { Image } from 'expo-image';
import { useEffect, useRef, useState } from 'react';
import { StyleSheet, Text, View, type LayoutChangeEvent } from 'react-native';
import { GestureDetector, usePanGesture, usePinchGesture, useSimultaneousGestures, useCompetingGestures, useTapGesture } from 'react-native-gesture-handler';
import Animated, { useAnimatedStyle, useSharedValue } from 'react-native-reanimated';

import { PET_CLIPS } from '@/data/petClips';
import { YARD, YARD_IMG } from '@/data/yard';
import type { Poly, Pt } from '@/data/yardTypes';
import { buildWalk, camBounds, cellPt, findPath, lineY, nearestCell, walkable, zoneAt, type WalkMap } from '@/lib/yardGeo';

// 마당 화면 (export README '마당' 절, 참고 구현 design/yard_test/index.html)
// - 큰 캔버스(2160×3100)를 카드 너비 = 1080px 기준으로 줄여 창처럼 보여줌. 끌기 = 둘러보기, 두 손가락 = 줌(0.6~1, 유지), 탭 = 걸어가기
// - 그리는 순서: 타일 → 잠긴 구역 울타리 → ground → pond → (나무·sorted 소품·화단 꽃·단짝·땅 참새를 sort_y 순, 단짝은 sort_line 비교) → 물장구 물 → 나비
// - 밤: 그림마다 같은 그림을 night.overlay 색으로 칠해 그 투명도로 겹침(자기 픽셀에만 = source-atop). night_file 소품은 덮개 없이
// - 단짝 동작 클립이 오기 전: 마당 대기 클립 + 통통 튀기(걷기·대기 모두)

const P = YARD.walk.pet;
const [OR, OG, OB, OA] = YARD.night.overlay;
const TINT = `rgb(${OR},${OG},${OB})`;
const CAM = YARD.camera;
const SPEED = 0.9; // 걷는 속도 (땅 위 단위/초, 1단위 = 400px) — 대표 결정 2026-11-11 (character manifest walk.speed_px_s 360)
const DEPTH = 0.426; // 25° 카메라: 화면 세로 1px = 땅 위 1/0.426px (character manifest walk.depth_factor)
type Face = 'idle' | 'front' | 'side' | 'back';
const FACE_CLIP = { idle: 'garden_idle', front: 'walk_front', side: 'walk_side', back: 'walk_back' } as const;
// 밤 단짝 = 밤 색을 미리 입힌 클립 한 장 (scripts/gen_yard_night_pet.py). 움직이는 그림 두 장을 겹치면 각자 재생돼 어긋남
const NIGHT_CLIP = {
  idle: require('@/assets/pet/hippo_garden_idle_night.webp'),
  front: require('@/assets/pet/hippo_walk_front_night.webp'),
  side: require('@/assets/pet/hippo_walk_side_night.webp'),
  back: require('@/assets/pet/hippo_walk_back_night.webp'),
} as const;
const ACT_MS = 6000;
export const ACT_KO: Record<string, string> = {
  sniff: '🌷 킁킁', sit_bench: '🪑 쉬는 중', sit_eat: '🧺 냠냠', lie: '😴 쿨쿨', splash: '💦 첨벙', show_fruit: '🍑 이거 봐!',
};

let keptZoom = 1; // 줌 유지 (앱을 켜 둔 동안)

type Guest = { k: 'perch' } | { k: 'ground'; x: number; y: number } | { k: 'fly'; cx: number; cy: number };
export type YardTap =
  | { kind: 'zone'; zone: number }
  | { kind: 'forest' }
  | { kind: 'fruit'; index: number }
  | { kind: 'item'; id: string };

export type YardSceneHandle = { walkTo: (interactId: string, then?: () => void) => void };

type Props = {
  zones: number[];          // 산 구역 (1은 항상)
  items: string[];          // 가진 마당 소품 id
  stage: number;            // 추억 나무 단계 1~4
  fruitsHidden: number[];   // 이번에 딴 열매
  night: boolean;
  guests: boolean;          // 이번 방문에 손님이 오는지 (30%)
  active: boolean;          // 지금 보이는 페이지일 때만 움직임
  onTap: (t: YardTap) => void;
  onLeave?: () => void;     // 왼쪽 끝에서 더 끌면 (방으로)
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

export function YardScene({ zones, items, stage, fruitsHidden, night, guests, active, onTap, onLeave, bubble, sceneRef }: Props) {
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
  const [face, setFace] = useState<Face>('idle');
  const [petZ, setPetZ] = useState(() => moverZFrom(statics0(stage, items), YARD.walk.home[0], YARD.walk.home[1]));
  const [act, setAct] = useState<string | null>(null);
  const guestRef = useRef<Guest[]>([]);
  useEffect(() => { guestRef.current = guestList ?? []; }, [guestList]);

  // 움직이는 값 (화면 = UI 스레드 shared value, 계산은 JS 루프)
  const camX = useSharedValue(0), camY = useSharedValue(0), scale = useSharedValue(1);
  const petX = useSharedValue(YARD.walk.home[0]), petY = useSharedValue(YARD.walk.home[1]), petDir = useSharedValue(1), petBob = useSharedValue(0);
  const flyX = useSharedValue(0), flyY = useSharedValue(0), flyOpen = useSharedValue(0);

  const G = useRef({
    cam: { x: 0, y: 0 }, zoom: keptZoom, s: 1, vw: 1080, vh: 1860, started: false,
    pet: { x: YARD.walk.home[0], y: YARD.walk.home[1], dir: 1, face: 'side' as Face, t: 0, state: 'idle' as 'idle' | 'walk' | 'act', path: [] as Pt[], act: null as null | { id: string; action: string; stand: Pt }, until: 0, walks: 0, then: null as null | (() => void) },
    dragging: false, lastDrag: -1e9, glide: null as null | { t0: number; x: number; y: number }, glided: true,
    panStart: { x: 0, y: 0 }, pinchStart: 1, left: false,
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
    keptZoom = g.zoom;
    view();
    if (ax !== undefined && ay !== undefined) {
      g.cam.x = ax - ((ax - g.cam.x) * g.vw) / oldW;
      g.cam.y = ay - ((ay - g.cam.y) * g.vh) / oldH;
    }
    clamp(); push();
  }
  const petCenter = (): Pt => [G.current.pet.x + P.feet_to_center[0], G.current.pet.y + P.feet_to_center[1]];

  function goTo(pt: Pt, a?: { id: string; action: string; stand: Pt } | null, then?: () => void) {
    const g = G.current, m = getWalk();
    let path = findPath(m, [g.pet.x, g.pet.y], pt);
    if (a) path = path.concat([a.stand]);
    g.pet.path = path; g.pet.act = a ?? null; g.pet.then = then ?? null;
    g.pet.state = path.length ? 'walk' : a ? 'act' : 'idle';
    g.pet.until = performance.now() + (a && !path.length ? ACT_MS : 4000);
    if (!path.length && a) { setAct(a.action); then?.(); g.pet.then = null; }
    else setAct(null);
  }
  function walkToInteract(id: string, then?: () => void) {
    const v = YARD.walk.interact[id];
    if (!v) return;
    goTo(v.enter ?? v.stand, { id, action: v.action, stand: v.stand }, then);
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
    g.zoom = keptZoom;
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
    let raf = 0, last = performance.now(), lastZ = -1, lastFace: Face = 'idle';
    const loop = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000); last = now;
      const g = G.current, pet = g.pet;
      // 단짝
      pet.t += dt;
      if (pet.state === 'walk') {
        const t = pet.path[0];
        if (!t) {
          pet.state = pet.act ? 'act' : 'idle';
          pet.until = now + (pet.act ? ACT_MS : 4000 + Math.random() * 4000);
          if (pet.act) { setAct(pet.act.action); pet.then?.(); pet.then = null; }
        } else {
          // 속도는 땅 위 거리로 (화면 세로 이동은 25° 카메라라 짧아 보임)
          const dx = t[0] - pet.x, dy = t[1] - pet.y, d = Math.hypot(dx, dy / DEPTH), step = SPEED * YARD.px_per_unit * dt;
          if (Math.abs(dx) > 2) pet.dir = dx > 0 ? 1 : -1;
          pet.face = Math.abs(dx) >= Math.abs(dy / DEPTH) ? 'side' : dy > 0 ? 'front' : 'back';
          if (d <= step) { pet.x = t[0]; pet.y = t[1]; pet.path.shift(); } else { pet.x += (dx / d) * step; pet.y += (dy / d) * step; }
        }
      } else if (pet.state === 'act' && now > pet.until) {
        pet.state = 'idle'; pet.act = null; pet.until = now + 2000; setAct(null);
      } else if (pet.state === 'idle' && now > pet.until) {
        pet.walks++;
        const acts = Object.keys(YARD.walk.interact).filter((id) => id === 'pond' || id === 'tree' || ownItems.has(id));
        if (pet.walks % 3 === 0 && acts.length) walkToInteract(acts[Math.floor(Math.random() * acts.length)]);
        else goTo(randomWalkable());
      }
      // 걷기 = 25° 걷기 클립(왼쪽 = 옆 클립 뒤집기). 서 있기·동작 = 대기 클립 + 통통 (자리 동작 클립 오기 전 임시)
      const face: Face = pet.state === 'walk' && pet.path.length ? pet.face : 'idle';
      if (face !== lastFace) { lastFace = face; setFace(face); }
      const bob = face === 'idle' ? -Math.abs(Math.sin(pet.t * 3.2)) * 10 : 0;
      petX.value = pet.x; petY.value = pet.y; petDir.value = face === 'idle' || face === 'side' ? pet.dir : 1; petBob.value = bob;
      const z = moverZFrom(staticsRef.current, pet.x, pet.y);
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

  // 손가락: 끌기 = 둘러보기, 두 손가락 = 줌, 탭 = 걸어가기/구역·열매
  const pan = usePanGesture({
    minDistance: 8, maxPointers: 1, runOnJS: true,
    onActivate: () => { const g = G.current; g.dragging = true; g.glide = null; g.panStart = { ...g.cam }; g.left = false; },
    onUpdate: (e) => {
      const g = G.current;
      g.cam.x = g.panStart.x - e.translationX / g.s; g.cam.y = g.panStart.y - e.translationY / g.s;
      const want = g.cam.x;
      clamp(); push();
      // 왼쪽 끝에서 더 끌면 방으로
      if (onLeave && !g.left && g.cam.x - want > 90 / g.s) { g.left = true; onLeave(); }
    },
    onDeactivate: () => { const g = G.current; g.dragging = false; g.lastDrag = performance.now(); g.glide = null; },
  });
  const pinch = usePinchGesture({
    runOnJS: true,
    onActivate: () => { const g = G.current; g.dragging = true; g.pinchStart = g.zoom; },
    onUpdate: (e) => {
      const g = G.current;
      setZoom(g.pinchStart * e.scale, g.cam.x + e.focalX / g.s, g.cam.y + e.focalY / g.s);
    },
    onDeactivate: () => { const g = G.current; g.dragging = false; g.lastDrag = performance.now(); },
  });
  const tap = useTapGesture({
    maxDistance: 8, runOnJS: true,
    onDeactivate: (e) => {
      if (e.canceled) return;
      const g = G.current;
      handleTap(g.cam.x + e.x / g.s, g.cam.y + e.y / g.s);
    },
  });
  const gesture = useCompetingGestures(useSimultaneousGestures(pan, pinch), tap);

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
    // 피크닉 매트 (먹이기)
    const mat = YARD.items.find((e) => e.id === 'picnic_mat')!;
    if (ownItems.has('picnic_mat') && x > mat.x && x < mat.x + mat.w && y > mat.y && y < mat.y + mat.h) { onTap({ kind: 'item', id: 'picnic_mat' }); return; }
    goTo([x, y]);
  }

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
      { translateY: petY.value + P.feet_to_center[1] + petBob.value - P.h / 2 },
      { scaleX: petDir.value },
    ],
  }));
  const bubbleStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: petX.value - 300 }, { translateY: petY.value + P.feet_to_center[1] - P.h * 0.42 - 90 + petBob.value }],
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
  const splashOn = act === 'splash';
  const speech = bubble ?? (act ? ACT_KO[act] ?? null : null);
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
                <Image source={night ? NIGHT_CLIP[face] : PET_CLIPS[FACE_CLIP[face]].source} style={StyleSheet.absoluteFill} contentFit="contain" loading="eager" />
              </Animated.View>
              {splashOn && <Sprite {...YARD.extras.pond_water} night={night} z={900} />}
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
