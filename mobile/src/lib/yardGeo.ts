// 마당 걷기·화면 계산 (React 없음). 참고 구현 design/yard_test/index.html 그대로 옮김
import { YARD } from '@/data/yard';
import type { Poly, Pt, RectArr } from '@/data/yardTypes';

export const ZONES = Object.keys(YARD.walk.zones).map(Number); // 1..4

export function inPoly(x: number, y: number, P: Poly) {
  let c = false;
  for (let i = 0, j = P.length - 1; i < P.length; j = i++) {
    const [xi, yi] = P[i], [xj, yj] = P[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c;
  }
  return c;
}
function rectDist(x: number, y: number, [rx, ry, rw, rh]: RectArr) {
  const dx = Math.max(rx - x, 0, x - rx - rw), dy = Math.max(ry - y, 0, y - ry - rh);
  return Math.hypot(dx, dy);
}
export function zoneAt(x: number, y: number): number | null {
  for (const [z, Z] of Object.entries(YARD.walk.zones)) {
    const [rx, ry, rw, rh] = Z.rect;
    if (x >= rx && x < rx + rw && y >= ry && y < ry + rh) return Number(z);
  }
  return null;
}
// 정렬선(발 x 위치의 y, 양 끝은 고정)
export function lineY(L: Poly, x: number) {
  if (x <= L[0][0]) return L[0][1];
  for (let k = 1; k < L.length; k++) if (x <= L[k][0]) {
    const [x0, y0] = L[k - 1], [x1, y1] = L[k];
    return y0 + ((y1 - y0) * (x - x0)) / (x1 - x0);
  }
  return L[L.length - 1][1];
}

// 걷기 지도: 산 구역 + 가진 소품으로 만든다 (바뀔 때만 다시)
const G = 30;
export type WalkMap = { own: Set<number>; items: Set<string>; GW: number; GH: number; grid: Uint8Array };

function walkableRaw(own: Set<number>, items: Set<string>, x: number, y: number) {
  const W = YARD.walk;
  let inside = false;
  for (const [z, Z] of Object.entries(W.zones)) {
    if (!Z.area || !own.has(Number(z))) continue;
    if (inPoly(x, y, Z.area)) {
      inside = true;
      for (const p of Object.values(Z.blocked ?? {})) if (inPoly(x, y, p)) return false;
    }
  }
  if (!inside) return false;
  for (const [z, Z] of Object.entries(W.zones)) if (!own.has(Number(z)) && rectDist(x, y, Z.rect) < 70) return false;
  for (const p of Object.values(W.blocked)) if (inPoly(x, y, p)) return false;
  for (const [id, p] of Object.entries(W.item_blocked)) if (items.has(id) && inPoly(x, y, p)) return false;
  return true;
}

export function buildWalk(own: Set<number>, items: Set<string>): WalkMap {
  const GW = Math.ceil(YARD.canvas[0] / G), GH = Math.ceil(YARD.canvas[1] / G);
  const grid = new Uint8Array(GW * GH);
  for (let j = 0; j < GH; j++) for (let i = 0; i < GW; i++) grid[j * GW + i] = walkableRaw(own, items, i * G + G / 2, j * G + G / 2) ? 1 : 0;
  return { own, items, GW, GH, grid };
}
export const walkable = (m: WalkMap, x: number, y: number) => walkableRaw(m.own, m.items, x, y);

export function nearestCell(m: WalkMap, x: number, y: number) {
  let best = -1, bd = 1e18;
  for (let k = 0; k < m.grid.length; k++) if (m.grid[k]) {
    const cx = (k % m.GW) * G + G / 2, cy = Math.floor(k / m.GW) * G + G / 2, d = (cx - x) ** 2 + (cy - y) ** 2;
    if (d < bd) { bd = d; best = k; }
  }
  return best;
}
export const cellPt = (m: WalkMap, k: number): Pt => [(k % m.GW) * G + G / 2, Math.floor(k / m.GW) * G + G / 2];

function lineOK(m: WalkMap, a: Pt, b: Pt) {
  const n = Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 12);
  for (let k = 1; k < n; k++) {
    const t = k / n;
    if (!walkable(m, a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)) return false;
  }
  return true;
}

