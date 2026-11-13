import Svg, { Circle, Path, Rect } from 'react-native-svg';

import { C } from './theme';

// 선 아이콘 한 벌 (이모지 대신, 2026-11-13 UI 개편). 24 격자, 선 굵기 1.8, 둥근 끝.
export type IconName =
  | 'home' | 'jar' | 'plant' | 'gear' | 'search' | 'basket' | 'leaf' | 'lock' | 'send'
  | 'chevronLeft' | 'chevronRight' | 'chevronDown' | 'check' | 'plus' | 'sparkle' | 'zzz'
  | 'fruit' | 'sliders' | 'close' | 'star' | 'more';

export function Icon({ name, size = 22, color = C.ink, stroke = 1.8, fill }: {
  name: IconName; size?: number; color?: string; stroke?: number; fill?: string;
}) {
  const p = { stroke: color, strokeWidth: stroke, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, fill: 'none' };
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      {name === 'home' && <>
        <Path {...p} d="M4 11.2 12 4.5l8 6.7" />
        <Path {...p} d="M6 9.8V19a1 1 0 0 0 1 1h3.5v-5h3v5H17a1 1 0 0 0 1-1V9.8" />
      </>}
      {name === 'jar' && <>
        <Rect {...p} x="7" y="3.5" width="10" height="3" rx="1.5" />
        <Path {...p} d="M8 6.5v1.3C6.2 8.9 5.5 10.4 5.5 12.5V18a2.5 2.5 0 0 0 2.5 2.5h8a2.5 2.5 0 0 0 2.5-2.5v-5.5c0-2.1-.7-3.6-2.5-4.7V6.5" />
        <Circle {...p} cx="10" cy="16" r="1.4" />
        <Circle {...p} cx="14.2" cy="14.6" r="1.4" />
      </>}
      {name === 'plant' && <>
        <Path {...p} d="M6.5 14h11l-1.3 5.4a1.5 1.5 0 0 1-1.5 1.1H9.3a1.5 1.5 0 0 1-1.5-1.1L6.5 14Z" />
        <Path {...p} d="M12 14V9.5" />
        <Path {...p} d="M12 10c0-3 2-5 5.5-5 0 3.2-2 5-5.5 5Z" />
        <Path {...p} d="M12 11.5c0-2.4-1.6-4-4.5-4 0 2.6 1.6 4 4.5 4Z" />
      </>}
      {name === 'gear' && <>
        <Circle {...p} cx="12" cy="12" r="3" />
        <Path {...p} d="M12 3.5v2.2M12 18.3v2.2M20.5 12h-2.2M5.7 12H3.5M18 6l-1.6 1.6M7.6 16.4 6 18M18 18l-1.6-1.6M7.6 7.6 6 6" />
        <Circle {...p} cx="12" cy="12" r="6.3" />
      </>}
      {name === 'search' && <>
        <Circle {...p} cx="11" cy="11" r="6" />
        <Path {...p} d="m15.5 15.5 4 4" />
      </>}
      {name === 'basket' && <>
        <Path {...p} d="M3.5 10h17l-1.6 8.3a2 2 0 0 1-2 1.7H7.1a2 2 0 0 1-2-1.7L3.5 10Z" />
        <Path {...p} d="M8 10 11 4.5M16 10l-3-5.5M9.5 13.5v3.5M14.5 13.5v3.5" />
      </>}
      {name === 'leaf' && <>
        <Path {...p} fill={fill ?? 'none'} d="M5 19c0-8 5-13.5 14-14 .3 8.6-5 14-14 14Z" />
        <Path {...p} d="M5 19c3-4 6-6.5 9.5-8.5" stroke={fill ? C.white : color} />
      </>}
      {name === 'lock' && <>
        <Rect {...p} x="5" y="10.5" width="14" height="10" rx="3" />
        <Path {...p} d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5M12 14.5v2" />
      </>}
      {name === 'send' && <Path {...p} d="M12 19V5.5M6.5 11 12 5.5l5.5 5.5" />}
      {name === 'chevronLeft' && <Path {...p} d="M14.5 6 8.5 12l6 6" />}
      {name === 'chevronRight' && <Path {...p} d="m9.5 6 6 6-6 6" />}
      {name === 'chevronDown' && <Path {...p} d="m6 9.5 6 6 6-6" />}
      {name === 'check' && <Path {...p} d="m5.5 12.5 4 4 9-9" />}
      {name === 'plus' && <Path {...p} d="M12 5.5v13M5.5 12h13" />}
      {name === 'close' && <Path {...p} d="m6.5 6.5 11 11M17.5 6.5l-11 11" />}
      {name === 'sparkle' && <>
        <Path {...p} d="M12 4c.6 4.2 1.8 5.4 6 6-4.2.6-5.4 1.8-6 6-.6-4.2-1.8-5.4-6-6 4.2-.6 5.4-1.8 6-6Z" />
        <Path {...p} d="M18.5 15.5v4M16.5 17.5h4" />
      </>}
      {name === 'zzz' && <Path {...p} d="M5 9h5l-5 6h5M13 5h4l-4 5h4M15.5 14h3.5l-3.5 4.5H19" />}
      {name === 'fruit' && <>
        <Circle {...p} cx="12" cy="14" r="6" />
        <Path {...p} d="M12 8c0-2 1-3.3 2.5-4M12 8c-1.8-1.6-4-1.6-5.5-.6 1.3 1.6 3.5 1.8 5.5.6Z" />
      </>}
      {name === 'star' && <Path {...p} fill={fill ?? 'none'} d="m12 4.2 2.3 4.8 5.2.7-3.8 3.6.9 5.2L12 16l-4.6 2.5.9-5.2-3.8-3.6 5.2-.7L12 4.2Z" />}
      {name === 'more' && <>
        <Circle cx="6" cy="12" r="1.6" fill={color} />
        <Circle cx="12" cy="12" r="1.6" fill={color} />
        <Circle cx="18" cy="12" r="1.6" fill={color} />
      </>}
      {name === 'sliders' && <>
        <Path {...p} d="M5 7h8M17 7h2M5 17h2M11 17h8" />
        <Circle {...p} cx="15" cy="7" r="2" />
        <Circle {...p} cx="9" cy="17" r="2" />
      </>}
    </Svg>
  );
}
