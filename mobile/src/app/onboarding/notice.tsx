import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '@/lib/api';
import { track } from '@/lib/analytics';
import { useApp } from '@/state/app';
import { Icon } from '@/ui/Icon';
import { Btn } from '@/ui/kit';
import { C, R } from '@/ui/theme';

// 한 줄 안내 + 고지·동의 1화면 (FEATURES 3장, D4)
const ITEMS = [
  { key: 'age', label: '만 14세 이상이에요' },
  { key: 'notCounsel', label: '이 앱은 상담·치료 서비스가 아니라는 걸 알아요' },
  { key: 'privacy', label: '개인정보 수집·이용에 동의해요 (기록 분류를 위해 기록 내용이 이름 없이 해외 AI 서비스로 전송돼요)' },
] as const;

export default function Notice() {
  const { updateProfile, refresh } = useApp();
  const [ok, setOk] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);
  const all = ITEMS.every((i) => ok[i.key]);

  async function start() {
    setBusy(true);
    try {
      await api.gift(); // 온보딩 선물 씨앗 6개 → 첫날 첫 소품 구매 가능
      const now = new Date().toISOString();
      await updateProfile({ consented_at: now, onboarded_at: now });
      await refresh();
      track('onboarding_done');
    } finally {
      setBusy(false);
    }
  }

  return (
    <SafeAreaView style={st.wrap}>
      <ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: 'center', gap: 14 }}>
        <Text style={st.big}>침대 정리도, 물 한 잔도{'\n'}다 승리야.</Text>
        <Text style={st.sub}>크기는 상관없어. 해낸 걸 적으면 내가 축하해줄게.</Text>
        <View style={st.box}>
          {ITEMS.map((i) => (
            <Pressable key={i.key} accessibilityRole="checkbox" accessibilityState={{ checked: !!ok[i.key] }}
              onPress={() => setOk((o) => ({ ...o, [i.key]: !o[i.key] }))} style={st.row}>
              <View style={[st.check, ok[i.key] && st.checked]}>{ok[i.key] ? <Icon name="check" size={15} color={C.white} stroke={2.6} /> : null}</View>
              <Text style={st.label}>{i.label}</Text>
            </Pressable>
          ))}
          <Pressable onPress={() => setOk(Object.fromEntries(ITEMS.map((i) => [i.key, !all])))} style={[st.row, { paddingTop: 4 }]}>
            <Text style={st.allText}>{all ? '모두 해제' : '모두 동의'}</Text>
          </Pressable>
        </View>
        <Text style={st.small}>힘든 순간엔 설정 › 도움받을 수 있는 곳에서 상담 번호를 바로 찾을 수 있어요.</Text>
        <Btn title="시작하기" onPress={start} disabled={!all} loading={busy} />
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, padding: 24, maxWidth: 480, width: '100%', alignSelf: 'center' },
  big: { fontSize: 26, fontWeight: '800', color: C.ink, lineHeight: 36 },
  sub: { fontSize: 15, color: C.muted, lineHeight: 22 },
  box: { backgroundColor: C.card, borderRadius: R.card, paddingVertical: 14, paddingHorizontal: 18, gap: 4 },
  row: { flexDirection: 'row', gap: 12, alignItems: 'flex-start', paddingVertical: 8 },
  check: { width: 24, height: 24, borderRadius: R.pill, backgroundColor: C.soft, alignItems: 'center', justifyContent: 'center' },
  checked: { backgroundColor: C.accent },
  label: { flex: 1, fontSize: 14, color: C.ink, lineHeight: 22 },
  allText: { fontSize: 13, color: C.accentInk, fontWeight: '700' },
  small: { fontSize: 12, color: C.muted, lineHeight: 18 },
});
