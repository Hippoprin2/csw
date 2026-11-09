// 방 소품 자리(slot) → 화면 위치 (방 그림 영역 기준 %). 임시 배치.
// 공간 스레드가 렌더한 소품 이미지 + 위치 JSON이 나오면 이 파일을 그 JSON으로 대체한다 (docs/WORLD.md 1장).
type Pct = `${number}%`;
type Pos = { left?: Pct; right?: Pct; top?: Pct; bottom?: Pct; size: number };

export const SLOT_POS: Record<string, Pos> = {
  window: { left: '5%', top: '7%', size: 40 },
  wall_left: { left: '33%', top: '8%', size: 28 },
  wall_right: { right: '8%', top: '8%', size: 28 },
  wall_top: { left: '46%', top: '1%', size: 24 },
  ceiling: { left: '64%', top: '1%', size: 26 },
  back_left: { left: '2%', bottom: '30%', size: 46 },
  back_right: { right: '2%', bottom: '33%', size: 42 },
  bedside: { left: '23%', bottom: '37%', size: 26 },
  lean: { right: '22%', bottom: '35%', size: 32 },
  floor_center: { left: '40%', bottom: '3%', size: 40 },
  floor_right: { right: '14%', bottom: '16%', size: 30 },
  front_left: { left: '4%', bottom: '4%', size: 32 },
  front_right: { right: '4%', bottom: '4%', size: 34 },
  front_center: { left: '24%', bottom: '2%', size: 28 },
};
