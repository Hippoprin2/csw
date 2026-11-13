import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api, friendlyError, LIST_PAGE, type ListFilter, type Win } from '@/lib/api';
import { track } from '@/lib/analytics';
import { CATEGORY_ORDER, CATS, type Category } from '@/lib/categories';
import { useApp } from '@/state/app';
import { Icon } from '@/ui/Icon';
import { Back, Btn, H, Sub } from '@/ui/kit';
import { patchList, RecordList } from '@/ui/RecordList';
import { C, R } from '@/ui/theme';

// 목록 화면 하나 (C9 M2·M3·N3): 분류별 모아 보기 /jar/list/move, ☆ 다시 보고 싶은 기록 /jar/list/star
// 최근 것부터 100개씩, 달 제목. 숫자는 늘기만 함 (비교·목표 없음)
export default function RecordsList() {
  const { f } = useLocalSearchParams<{ f: string }>();
  const filter: ListFilter | null = f === 'star' || CATEGORY_ORDER.includes(f as Category) ? (f as ListFilter) : null;
  const { wins: allWins } = useApp();
  const [wins, setWins] = useState<Win[] | null>(null);
  const [more, setMore] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  // ☆ 목록에서 ☆를 끄면 바로 빠지게: 전역 기록의 ☆가 바뀌면 다시 받음
  const sig = filter === 'star' ? allWins.filter((w) => w.starred).map((w) => w.id).join(',') : '';
  useEffect(() => {
    if (!filter) return;
    api.listWins(filter, 0).then((ws) => { setWins(ws); setMore(ws.length === LIST_PAGE); }).catch((e) => setErr(friendlyError(e)));
  }, [filter, sig]);
  useEffect(() => { if (filter) track('records_list_viewed', { f: filter }); }, [filter]);

  async function loadMore() {
    if (!filter || !wins) return;
    setBusy(true);
    try {
      const ws = await api.listWins(filter, Math.floor(wins.length / LIST_PAGE));
      setWins([...wins, ...ws.filter((w) => !wins.some((x) => x.id === w.id))]); setMore(ws.length === LIST_PAGE);
    } catch (e) { setErr(friendlyError(e)); }
    setBusy(false);
  }
  const onChange = (w: Win, deleted: boolean) =>
    setWins((ws) => patchList(w, deleted || (filter === 'star' ? !w.starred : w.category !== filter))(ws));

  const star = filter === 'star';
  const n = wins?.length ?? 0;
  return (
    <SafeAreaView style={st.wrap} edges={['top']}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
        <Back label="유리병" onPress={() => router.back()} />
        {filter && (
          <View style={st.titleRow}>
            {star
              ? <Icon name="star" size={22} color={C.accentInk} fill={C.accentInk} />
              : <View style={[st.dot, { backgroundColor: CATS[filter as Category].color }]} />}
            <H style={{ flexShrink: 1 }}>{star ? '다시 보고 싶은 기록' : CATS[filter as Category].name}</H>
          </View>
        )}
        {filter && wins && (
          <Sub>{star
            ? n ? '크기랑 상관없이, 다시 읽고 싶은 것만 모았어.' : '기록을 눌러 크게 보기에서 ☆를 누르면 여기 모여.'
            : `지금까지 ${more ? `${n}가지 넘게` : `${n}가지`} 모였어.`}</Sub>
        )}
        {!filter && <Text style={st.err}>없는 목록이야.</Text>}
        {err ? <Text style={st.err}>{err}</Text> : null}
        {filter && !wins && !err ? <ActivityIndicator color={C.accent} style={{ marginTop: 30 }} /> : null}
        <View style={{ height: 14 }} />
        {wins && <RecordList wins={wins} onChange={onChange} />}
        {more && <Btn title="더 보기" kind="ghost" onPress={loadMore} loading={busy} />}
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, maxWidth: 520, width: '100%', alignSelf: 'center' },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  dot: { width: 14, height: 14, borderRadius: R.pill },
  err: { color: C.danger, fontSize: 13, marginVertical: 8 },
});
