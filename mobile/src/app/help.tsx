import { router } from 'expo-router';
import { Pressable, ScrollView, StyleSheet, Text } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { HelpLines } from '@/ui/kit';
import { C } from '@/ui/theme';

// 설정 › 도움받을 수 있는 곳 (S5 상시 안내)
export default function Help() {
  return (
    <SafeAreaView style={st.wrap}>
      <Pressable onPress={() => router.back()} accessibilityRole="button"><Text style={st.back}>닫기</Text></Pressable>
      <ScrollView contentContainerStyle={{ gap: 14, paddingBottom: 24 }}>
        <Text style={st.h}>도움받을 수 있는 곳</Text>
        <Text style={st.p}>마음이 많이 힘들 때는 혼자 버티지 않아도 돼요. 아래 번호는 모두 24시간 연결돼요. 번호를 누르면 바로 전화가 걸려요.</Text>
        <HelpLines />
        <Text style={st.small}>이 앱은 상담·치료 서비스가 아니에요. 운영자가 기록 내용을 보고 따로 연락하지 않아요.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, padding: 20, maxWidth: 480, width: '100%', alignSelf: 'center' },
  back: { fontSize: 15, color: C.muted, paddingVertical: 8, alignSelf: 'flex-end' },
  h: { fontSize: 22, fontWeight: '800', color: C.ink },
  p: { fontSize: 15, color: C.ink, lineHeight: 22 },
  small: { fontSize: 12, color: C.muted, lineHeight: 18 },
});
