// 텃밭 ← 방 → 마당 페이지를 손가락으로 끌어 넘기기 (index의 바깥 스크롤을 UI 스레드에서 직접 움직임).
// 방 여백·방 그림 끝·마당 왼쪽 끝에서 공통으로 씀. 두 함수 모두 worklet이라 UI·JS 어디서 불러도 됨
export type Pager = {
  /** 이번 끌기에서 손가락이 움직인 거리(px, 오른쪽 +). 0부터 시작해 계속 불러 줌 */
  drag: (dx: number) => void;
  /** 손을 뗌: 1/4 넘게 또는 빠르게 끌었으면 옆 페이지, 아니면 제자리로 부드럽게 */
  end: (dx: number, vx: number, canceled?: boolean) => void;
};
