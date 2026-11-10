import { useWindowDimensions } from 'react-native';

// 공간 그림(방·텃밭·마당) 크기를 화면에 맞춘다.
// - 높이: 화면 높이의 42%, 280~380 사이 (작은 폰에서도 입력창이 첫 화면에 보이게)
// - 단짝 크기: 공간 높이에 비례 (방 기준 360 → 210)
// - 태블릿은 지원하지 않음(app.json supportsTablet=false), 넓은 화면은 화면 쪽에서 최대 너비 520으로 묶음
export function useSpaceSize() {
  const { height } = useWindowDimensions();
  const spaceH = Math.round(Math.min(380, Math.max(280, height * 0.42)));
  return { spaceH, petW: Math.round(spaceH * 0.58), gardenPetW: Math.round(spaceH * 0.3) };
}
