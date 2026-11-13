import { useEffect, useState } from 'react';
import { AccessibilityInfo } from 'react-native';

// 기기 '동작 줄이기' 설정 (iOS 손쉬운 사용 → 동작 → 동작 줄이기). 켜져 있으면 단짝 동작 대신 멈춘 그림 (C9 N1)
export function useReduceMotion() {
  const [on, setOn] = useState(false);
  useEffect(() => {
    let alive = true;
    AccessibilityInfo.isReduceMotionEnabled().then((v) => { if (alive) setOn(v); }).catch(() => {});
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setOn);
    return () => { alive = false; sub.remove(); };
  }, []);
  return on;
}
