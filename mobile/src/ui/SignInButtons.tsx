import * as AppleAuthentication from 'expo-apple-authentication';
import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { appleAvailable, signInWithApple, signInWithProvider } from '@/lib/auth';
import { Btn } from '@/ui/kit';
import { C, H as HT, R } from '@/ui/theme';

// 로그인·가입 버튼 묶음 — Apple(iOS) · 카카오 · 구글 · 이메일. '이미 계정이 있어요' 화면과 ⑥ 가입 시트가 같이 씀.
// 익명 세션이면 lib/auth가 '연결'(가입), 아니면 로그인으로 처리. 카카오·구글은 Supabase에 키를 넣은 뒤 env로 켠다
const KAKAO = process.env.EXPO_PUBLIC_AUTH_KAKAO === '1';
const GOOGLE = process.env.EXPO_PUBLIC_AUTH_GOOGLE === '1';

export function SignInButtons({ onEmail }: { onEmail?: () => void }) {
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
      setErr('연결하지 못했어. 다시 해볼래?');
    } finally {
      setBusy(null);
    }
  }

  return (
    <View style={st.col}>
      {apple && (
        <AppleAuthentication.AppleAuthenticationButton
          buttonType={AppleAuthentication.AppleAuthenticationButtonType.CONTINUE}
          buttonStyle={AppleAuthentication.AppleAuthenticationButtonStyle.BLACK}
          cornerRadius={26}
          style={{ height: HT.btn }}
          onPress={() => run('apple', signInWithApple)}
        />
      )}
      {KAKAO && (
        <Pressable accessibilityRole="button" disabled={!!busy} onPress={() => run('kakao', () => signInWithProvider('kakao'))} style={[st.social, { backgroundColor: C.kakao }]}>
          <Text style={[st.socialText, { color: C.kakaoInk }]}>{busy === 'kakao' ? '연결 중…' : '카카오로 계속하기'}</Text>
        </Pressable>
      )}
      {GOOGLE && (
        <Pressable accessibilityRole="button" disabled={!!busy} onPress={() => run('google', () => signInWithProvider('google'))} style={[st.social, st.google]}>
          <Text style={[st.socialText, { color: C.ink }]}>{busy === 'google' ? '연결 중…' : 'Google로 계속하기'}</Text>
        </Pressable>
      )}
      <Btn title="이메일로 계속하기" kind={apple || KAKAO || GOOGLE ? 'soft' : 'primary'} onPress={onEmail ?? (() => router.push('/auth/email'))} />
      {err ? <Text style={st.err}>{err}</Text> : null}
    </View>
  );
}

const st = StyleSheet.create({
  col: { gap: 10 },
  social: { minHeight: HT.btn, borderRadius: R.pill, alignItems: 'center', justifyContent: 'center' },
  google: { backgroundColor: C.card, borderWidth: 1, borderColor: C.divider },
  socialText: { fontSize: 15, fontWeight: '700' },
  err: { color: C.danger, fontSize: 13, textAlign: 'center' },
});
