import { router, useLocalSearchParams } from 'expo-router';
import { Pressable, ScrollView, StyleSheet, Text } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { LEGAL } from '@/data/legal';
import { Icon } from '@/ui/Icon';
import { C, R } from '@/ui/theme';

// 약관·처리방침 앱 안 보기 (로그인 전·온보딩·설정 어디서든 열림). 원문 docs/legal/*.md → scripts/gen_legal.py
export default function Legal() {
  const { doc } = useLocalSearchParams<{ doc: string }>();
  const blocks = LEGAL[doc === 'terms' ? 'terms' : 'privacy'];
  return (
    <SafeAreaView style={st.wrap}>
      <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))} accessibilityRole="button" accessibilityLabel="닫기" style={st.close} hitSlop={8}>
        <Icon name="close" size={20} color={C.ink} />
      </Pressable>
      <ScrollView contentContainerStyle={{ gap: 8, paddingBottom: 32 }}>
        {blocks.map(([k, t], i) => (
          <Text key={i} style={st[k]}>{k === 'li' ? `· ${t}` : t}</Text>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, padding: 20, maxWidth: 560, width: '100%', alignSelf: 'center' },
  close: { alignSelf: 'flex-end', width: 40, height: 40, borderRadius: R.pill, backgroundColor: C.soft, alignItems: 'center', justifyContent: 'center', marginBottom: 8 },
  h1: { fontSize: 22, fontWeight: '800', color: C.ink, marginBottom: 6 },
  h2: { fontSize: 16, fontWeight: '800', color: C.ink, marginTop: 14 },
  p: { fontSize: 14, color: C.ink, lineHeight: 21 },
  li: { fontSize: 14, color: C.ink, lineHeight: 21, paddingLeft: 6 },
});
