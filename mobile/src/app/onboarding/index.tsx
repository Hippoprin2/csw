import { Redirect, router } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { track } from '@/lib/analytics';
import { useApp } from '@/state/app';
import { Btn } from '@/ui/kit';
import { Pet } from '@/ui/Pet';
import { C, H as HT, R } from '@/ui/theme';

// S1 이름 짓기 (기본 이름 제시, 건너뛰기 가능)
export default function NamePet() {
  const { profile, updateProfile, anonymous } = useApp();
  const [name, setName] = useState(profile?.pet_name ?? '하몽');
  const [busy, setBusy] = useState(false);
  // 동의까지 마친 익명 계정이 앱을 다시 열면 ④ 첫 기록(기록이 있으면 ⑥ 가입)으로 바로 (2026-11-17 첫 실행 순서 변경)
  if (anonymous && profile?.consented_at) return <Redirect href="/onboarding/first" />;

  async function next(skip = false) {
    setBusy(true);
    try {
      const n = name.trim();
      if (!skip && n && n !== profile?.pet_name) await updateProfile({ pet_name: n.slice(0, 12) });
      track('ob_name_done', { skip });
      router.push('/onboarding/notice');
    } finally {
      setBusy(false);
    }
  }

  return (
    <SafeAreaView style={st.wrap}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1, justifyContent: 'center', gap: 12 }}>
        <View style={{ alignItems: 'center' }}>
          <Pet action={{ kind: 'care', key: 1 }} size={190} />
        </View>
        <Text style={st.h}>내 이름을 지어줄래?</Text>
        <TextInput style={st.input} value={name} onChangeText={setName} maxLength={12} accessibilityLabel="단짝 이름" onSubmitEditing={() => next()} />
        <Btn title="이 이름으로 할래" onPress={() => next()} disabled={!name.trim()} loading={busy} />
        <Btn title="나중에 정할게" kind="ghost" onPress={() => next(true)} />
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, padding: 24, maxWidth: 480, width: '100%', alignSelf: 'center' },
  h: { fontSize: 22, fontWeight: '800', color: C.ink, textAlign: 'center', marginBottom: 6 },
  input: { fontSize: 20, height: HT.input + 4, paddingHorizontal: 22, borderRadius: R.pill, backgroundColor: C.card, color: C.ink, textAlign: 'center', fontWeight: '700' },
});
