import { router } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api, friendlyError, type Win } from '@/lib/api';
import { H } from '@/ui/kit';
import { WinList } from '@/ui/WinList';
import { C, R } from '@/ui/theme';

// 지난 기록 글자로 찾기 (최근 것부터 100개). 검색어는 분석 이벤트에 넣지 않음
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
        <Pressable onPress={() => router.back()} accessibilityRole="button" style={{ marginBottom: 10 }}>
          <Text style={st.back}>‹ 유리병</Text>
        </Pressable>
        <H>기록 찾기</H>
        <TextInput
          style={st.input} value={q} onChangeText={setQ} onSubmitEditing={run} returnKeyType="search" autoFocus
          placeholder="예) 산책, 엄마, 책" placeholderTextColor={C.muted} maxLength={50} accessibilityLabel="찾을 말"
        />
        {busy ? <ActivityIndicator color={C.accent} /> : null}
        {err ? <Text style={st.msg}>{err}</Text> : null}
        {res && !busy && (res.length === 0
          ? <Text style={st.msg}>‘{q.trim()}’이 들어간 기록은 아직 없어.</Text>
          : <Text style={st.msg}>{res.length >= 100 ? '최근 100개' : `${res.length}개`}를 찾았어</Text>)}
        {res && (
          <WinList
            wins={res}
            onChange={(w, deleted) => setRes((ws) => (ws ?? []).flatMap((x) => (x.id !== w.id ? [x] : deleted ? [] : [w])))}
          />
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, maxWidth: 520, width: '100%', alignSelf: 'center' },
  back: { fontSize: 15, color: C.accent, fontWeight: '700' },
  input: { fontSize: 16, padding: 12, borderRadius: R.input, borderWidth: 1.5, borderColor: C.line, backgroundColor: '#fff', color: C.ink, marginVertical: 12 },
  msg: { fontSize: 13, color: C.muted, marginBottom: 12 },
});
