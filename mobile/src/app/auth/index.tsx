import * as AppleAuthentication from 'expo-apple-authentication';
import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { appleAvailable, signInWithApple, signInWithProvider } from '@/lib/auth';
import { Btn } from '@/ui/kit';
import { Pet } from '@/ui/Pet';
import { C, R } from '@/ui/theme';

// S1/S2: 펫 인사 직후 가입 1화면 — Apple(iOS) · 카카오 · 구글 · 이메일.
// 카카오·구글은 Supabase에 키를 넣은 뒤 env로 켠다 (키 없이 누르면 오류가 나므로).
const KAKAO = process.env.EXPO_PUBLIC_AUTH_KAKAO === '1';
const GOOGLE = process.env.EXPO_PUBLIC_AUTH_GOOGLE === '1';

export default function Welcome() {
  const [apple, setApple] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    appleAvailable().then(setApple).catch(() => setApple(false));
  }, []);

  async function run(name: string, fn: () => Promise<boolean>) {
    setBusy(name); setErr('');
    try {
      await fn();
    } catch {
      setErr('로그인하지 못했어. 다시 해볼래?');
    } finally {
      setBusy(null);
    }
  }

  return (
    <SafeAreaView style={st.wrap}>
      <View style={st.top}>
        <View style={st.bubble}>
          <Text style={st.bubbleText}>안녕! 오늘 해낸 걸 알려줘.{'\n'}아주 작은 것도 좋아.</Text>
        </View>
        <Pet action={{ kind: 'people', key: 1 }} size={230} />
      </View>
      <View style={st.bottom}>
        {apple && (
          <AppleAuthentication.AppleAuthenticationButton
            buttonType={AppleAuthentication.AppleAuthenticationButtonType.CONTINUE}
            buttonStyle={AppleAuthentication.AppleAuthenticationButtonStyle.BLACK}
            cornerRadius={R.input}
            style={{ height: 48 }}
            onPress={() => run('apple', signInWithApple)}
          />
        )}
        {KAKAO && (
          <Pressable accessibilityRole="button" disabled={!!busy} onPress={() => run('kakao', () => signInWithProvider('kakao'))} style={[st.social, { backgroundColor: '#FEE500' }]}>
            <Text style={[st.socialText, { color: '#191919' }]}>{busy === 'kakao' ? '연결 중…' : '카카오로 계속하기'}</Text>
          </Pressable>
        )}
        {GOOGLE && (
          <Pressable accessibilityRole="button" disabled={!!busy} onPress={() => run('google', () => signInWithProvider('google'))} style={[st.social, { backgroundColor: '#fff', borderWidth: 1, borderColor: C.line }]}>
            <Text style={[st.socialText, { color: C.ink }]}>{busy === 'google' ? '연결 중…' : 'Google로 계속하기'}</Text>
          </Pressable>
        )}
        <Btn title="이메일로 계속하기" kind={apple || KAKAO || GOOGLE ? 'ghost' : 'primary'} onPress={() => router.push('/auth/email')} />
        {err ? <Text style={st.err}>{err}</Text> : null}
        <Text style={st.legal}>
          계속하면 이용약관과 개인정보처리방침에 동의하고, 만 14세 이상임을 확인한 것으로 봐요.
        </Text>
      </View>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, padding: 24, maxWidth: 480, width: '100%', alignSelf: 'center' },
  top: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16 },
  bubble: { backgroundColor: '#fff', borderRadius: 18, paddingVertical: 12, paddingHorizontal: 16 },
  bubbleText: { fontSize: 16, fontWeight: '600', color: C.ink, textAlign: 'center', lineHeight: 23 },
  bottom: { gap: 10, paddingBottom: 8 },
  social: { minHeight: 48, borderRadius: R.input, alignItems: 'center', justifyContent: 'center' },
  socialText: { fontSize: 15, fontWeight: '700' },
  err: { color: '#c0392b', fontSize: 13, textAlign: 'center' },
  legal: { fontSize: 12, color: C.muted, textAlign: 'center', marginTop: 6, lineHeight: 17 },
});
