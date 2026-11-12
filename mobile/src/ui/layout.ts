import { useWindowDimensions } from 'react-native';

// 공간 그림(방·텃밭)은 화면 가로를 꽉 채운다 (A 포근한 창, 2026-11-13). 그림 높이는 SpaceChrome.useSceneHeight.
// - fullWidth: 화면 너비 (최대 520 화면 기준)
// - 태블릿 미지원(app.json supportsTablet=false)
export function useSpaceSize() {
  const { width } = useWindowDimensions();
  return { fullWidth: Math.round(Math.min(width, 520)) };
}
