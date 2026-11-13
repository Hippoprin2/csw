import { Image } from 'expo-image';
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { GestureDetector, usePanGesture } from 'react-native-gesture-handler';
import { SafeAreaView } from 'react-native-safe-area-context';

import { PET_ASPECT, PET_POSTER } from '@/data/petClips';
import { api, friendlyError, type Win } from '@/lib/api';
import { track } from '@/lib/analytics';
import { CATS } from '@/lib/categories';
import { kstToday, longDay } from '@/lib/dates';
import { useApp } from '@/state/app';
import { Icon } from '@/ui/Icon';
import { Back } from '@/ui/kit';
import { patchList } from '@/ui/RecordList';
import { useWinSheet } from '@/ui/WinSheet';
import { C, R } from '@/ui/theme';

// 하루 한 장 (C9 M2-B): 그날 기록을 한 장에. 좌우로 넘기면 기록한 날만 (빈 날은 건너뜀 — 놓친 날 압박 없게)
// 들어오는 길: 목록 날짜 제목, 방 '오늘의 쪽지' 다 보기
const isDay = (d: string) => /^\d{4}-\d{2}-\d{2}$/.test(d);
const label = (d: string) => `${Number(d.slice(5, 7))}월 ${Number(d.slice(8))}일`;

export default function DayPage() {
  const params = useLocalSearchParams<{ d: string }>();
  const d = params.d && isDay(params.d) ? params.d : kstToday();
  const { wins: allWins } = useApp();
  const { openWin } = useWinSheet();
  const [data, setData] = useState<{ d: string; wins: Win[]; prev: string | null; next: string | null } | null>(null);
  const [err, setErr] = useState('');

  // 오늘 장은 방에서 새로 적은 것도 바로 보이게
  const sig = allWins.filter((w) => w.win_date === d).map((w) => w.id + w.text + w.starred).join(',');
  useEffect(() => {
    let alive = true;
    api.dayWins(d).then((r) => { if (alive) { setData({ d, ...r }); setErr(''); } }).catch((e) => { if (alive) setErr(friendlyError(e)); });
    return () => { alive = false; };
  }, [d, sig]);
  useEffect(() => { track('day_viewed'); }, []);

  const go = (to: string | null) => { if (to) router.setParams({ d: to }); };
  const nav = useRef({ prev: null as string | null, next: null as string | null });
  useEffect(() => { nav.current = { prev: data?.prev ?? null, next: data?.next ?? null }; }, [data]);
  // 좌우로 밀어 넘기기 (세로 스크롤과 안 겹치게 가로로 충분히 움직였을 때만)
  const swipe = usePanGesture(useMemo(() => ({
    activeOffsetX: [-24, 24] as [number, number], failOffsetY: [-16, 16] as [number, number], runOnJS: true,
    onDeactivate: (e: { translationX: number; canceled: boolean }) => {
      if (e.canceled) return;
      if (e.translationX < -60 && nav.current.next) router.setParams({ d: nav.current.next });
      else if (e.translationX > 60 && nav.current.prev) router.setParams({ d: nav.current.prev });
    },
  }), []));

  const shown = data && data.d === d ? data : null;
  const onChange = (w: Win, deleted: boolean) =>
    setData((cur) => (cur ? { ...cur, wins: patchList(w, deleted)(cur.wins).filter((x) => x.win_date === cur.d) } : cur));

  return (
    <SafeAreaView style={st.wrap} edges={['top', 'bottom']}>
      <View style={{ paddingHorizontal: 20 }}>
        <Back label="유리병" onPress={() => router.back()} />
      </View>
      <GestureDetector gesture={swipe}>
        <View style={{ flex: 1 }}>
          <ScrollView contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 12, flexGrow: 1 }}>
            <View style={st.page}>
              <Text style={st.title}>{longDay(d)}</Text>
              {shown && <Text style={st.sub}>{shown.wins.length ? `이날 너는 ${shown.wins.length}가지를 해냈어` : '이날은 기록이 없어. 언제든 채워도 돼.'}</Text>}
              {err ? <Text style={st.err}>{err}</Text> : null}
              {!shown && !err ? <ActivityIndicator color={C.accent} style={{ marginTop: 30 }} /> : null}
              <View style={{ marginTop: 22 }}>
                {shown?.wins.map((w) => (
                  <Pressable key={w.id} onPress={() => openWin(w, onChange)} style={st.row} accessibilityRole="button" accessibilityHint="눌러서 크게 보기">
                    <View style={[st.dot, { backgroundColor: CATS[w.category].color }]} />
                    <View style={{ flex: 1 }}>
                      <Text style={st.text}>{w.text}</Text>
                      {w.note ? <Text style={st.note}>{w.note}</Text> : null}
                    </View>
                    {w.starred ? <Icon name="star" size={16} color={C.accentInk} fill={C.accentInk} /> : null}
                  </Pressable>
                ))}
              </View>
              <View style={{ flex: 1 }} />
              <Image source={PET_POSTER} style={st.pet} contentFit="contain" accessible={false} />
            </View>
          </ScrollView>
        </View>
      </GestureDetector>
      <View style={st.foot}>
        <Pressable onPress={() => go(shown?.prev ?? null)} disabled={!shown?.prev} hitSlop={10} accessibilityRole="button" accessibilityLabel={shown?.prev ? `이전 기록한 날, ${label(shown.prev)}` : undefined}>
          <Text style={[st.footText, !shown?.prev && { opacity: 0 }]}>‹ {shown?.prev ? label(shown.prev) : ''}</Text>
        </Pressable>
        <Pressable onPress={() => go(shown?.next ?? null)} disabled={!shown?.next} hitSlop={10} accessibilityRole="button" accessibilityLabel={shown?.next ? `다음 기록한 날, ${label(shown.next)}` : undefined}>
          <Text style={[st.footText, !shown?.next && { opacity: 0 }]}>{shown?.next ? label(shown.next) : ''} ›</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const PET_W = 76;
const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, maxWidth: 520, width: '100%', alignSelf: 'center' },
  page: { flex: 1, minHeight: 420, backgroundColor: C.card, borderRadius: R.cardLg, padding: 24, marginTop: 8 },
  title: { fontSize: 24, fontWeight: '800', color: C.ink },
  sub: { fontSize: 14, color: C.muted, marginTop: 6 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 15, borderBottomWidth: 1, borderBottomColor: C.divider },
  dot: { width: 10, height: 10, borderRadius: R.pill },
  text: { fontSize: 16, color: C.ink },
  note: { fontSize: 13, color: C.muted, marginTop: 3, lineHeight: 18 },
  err: { color: C.danger, fontSize: 13, marginTop: 8 },
  pet: { alignSelf: 'flex-end', width: PET_W, height: PET_W * PET_ASPECT, marginTop: 16 },
  foot: { flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: 24, paddingVertical: 12 },
  footText: { fontSize: 14, color: C.ink, fontWeight: '600' },
});
