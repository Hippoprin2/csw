import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { api, type WinCounts } from '@/lib/api';
import { CATEGORY_ORDER, CATS } from '@/lib/categories';
import { useApp } from '@/state/app';
import { Icon } from '@/ui/Icon';
import { C, H as HT, R } from '@/ui/theme';

// 분류 칩 한 줄 (2026-11-16 F-B): ☆ 맨 앞, 나머지는 기록 많은 순. 누르면 그 분류 목록 화면, 뒤로 = 원래 화면
// 숫자는 전체 기록 기준(서버 win_counts). 유리병 탭 병 아래 + 찾기 화면(입력 전)에서 같이 씀
export function CatChips({ style }: { style?: object }) {
  const { wins } = useApp();
  const [counts, setCounts] = useState<WinCounts | null>(null);
  const sig = `${wins.length}:${wins.filter((w) => w.starred).length}:${wins.map((w) => w.category).join('')}`;
  useEffect(() => { api.winCounts().then(setCounts).catch(() => {}); }, [sig]);

  const cats = CATEGORY_ORDER.map((c) => [c, counts?.cats[c] ?? 0] as const)
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1]); // sort는 안정 정렬 → 같은 수면 기본 순서
  const starred = counts?.starred ?? 0;
  if (!counts || (cats.length === 0 && starred === 0)) return null;

  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={st.row} style={style} keyboardShouldPersistTaps="handled">
      <Pressable onPress={() => router.push('/jar/list/star')} style={st.chip} accessibilityRole="button" accessibilityLabel={`다시 보고 싶은 기록 ${starred}개`}>
        <Icon name="star" size={14} color={C.accentInk} fill={starred > 0 ? C.accentInk : undefined} />
        <Text style={st.text}>다시 보고 싶은{starred ? ` ${starred}` : ''}</Text>
      </Pressable>
      {cats.map(([c, n]) => (
        <Pressable key={c} onPress={() => router.push(`/jar/list/${c}`)} style={st.chip} accessibilityRole="button" accessibilityLabel={`${CATS[c].name} ${n}개`}>
          <View style={[st.dot, { backgroundColor: CATS[c].color }]} />
          <Text style={st.text}>{CATS[c].name} {n}</Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}

const st = StyleSheet.create({
  row: { gap: 6, paddingHorizontal: 2 },
  chip: { flexDirection: 'row', alignItems: 'center', gap: 6, height: HT.chip, paddingHorizontal: 14, borderRadius: R.pill, backgroundColor: C.soft },
  text: { fontSize: 13, color: C.ink, fontWeight: '600' },
  dot: { width: 8, height: 8, borderRadius: R.pill },
});
