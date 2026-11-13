import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { Win } from '@/lib/api';
import { CATS } from '@/lib/categories';
import { kstToday, shortDay } from '@/lib/dates';
import { Icon } from '@/ui/Icon';
import { useWinSheet } from '@/ui/WinSheet';
import { C, R } from '@/ui/theme';

type OnChange = (w: Win, deleted: boolean) => void;

// 기록 한 줄: 색 점(= 구슬 색) + 원문 (+ 덧붙인 한 줄) + ☆ + 짧은 날짜. 누르면 크게 보기
export function RecordRow({ w, onChange, showDate = true }: { w: Win; onChange?: OnChange; showDate?: boolean }) {
  const { openWin } = useWinSheet();
  return (
    <Pressable onPress={() => openWin(w, onChange)} style={st.row} accessibilityRole="button" accessibilityHint="눌러서 크게 보기">
      <View style={[st.dot, { backgroundColor: CATS[w.category].color }]} />
      <View style={{ flex: 1 }}>
        <Text style={st.text}>{w.text}</Text>
        {w.note ? <Text style={st.note} numberOfLines={2}>{w.note}</Text> : null}
      </View>
      {w.starred ? <Icon name="star" size={15} color={C.accentInk} fill={C.accentInk} /> : null}
      {showDate ? <Text style={st.date}>{shortDay(w.win_date)}</Text> : null}
    </Pressable>
  );
}

// 목록 화면 모양 (C9 N3): 분류별·☆·찾기 결과가 같이 씀. 달 제목 아래 최근 것부터
export function RecordList({ wins, onChange }: { wins: Win[]; onChange?: OnChange }) {
  const months: [string, Win[]][] = [];
  for (const w of wins) {
    const m = w.win_date.slice(0, 7);
    const last = months[months.length - 1];
    if (last && last[0] === m) last[1].push(w);
    else months.push([m, [w]]);
  }
  const thisYear = kstToday().slice(0, 4);
  return (
    <>
      {months.map(([m, ws]) => (
        <View key={m} style={{ marginBottom: 14 }}>
          <Text style={st.month}>{m.slice(0, 4) === thisYear ? '' : `${m.slice(0, 4)}년 `}{Number(m.slice(5))}월</Text>
          {ws.map((w) => <RecordRow key={w.id} w={w} onChange={onChange} />)}
        </View>
      ))}
    </>
  );
}

// 로컬 목록 갱신 도우미: 고친 건 바꾸고 지운 건 뺀다
export const patchList = (w: Win, deleted: boolean) => (ws: Win[] | null) =>
  (ws ?? []).flatMap((x) => (x.id !== w.id ? [x] : deleted ? [] : [w]));

export const st = StyleSheet.create({
  month: { fontSize: 13, color: C.muted, fontWeight: '700', marginBottom: 8, marginLeft: 4 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: C.card, borderRadius: R.card, paddingVertical: 14, paddingHorizontal: 18, marginBottom: 6 },
  dot: { width: 10, height: 10, borderRadius: R.pill },
  text: { fontSize: 15, color: C.ink },
  note: { fontSize: 13, color: C.muted, marginTop: 3, lineHeight: 18 },
  date: { fontSize: 12, color: C.muted },
});
