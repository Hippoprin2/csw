import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api, friendlyError, type Win } from '@/lib/api';
import { CATEGORY_ORDER, CATS } from '@/lib/categories';
import { formatDay } from '@/lib/dates';
import { useApp } from '@/state/app';
import { H, Sub } from '@/ui/kit';
import { WinList } from '@/ui/WinList';
import { C, R } from '@/ui/theme';

// 선반의 닫힌 병 열기: 그 병의 기록 전부를 원문 그대로 (FEATURES C6 J1-A)
export default function JarDetail() {
  const { no } = useLocalSearchParams<{ no: string }>();
  const n = Number(no);
  const { jars } = useApp();
  const info = jars.jars.find((j) => j.no === n);
  const [wins, setWins] = useState<Win[] | null>(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    api.jarWins(n).then(setWins).catch((e) => setErr(friendlyError(e)));
  }, [n]);

  const byCat = info ? CATEGORY_ORDER.map((c) => [c, info.cats[c] ?? 0] as const).filter(([, k]) => k > 0) : [];
  return (
    <SafeAreaView style={st.wrap} edges={['top']}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
        <Pressable onPress={() => router.back()} accessibilityRole="button" style={{ marginBottom: 10 }}>
          <Text style={st.back}>‹ 유리병</Text>
        </Pressable>
        <H>{n}번째 병</H>
        {info && <Sub>{formatDay(info.from)} ~ {formatDay(info.to)} · 구슬 {info.count}개</Sub>}
        <View style={st.catRow}>
          {byCat.map(([c, k]) => <Text key={c} style={st.catPill}>{CATS[c].prop} {CATS[c].name} {k}</Text>)}
        </View>
        {err ? <Text style={st.err}>{err}</Text> : null}
        {!wins && !err ? <ActivityIndicator color={C.accent} style={{ marginTop: 30 }} /> : null}
        {wins && (
          <WinList
            wins={wins}
            onChange={(w, deleted) => setWins((ws) => (ws ?? []).flatMap((x) => (x.id !== w.id ? [x] : deleted ? [] : [w])))}
          />
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, maxWidth: 520, width: '100%', alignSelf: 'center' },
  back: { fontSize: 15, color: C.accent, fontWeight: '700' },
  catRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginVertical: 12 },
  catPill: { fontSize: 12, color: C.ink, backgroundColor: C.room, borderRadius: R.pill, paddingVertical: 4, paddingHorizontal: 9, overflow: 'hidden' },
  err: { color: '#c0392b', fontSize: 13, marginBottom: 8 },
});
