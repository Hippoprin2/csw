import { Redirect, router } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useApp } from '@/state/app';
import { Back } from '@/ui/kit';
import { Pet } from '@/ui/Pet';
import { SignInButtons } from '@/ui/SignInButtons';
import { C } from '@/ui/theme';

// '이미 계정이 있어요' (①에서). 이미 있던 계정이면 선물·무료 안내 없이 바로 방.
// 처음 보는 방법이면 새 계정이 만들어지고 ②이름 ③동의 뒤 방 (무료 기간은 계정을 만든 때부터)
export default function Login() {
  const { session } = useApp();
  if (session) return <Redirect href="/onboarding" />; // 익명은 ⑥ 가입 시트에서 로그인
  return (
    <SafeAreaView style={st.wrap}>
      <Back label="뒤로" onPress={() => router.back()} />
      <View style={st.top}>
        <Pet action={{ kind: 'people', key: 2 }} size={170} />
        <Text style={st.h}>다시 만나서 반가워</Text>
        <Text style={st.sub}>예전에 쓰던 방법으로 로그인해줘.</Text>
      </View>
      <View style={st.bottom}>
        <SignInButtons />
      </View>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, padding: 24, maxWidth: 480, width: '100%', alignSelf: 'center' },
  top: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 10 },
  h: { fontSize: 22, fontWeight: '800', color: C.ink },
  sub: { fontSize: 14, color: C.muted },
  bottom: { paddingBottom: 8 },
});
