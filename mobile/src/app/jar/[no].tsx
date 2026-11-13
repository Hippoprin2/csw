import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api, friendlyError, type Win } from '@/lib/api';
import { CATEGORY_ORDER, CATS } from '@/lib/categories';
import { formatDay } from '@/lib/dates';
import { useApp } from '@/state/app';
import { Back, H, Sub } from '@/ui/kit';
import { MarbleJar } from '@/ui/MarbleJar';
import { patchList, RecordRow } from '@/ui/RecordList';
import { C, R } from '@/ui/theme';

// 병 열기: 그 병의 구슬 목록을 넣은 순서대로, 줄 앞 점 = 구슬 색 (FEATURES C6 J1-A, C9 N5)
// 선반의 닫힌 병 + 유리병 탭 지금 병의 "목록으로 보기"가 같이 씀. 위의 병도 같은 쓸어 보기
export default function JarDetail() {
  const { no } = useLocalSearchParams<{ no: string }>();
  const n = Number(no);
  const { jars, wins: allWins } = useApp();
  const info = jars.jars.find((j) => j.no === n);
  const isCurrent = n === jars.current_jar;
  const [wins, setWins] = useState<Win[] | null>(null);
  const [err, setErr] = useState('');
  const [locked, setLocked] = useState(false);

  // 지금 병은 방에서 새로 넣은 구슬도 바로 보이게 전역 기록에서 다시 받음
  const sig = isCurrent ? allWins.filter((w) => w.jar_no === n).length : 0;
  useEffect(() => {
    api.jarWins(n).then((ws) => setWins([...ws].reverse())).catch((e) => setErr(friendlyError(e)));
  }, [n, sig]);

  const onChange = (w: Win, deleted: boolean) => setWins(patchList(w, deleted));
  const cats = info?.cats ?? (wins ?? []).reduce<Record<string, number>>((m, w) => ({ ...m, [w.category]: (m[w.category] ?? 0) + 1 }), {});
  const byCat = CATEGORY_ORDER.map((c) => [c, cats[c] ?? 0] as const).filter(([, k]) => k > 0);
  return (
    <SafeAreaView style={st.wrap} edges={['top']}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }} scrollEnabled={!locked}>
        <Back label="유리병" onPress={() => router.back()} />
        <H>{n}번째 병</H>
        {info
          ? <Sub>{formatDay(info.from)} ~ {formatDay(info.to)} · 구슬 {info.count}개</Sub>
          : isCurrent && wins ? <Sub>지금 채우는 병 · 구슬 {wins.length}개</Sub> : null}
        {wins && wins.length > 0 && (
          <View style={{ marginTop: 16 }}>
            <MarbleJar wins={wins} label={`${n}번째 병, 구슬 ${wins.length}개`} onScrollLock={setLocked} onChange={onChange} />
          </View>
        )}
        <View style={st.catRow}>
          {byCat.map(([c, k]) => (
            <View key={c} style={st.catPill}>
              <View style={[st.catDot, { backgroundColor: CATS[c].color }]} />
              <Text style={st.catPillText}>{CATS[c].name} {k}</Text>
            </View>
          ))}
        </View>
        {err ? <Text style={st.err}>{err}</Text> : null}
        {!wins && !err ? <ActivityIndicator color={C.accent} style={{ marginTop: 30 }} /> : null}
        {wins && wins.length === 0 && <Text style={st.empty}>아직 빈 병이야. 다음 구슬은 여기에 들어가.</Text>}
        {wins && wins.length > 0 && <Text style={st.h}>넣은 순서</Text>}
        {wins?.map((w) => <RecordRow key={w.id} w={w} onChange={onChange} />)}
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, maxWidth: 520, width: '100%', alignSelf: 'center' },
  catRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginVertical: 12 },
  catPill: { flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: C.soft, borderRadius: R.pill, height: 28, paddingHorizontal: 11 },
  catDot: { width: 8, height: 8, borderRadius: R.pill },
  catPillText: { fontSize: 12, color: C.ink },
  err: { color: C.danger, fontSize: 13, marginBottom: 8 },
  empty: { textAlign: 'center', color: C.muted, paddingVertical: 30, fontSize: 14 },
  h: { fontSize: 13, color: C.muted, fontWeight: '700', marginBottom: 8, marginLeft: 4 },
});
