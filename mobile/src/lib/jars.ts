import type { Win } from './api';

// 유리병 하나에 들어가는 구슬 수 (2026-11-10 대표 결정: 50개 차면 뚜껑 닫아 선반에 진열 + 새 병)
export const JAR_SIZE = 50;

export type GlassJar = { no: number; wins: Win[]; from: string; to: string };

// 기록을 넣은 순서대로 50개씩 나눈다. 꽉 찬 병 = 선반, 마지막 병 = 지금 채우는 병(비어 있을 수 있음).
// 서버 저장 없이 기록 목록에서 계산 → 사용자가 기록을 지우면 그만큼 경계가 당겨진다(본인이 지운 것만큼).
export function splitJars(wins: Win[]): { shelf: GlassJar[]; current: GlassJar } {
  const asc = [...wins].sort((a, b) => (a.created_at < b.created_at ? -1 : a.created_at > b.created_at ? 1 : 0));
  const jars: GlassJar[] = [];
  for (let i = 0; i < asc.length; i += JAR_SIZE) {
    const ws = asc.slice(i, i + JAR_SIZE);
    const dates = ws.map((w) => w.win_date).sort();
    jars.push({ no: jars.length + 1, wins: ws, from: dates[0], to: dates[dates.length - 1] });
  }
  const last = jars[jars.length - 1];
  if (!last || last.wins.length === JAR_SIZE) {
    return { shelf: jars, current: { no: jars.length + 1, wins: [], from: '', to: '' } };
  }
  return { shelf: jars.slice(0, -1), current: last };
}

// 방금 기록으로 병이 꽉 찼는지 (기록 후 전체 개수 기준)
export const justSealed = (totalAfter: number) => totalAfter > 0 && totalAfter % JAR_SIZE === 0;
