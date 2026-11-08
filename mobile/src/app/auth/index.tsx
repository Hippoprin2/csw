import { router } from 'expo-router';
import { Platform, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Btn } from '@/ui/kit';
import { Pet } from '@/ui/Pet';
import { C } from '@/ui/theme';

// S1/S2: 펫 인사 직후 가입 1화면. Apple·카카오는 개발자 계정·키 준비되면 env로 켠다.
const APPLE = process.env.EXPO_PUBLIC_AUTH_APPLE === '1' && Platform.OS === 'ios';
const KAKAO = process.env.EXPO_PUBLIC_AUTH_KAKAO === '1';

export default function Welcome() {
  return (
    <SafeAreaView style={st.wrap}>
      <View style={st.top}>
        <View style={st.bubble}>
          <Text style={st.bubbleText}>안녕! 오늘 해낸 걸 알려줘.{'\n'}아주 작은 것도 좋아.</Text>
        </View>
        <Pet action={{ kind: 'people', key: 1 }} size={200} />
      </View>
      <View style={st.bottom}>
        {APPLE && <Btn title="Apple로 계속하기" kind="dark" onPress={() => {}} />}
        {KAKAO && <Btn title="카카오로 계속하기" onPress={() => {}} style={{ backgroundColor: '#FEE500' }} />}
        <Btn title="이메일로 계속하기" onPress={() => router.push('/auth/email')} />
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
  legal: { fontSize: 12, color: C.muted, textAlign: 'center', marginTop: 6, lineHeight: 17 },
});
