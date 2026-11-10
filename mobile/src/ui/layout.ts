import { useWindowDimensions } from 'react-native';

// 공간 그림(방·텃밭·마당)은 정사각형 캔버스(design/world/export) → 카드도 정사각형.
// - 너비: 화면 너비 - 32 (최대 520 화면 기준)
// - 방: 아래 입력창이 첫 화면에 보이도록 화면 높이의 45%(최소 300)를 넘지 않게 → 작은 폰(SE)은 카드가 조금 작아지고 가운데 정렬
// - 텃밭·마당: 입력창이 없어서 너비 그대로
// - 태블릿 미지원(app.json supportsTablet=false)
export function useSpaceSize() {
  const { width, height } = useWindowDimensions();
  const full = Math.round(Math.min(width, 520) - 32);
  const roomSize = Math.min(full, Math.max(300, Math.round(height * 0.45)));
  return { roomSize, gardenSize: full };
}