// A* (8방향) + 줄 당기기. 목적지가 못 가는 곳이면 가장 가까운 걷는 점까지
export function findPath(m: WalkMap, from: Pt, to: Pt): Pt[] {
  const { GW, GH, grid } = m;
  if (walkable(m, ...to) && lineOK(m, from, to)) return [to];
  const s = walkable(m, ...from) ? Math.floor(from[1] / G) * GW + Math.floor(from[0] / G) : nearestCell(m, ...from);
  const tIdx = walkable(m, ...to) ? Math.floor(to[1] / G) * GW + Math.floor(to[0] / G) : nearestCell(m, ...to);
  if (s < 0 || tIdx < 0) return [];
  const gS = new Float32Array(grid.length).fill(Infinity), came = new Int32Array(grid.length).fill(-1);
  const open = [s], inOpen = new Uint8Array(grid.length);
  gS[s] = 0; inOpen[s] = 1;
  const tx = tIdx % GW, ty = Math.floor(tIdx / GW), h = (k: number) => Math.hypot((k % GW) - tx, Math.floor(k / GW) - ty);
  while (open.length) {
    let bi = 0;
    for (let i = 1; i < open.length; i++) if (gS[open[i]] + h(open[i]) < gS[open[bi]] + h(open[bi])) bi = i;
    const c = open.splice(bi, 1)[0];
    inOpen[c] = 0;
    if (c === tIdx) break;
    const cx = c % GW, cy = Math.floor(c / GW);
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
      if (!dx && !dy) continue;
      const nx = cx + dx, ny = cy + dy;
      if (nx < 0 || ny < 0 || nx >= GW || ny >= GH) continue;
      const n = ny * GW + nx;
      if (!grid[n]) continue;
      if (dx && dy && (!grid[cy * GW + nx] || !grid[ny * GW + cx])) continue;
      const g = gS[c] + (dx && dy ? 1.414 : 1);
      if (g < gS[n]) { gS[n] = g; came[n] = c; if (!inOpen[n]) { open.push(n); inOpen[n] = 1; } }
    }
  }
  if (came[tIdx] < 0 && tIdx !== s) return [];
  const pts: Pt[] = [];
  for (let k = tIdx; k !== -1 && k !== s; k = came[k]) pts.unshift(cellPt(m, k));
  if (walkable(m, ...to)) pts.push(to);
  const out: Pt[] = [];
  let cur = from, i = 0;
  while (i < pts.length) {
    let j = pts.length - 1;
    while (j > i && !lineOK(m, cur, pts[j])) j--;
    out.push(pts[j]); cur = pts[j]; i = j + 1;
  }
  return out;
}

// 화면이 갈 수 있는 범위: 산 구역 + 맞닿은 잠긴 구역으로 peek px (README '마당' camera.bounds)
export function camBounds(own: Set<number>): [number, number, number, number] {
  const rects = Object.entries(YARD.walk.zones).filter(([z]) => own.has(Number(z))).map(([, Z]) => Z.rect);
  let x0 = Math.min(...rects.map((r) => r[0])), y0 = Math.min(...rects.map((r) => r[1]));
  let x1 = Math.max(...rects.map((r) => r[0] + r[2])), y1 = Math.max(...rects.map((r) => r[1] + r[3]));
  const peek = YARD.camera.peek;
  const ov = (a0: number, a1: number, b0: number, b1: number) => Math.min(a1, b1) > Math.max(a0, b0);
  for (const [z, Z] of Object.entries(YARD.walk.zones)) {
    if (own.has(Number(z)) || Z.price === null) continue;
    const [rx, ry, rw, rh] = Z.rect;
    if (rx === x1 && ov(ry, ry + rh, y0, y1)) x1 += peek;
    if (ry === y1 && ov(rx, rx + rw, x0, x1)) y1 += peek;
    if (rx + rw === x0 && ov(ry, ry + rh, y0, y1)) x0 -= peek;
  }
  return [x0, y0, x1, y1];
}

// 추억 나무 단계: 기록한 날 0~9 → 1, 10 → 2, 30 → 3, 60 → 4 (WORLD 7장 Y2)
export function treeStage(days: number) {
  return days >= 60 ? 4 : days >= 30 ? 3 : days >= 10 ? 2 : 1;
}
// 밤 = 기기 시간 19:00~06:00 (Y4)
export function isNight(d = new Date()) {
  const h = d.getHours();
  return h >= 19 || h < 6;
}
