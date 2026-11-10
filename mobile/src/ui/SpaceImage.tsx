import { Image } from 'expo-image';
import type { ReactNode } from 'react';
import { View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';

import type { Rect } from '@/data/world';

// 캔버스 px 위치(design/world/export manifest)를 화면 pt로 바꿔 그림 한 장을 얹는다
export function SpaceImage({ source, rect, s, fadeIn, children, label }: {
  source: number; rect: Rect; s: number; fadeIn?: boolean; children?: ReactNode; label?: string;
}) {
  const style = { position: 'absolute' as const, left: rect.x * s, top: rect.y * s, width: rect.w * s, height: rect.h * s };
  const img = <Image source={source} style={{ width: '100%', height: '100%' }} contentFit="fill" loading="eager" accessibilityLabel={label} />;
  if (fadeIn) return <Animated.View entering={FadeIn.duration(600)} style={style} pointerEvents="none">{img}{children}</Animated.View>;
  return <View style={style} pointerEvents="none">{img}{children}</View>;
}
