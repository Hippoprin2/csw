import { router } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { track } from '@/lib/analytics';
import { redirectTo } from '@/lib/auth';
import { supabase } from '@/lib/supabase';
import { Back, Btn } from '@/ui/kit';
import { C, H as HT, R } from '@/ui/theme';

// 이메일 OTP 로그인 (가입 겸용). 코드 6자리 또는 메일 링크(→ auth/callback).
export default function EmailLogin() {
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const validEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());

  async function send() {
    setBusy(true); setErr('');
    const { error } = await supabase.auth.signInWithOtp({ email: email.trim(), options: { shouldCreateUser: true, emailRedirectTo: redirectTo } });
    setBusy(false);
    if (error) setErr(error.message.includes('rate') ? '잠시 뒤에 다시 시도해줘.' : '메일을 보내지 못했어. 주소를 확인해줄래?');
    else setSent(true);
  }

  async function verify() {
    setBusy(true); setErr('');
    const { error } = await supabase.auth.verifyOtp({ email: email.trim(), token: code.trim(), type: 'email' });
    setBusy(false);
    if (error) setErr('코드가 맞지 않거나 시간이 지났어. 다시 받아볼래?');
    else track('signed_in', { method: 'email' });
  }

  return (
    <SafeAreaView style={st.wrap}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <Back label="뒤로" onPress={() => (sent ? setSent(false) : router.back())} />
        <View style={{ flex: 1, justifyContent: 'center', gap: 12 }}>
          {!sent ? (
            <>
              <Text style={st.h}>이메일로 계속하기</Text>
              <Text style={st.sub}>로그인 코드를 메일로 보내줄게. 비밀번호는 필요 없어.</Text>
              <TextInput
                style={st.input} value={email} onChangeText={setEmail} placeholder="email@example.com" placeholderTextColor="#A8968A"
                autoCapitalize="none" autoComplete="email" keyboardType="email-address" inputMode="email"
                onSubmitEditing={() => validEmail && send()} accessibilityLabel="이메일"
              />
              <Btn title="코드 받기" onPress={send} disabled={!validEmail} loading={busy} />
            </>
          ) : (
            <>
              <Text style={st.h}>메일함을 확인해줘</Text>
              <Text style={st.sub}>{email.trim()}로 메일을 보냈어. 6자리 코드를 입력하거나, 휴대폰에서 메일 속 링크를 눌러줘.</Text>
              <TextInput
                style={[st.input, st.code]} value={code} onChangeText={(t) => setCode(t.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000" placeholderTextColor="#C9BBA8" keyboardType="number-pad" inputMode="numeric" autoComplete="one-time-code"
                textContentType="oneTimeCode" maxLength={6} accessibilityLabel="인증 코드"
                onSubmitEditing={() => code.length === 6 && verify()}
              />
              <Btn title="확인" onPress={verify} disabled={code.length !== 6} loading={busy} />
              <Btn title="코드 다시 받기" kind="ghost" onPress={send} disabled={busy} />
            </>
          )}
          {err ? <Text style={st.err}>{err}</Text> : null}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, padding: 24, maxWidth: 480, width: '100%', alignSelf: 'center' },
  h: { fontSize: 24, fontWeight: '800', color: C.ink },
  sub: { fontSize: 14, color: C.muted, lineHeight: 20, marginBottom: 6 },
  input: { fontSize: 17, height: HT.input, paddingHorizontal: 22, borderRadius: R.pill, backgroundColor: C.card, color: C.ink },
  code: { fontSize: 26, letterSpacing: 10, textAlign: 'center', fontWeight: '700' },
  err: { color: C.danger, fontSize: 13, textAlign: 'center' },
});
