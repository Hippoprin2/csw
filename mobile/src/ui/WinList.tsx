import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { Win } from '@/lib/api';
import { CATS, type Category } from '@/lib/categories';
import { formatDay } from '@/lib/dates';
import { Icon } from '@/ui/Icon';
import { useWinSheet } from '@/ui/WinSheet';
import { C, R } from '@/ui/theme';

const COLLAPSE_OVER = 6; // 하루 기록이 많으면 접어서 표시

type Row = { key: string; text: string; category: Category; count: number; latest: Win; starred: boolean; note: string | null };

// 같은 날 같은 내용은 한 줄로 묶기 ("물 마셨다 ×4"). 누르면 가장 최근 것의 크게 보기
function groupDay(ws: Win[]): Row[] {
  const m = new Map<string, Row>();
  for (const w of ws) {
    const key = w.text.trim();
    const r = m.get(key);
    if (r) { r.count++; r.starred ||= w.starred; r.note ??= w.note; }
    else m.set(key, { key: w.id, text: key, category: w.category, count: 1, latest: w, starred: w.starred, note: w.note });
  }
  return [...m.values()];
}

export function byDay(wins: Win[]): [string, Win[]][] {
  const m = new Map<string, Win[]>();
  wins.forEach((w) => m.set(w.win_date, [...(m.get(w.win_date) ?? []), w]));
  return [...m.entries()].sort((a, b) => (a[0] < b[0] ? 1 : -1));
}

// 날짜별 기록 목록. 기록을 누르면 크게 보기 시트(고치기·지우기는 그 안 ···), 날짜 제목을 누르면 하루 한 장 (C9 M2)
// onChange: 이 목록이 가진 로컬 상태도 갱신하라고 알림
export function WinList({ wins, onChange }: { wins: Win[]; onChange?: (w: Win, deleted: boolean) => void }) {
  const { openWin } = useWinSheet();
  const [open, setOpen] = useState<Record<string, boolean>>({});

  return (
    <>
      {byDay(wins).map(([d, ws]) => {
        const rows = groupDay(ws);
        const collapsed = ws.length > COLLAPSE_OVER && !open[d];
        return (
          <View key={d} style={{ marginBottom: 16 }}>
            <Pressable onPress={() => router.push(`/jar/day/${d}`)} style={st.dayRow} accessibilityRole="button" accessibilityLabel={`${formatDay(d)}, 하루 한 장으로 보기`}>
              <Text style={st.dayH}>{formatDay(d)}</Text>
              <Icon name="chevronRight" size={14} color={C.muted} />
            </Pressable>
            {collapsed ? (
              <Pressable onPress={() => setOpen((o) => ({ ...o, [d]: true }))} style={st.win}>
                <Text style={[st.winText, { fontWeight: '700' }]}>{formatDay(d)} {ws.length}가지 · 펼치기</Text>
              </Pressable>
            ) : rows.map((r) => (
              <Pressable key={r.key} onPress={() => openWin(r.latest, onChange)} style={st.win} accessibilityRole="button" accessibilityHint="눌러서 크게 보기">
                <View style={[st.dot, { backgroundColor: CATS[r.category].color }]} />
                <View style={{ flex: 1 }}>
                  <Text style={st.winText}>{r.text}{r.count > 1 ? `  ×${r.count}` : ''}</Text>
                  {r.note ? <Text style={st.note} numberOfLines={1}>{r.note}</Text> : null}
                </View>
                {r.starred ? <Icon name="star" size={15} color={C.accentInk} fill={C.accentInk} /> : null}
                <Text style={st.tag}>{CATS[r.category].name}</Text>
              </Pressable>
            ))}
          </View>
        );
      })}
    </>
  );
}

export const st = StyleSheet.create({
  dayRow: { flexDirection: 'row', alignItems: 'center', gap: 2, alignSelf: 'flex-start', marginBottom: 8, marginLeft: 4, paddingRight: 8 },
  dayH: { fontSize: 13, color: C.muted, fontWeight: '700' },
  win: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: C.card, borderRadius: R.card, paddingVertical: 14, paddingHorizontal: 18, marginBottom: 6 },
  dot: { width: 10, height: 10, borderRadius: R.pill },
  winText: { fontSize: 15, color: C.ink },
  note: { fontSize: 13, color: C.muted, marginTop: 3 },
  tag: { fontSize: 11, color: C.muted, backgroundColor: C.soft, paddingVertical: 4, paddingHorizontal: 10, borderRadius: R.pill, overflow: 'hidden' },
});
