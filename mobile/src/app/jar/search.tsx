import { router } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api, friendlyError, type Win } from '@/lib/api';
import { Icon } from '@/ui/Icon';
import { Back, H } from '@/ui/kit';
import { patchList, RecordList } from '@/ui/RecordList';
import { C, H as HT, R } from '@/ui/theme';

// 지난 기록 글자로 찾기 (최근 것부터 100개, 덧붙인 한 줄도 찾음). 결과는 분류별 목록과 같은 모양 (C9 N3). 검색어는 분석 이벤트에 넣지 않음
export default function JarSearch() {
  const [q, setQ] = useState('');
  const [res, setRes] = useState<Win[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  async function run() {
    const t = q.trim();
    if (!t) return;
    setBusy(true); setErr('');
    try { setRes(await api.searchWins(t)); } catch (e) { setErr(friendlyError(e)); }
    setBusy(false);
  }

  return (
    <SafeAreaView style={st.wrap} edges={['top']}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }} keyboardShouldPersistTaps="handled">
        <Back label="유리병" onPress={() => router.back()} />
        <H>기록 찾기</H>
        <View style={st.field}>
        <Icon name="search" size={20} color={C.muted} />
        <TextInput
          style={st.input} value={q} onChangeText={setQ} onSubmitEditing={run} returnKeyType="search" autoFocus
          placeholder="예) 산책, 엄마, 책" placeholderTextColor={C.muted} maxLength={50} accessibilityLabel="찾을 말"
        />
        </View>
        {busy ? <ActivityIndicator color={C.accent} /> : null}
        {err ? <Text style={st.msg}>{err}</Text> : null}
        {res && !busy && (res.length === 0
          ? <Text style={st.msg}>‘{q.trim()}’이 들어간 기록은 아직 없어.</Text>
          : <Text style={st.msg}>{res.length >= 100 ? '최근 100개' : `${res.length}개`}를 찾았어</Text>)}
        {res && (
          <RecordList wins={res} onChange={(w, deleted) => setRes(patchList(w, deleted))} />
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, maxWidth: 520, width: '100%', alignSelf: 'center' },
  field: { flexDirection: 'row', alignItems: 'center', gap: 8, height: HT.input, paddingLeft: 20, borderRadius: R.pill, backgroundColor: C.card, marginVertical: 12 },
  input: { flex: 1, minWidth: 0, height: HT.input, fontSize: 16, paddingRight: 20, color: C.ink },
  msg: { fontSize: 13, color: C.muted, marginBottom: 12 },
});
