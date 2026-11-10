import type { JarInfo, JarSummary } from './api';
import { CATEGORY_ORDER, type Category } from './categories';

// 유리병 하나에 들어가는 구슬 수 (2026-11-10 대표 결정). 병 번호는 서버(record_win)가 넣는 순간 고정 → 바꾸려면 DB 함수도 같이
export const JAR_SIZE = 50;

// 선반 = 지금 병보다 앞 번호의 병(구슬이 남아 있는 것만). 연도별 칸, 최근 연도·최근 병 먼저
export function shelfByYear(s: JarSummary): { year: string; jars: JarInfo[] }[] {
  const shelf = s.jars.filter((j) => j.no < s.current_jar && j.count > 0).sort((a, b) => b.no - a.no);
  const m = new Map<string, JarInfo[]>();
  shelf.forEach((j) => { const y = j.to.slice(0, 4); m.set(y, [...(m.get(y) ?? []), j]); });
  return [...m.entries()].sort((a, b) => (a[0] < b[0] ? 1 : -1)).map(([year, jars]) => ({ year, jars }));
}

// 닫힌 병 그림용: 카테고리별 개수를 구슬 색 목록으로
export function jarMarbles(j: JarInfo): Category[] {
  return CATEGORY_ORDER.flatMap((c) => Array<Category>(j.cats[c] ?? 0).fill(c));
}
