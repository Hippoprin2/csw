import { Redirect, router } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { startAnonymous } from '@/lib/auth';
import { useApp } from '@/state/app';
import { Btn } from '@/ui/kit';
import { Pet } from '@/ui/Pet';
import { C, R } from '@/ui/theme';

// ① 인사 (2026-11-17 첫 실행 순서 변경, design/onboarding sheet1). 로그인 버튼 대신 '시작하기' 하나 →
// 익명 계정으로 바로 ②이름 ③동의 ④첫 기록. 가입은 첫 기록 축하 뒤 ⑥. 예전에 가입한 사람은 '이미 계정이 있어요'
export default function Welcome() {
  const { session } = useApp();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  if (session) return <Redirect href="/onboarding" />;

  async function start() {
    setBusy(true); setErr('');
    try {
      await startAnonymous(); // 세션이 생기면 루트 가드가 ② 이름으로
    } catch {
      setErr('시작하지 못했어. 인터넷 연결을 확인하고 다시 해볼래?');
      setBusy(false);
    }
  }

  return (
    <SafeAreaView style={st.wrap}>
      <View style={st.top}>
        <View style={st.bubble}>
          <Text style={st.bubbleText}>안녕! 오늘 해낸 걸 알려주면{'\n'}내가 축하해 줄게. 아주 작은 것도 좋아.</Text>
        </View>
        <Pet action={{ kind: 'people', key: 1 }} size={230} />
      </View>
      <View style={st.bottom}>
        <Btn title="시작하기" onPress={start} loading={busy} />
        <Btn title="이미 계정이 있어요" kind="ghost" onPress={() => router.push('/auth/login')} disabled={busy} />
        {err ? <Text style={st.err}>{err}</Text> : null}
      </View>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, padding: 24, maxWidth: 480, width: '100%', alignSelf: 'center' },
  top: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16 },
  bubble: { backgroundColor: C.card, borderRadius: R.card, paddingVertical: 14, paddingHorizontal: 20 },
  bubbleText: { fontSize: 16, fontWeight: '600', color: C.ink, textAlign: 'center', lineHeight: 23 },
  bottom: { gap: 10, paddingBottom: 8 },
  err: { color: C.danger, fontSize: 13, textAlign: 'center' },
});
