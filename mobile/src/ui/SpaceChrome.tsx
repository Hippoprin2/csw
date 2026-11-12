import { Pressable, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { todayLabel } from '@/lib/dates';
import { useApp } from '@/state/app';
import { Icon } from './Icon';
import { FloatChip, Seeds } from './kit';
import { C, H, R } from './theme';

// 방·텃밭·마당 공통 틀 (A 포근한 창, 2026-11-13)
// - 그림 위 크림 칩 2개: 왼쪽 날짜+공간 이름, 오른쪽 씨앗
// - 판 안의 텃밭/방/마당 전환 (옅은 면 위 흰 알약). 마당에는 넣지 않음
// - 마당 왼쪽 가장자리 "‹ 방" 손잡이

export const SPACES = ['garden', 'room', 'yard'] as const;
export type SpaceKey = (typeof SPACES)[number];
const LABEL: Record<SpaceKey, string> = { garden: '텃밭', room: '방', yard: '마당' };

export type SpaceNav = { page: number; go: (p: number) => void };

// 그림 높이: 화면 위쪽 가로 꽉, 약 420 (작은 폰은 화면 높이의 절반, 최소 300)
export const PANEL_OVERLAP = 28;
export function useSceneHeight() {
  const { height } = useWindowDimensions();
  return Math.round(Math.min(420, Math.max(300, height * 0.5)));
}

export function SpaceChips({ space }: { space: SpaceKey }) {
  const { profile, balance } = useApp();
  const insets = useSafeAreaInsets();
  const pet = profile?.pet_name ?? '단짝';
  const date = todayLabel().replace(/요일$/, '');
  return (
    <View style={[st.chips, { top: insets.top + 8 }]} pointerEvents="box-none">
      <FloatChip style={{ flexShrink: 1 }}>
        <Text style={st.chipDate}>{date}</Text>
        <Text style={st.chipName} numberOfLines={1}>{pet}의 {LABEL[space]}</Text>
      </FloatChip>
      <Seeds n={balance} />
    </View>
  );
}

export function SpaceSwitch({ nav }: { nav: SpaceNav }) {
  return (
    <View style={st.seg} accessibilityRole="tablist">
      {SPACES.map((p, i) => {
        const on = nav.page === i;
        return (
          <Pressable key={p} onPress={() => nav.go(i)} style={[st.segItem, on && st.segOn]}
            accessibilityRole="tab" accessibilityState={{ selected: on }}>
            <Text style={[st.segText, on && st.segTextOn]}>{LABEL[p]}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

// 마당 → 방 손잡이 (왼쪽 가장자리, 위쪽 칩 아래)
export function RoomHandle({ onPress }: { onPress: () => void }) {
  const insets = useSafeAreaInsets();
  return (
    <Pressable onPress={onPress} style={[st.handle, { top: insets.top + 8 + H.chip + 12 }]}
      accessibilityRole="button" accessibilityLabel="방으로 가기" hitSlop={6}>
      <Icon name="chevronLeft" size={18} color={C.ink} />
      <Text style={st.handleText}>방</Text>
    </Pressable>
  );
}

const st = StyleSheet.create({
  chips: { position: 'absolute', left: 16, right: 16, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8, zIndex: 20 },
  chipDate: { fontSize: 13, color: C.muted, fontWeight: '600' },
  chipName: { fontSize: 13, color: C.ink, fontWeight: '800', flexShrink: 1 },
  seg: { flexDirection: 'row', backgroundColor: C.soft, borderRadius: R.pill, padding: 4, alignSelf: 'stretch' },
  segItem: { flex: 1, height: 36, borderRadius: R.pill, alignItems: 'center', justifyContent: 'center' },
  segOn: { backgroundColor: C.card },
  segText: { fontSize: 14, color: C.muted, fontWeight: '600' },
  segTextOn: { color: C.ink, fontWeight: '800' },
  handle: {
    position: 'absolute', left: 0, height: 44, paddingLeft: 8, paddingRight: 16, flexDirection: 'row', alignItems: 'center', gap: 2,
    backgroundColor: C.chip, borderTopRightRadius: R.pill, borderBottomRightRadius: R.pill, zIndex: 20,
  },
  handleText: { fontSize: 14, fontWeight: '700', color: C.ink },
});
