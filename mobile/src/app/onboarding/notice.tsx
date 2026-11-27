import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '@/lib/api';
import { openLegal } from '@/lib/legal';
import { track } from '@/lib/analytics';
import { JOINED_KEY } from '@/lib/auth';
import { store } from '@/lib/store';
import { useApp } from '@/state/app';
import { Icon } from '@/ui/Icon';
import { Btn } from '@/ui/kit';
import { C, R } from '@/ui/theme';

// 한 줄 안내 + 고지·동의 1화면 (FEATURES 3장, D4). 모두 필수.
// 2026-11-27 대표 결정: 민감정보 별도 동의(J4)와 '상담 앱 아님' 체크를 뺌 — 상담 아님 고지는 약관 제2조 2항·제11조 3항과 도움 화면에 있음.
// 개인정보 줄의 OpenAI 한 줄은 남김: Apple 심사 지침 5.1.2(i)(제3자 AI로 개인 데이터를 보낼 때 앱 안에서 알리고 동의받기).
type Item = { key: string; label: string; detail?: string; doc?: 'terms' | 'privacy' };
const ALL: Item[] = [
  { key: 'age', label: '만 14세 이상이에요' },
  { key: 'terms', label: '[필수] 이용약관에 동의해요', doc: 'terms' },
  { key: 'privacy', label: '[필수] 개인정보 수집·이용에 동의해요', doc: 'privacy',
    detail: '분류를 위해 기록 한 줄만 이름 없이 OpenAI(미국)로 보내요.' },
];

export default function Notice() {
  const { refresh, anonymous } = useApp();
  const [ok, setOk] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);
  const all = ALL.every((i) => ok[i.key]);

  const toggle = (k: string) => setOk((o) => ({ ...o, [k]: !o[k] }));

  async function start() {
    setBusy(true);
    try {
      if (anonymous) {
        // 가입 전(익명): 동의만 저장하고 ④ 첫 기록으로. 선물 씨앗 6개·무료 기간·온보딩 완료는 ⑥ 가입(연결) 때 서버가 (2026-11-17)
        await api.consent(); // 동의 칸은 서버 함수로만 (동의한 판도 저장, 2026-11-18)
        await refresh();
        track('ob_consent_done');
        router.replace('/onboarding/first');
        return;
      }
      // 정식 계정인데 온보딩 전 = '이미 계정이 있어요'에서 처음 만든 계정 → 선물 받고 바로 방 (⑦ 선물 말풍선·⑧ 알림 시트)
      await api.gift(); // 온보딩 선물 씨앗 6개 → 첫날 첫 소품 구매 가능
      await api.consent(true);
      track('ob_consent_done');
      store.set(JOINED_KEY, '1');
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
          {ALL.map((i) => <Check key={i.key} item={i} on={!!ok[i.key]} toggle={() => toggle(i.key)} />)}
        </View>
        <Pressable onPress={() => setOk(Object.fromEntries(ALL.map((i) => [i.key, !all])))} style={st.allBtn} accessibilityRole="button">
          <Text style={st.allText}>{all ? '모두 해제' : '모두 동의'}</Text>
        </Pressable>
        <Text style={st.small}>힘든 순간엔 설정 › 도움받을 수 있는 곳에서 상담 번호를 바로 찾을 수 있어요.</Text>
        <Btn title="시작하기" onPress={start} disabled={!all} loading={busy} />
      </ScrollView>
    </SafeAreaView>
  );
}

function Check({ item, on, toggle }: { item: Item; on: boolean; toggle: () => void }) {
  return (
    <View style={st.row}>
      <Pressable accessibilityRole="checkbox" accessibilityState={{ checked: on }} onPress={toggle} style={st.rowMain}>
        <View style={[st.check, on && st.checked]}>{on ? <Icon name="check" size={15} color={C.white} stroke={2.6} /> : null}</View>
        <View style={{ flex: 1, gap: 2 }}>
          <Text style={st.label}>{item.label}</Text>
          {item.detail ? <Text style={st.detail}>{item.detail}</Text> : null}
        </View>
      </Pressable>
      {item.doc ? (
        <Pressable onPress={() => openLegal(item.doc!)} hitSlop={8} accessibilityRole="link">
          <Text style={st.view}>보기</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, padding: 24, maxWidth: 480, width: '100%', alignSelf: 'center' },
  big: { fontSize: 26, fontWeight: '800', color: C.ink, lineHeight: 36 },
  sub: { fontSize: 15, color: C.muted, lineHeight: 22 },
  box: { backgroundColor: C.card, borderRadius: R.card, paddingVertical: 14, paddingHorizontal: 18, gap: 4 },
  row: { flexDirection: 'row', gap: 8, alignItems: 'flex-start', paddingVertical: 8 },
  rowMain: { flex: 1, flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
  detail: { fontSize: 12, color: C.muted, lineHeight: 18 },
  view: { fontSize: 13, color: C.accentInk, fontWeight: '700', textDecorationLine: 'underline', paddingTop: 2 },
  allBtn: { alignSelf: 'flex-start', paddingVertical: 4, paddingHorizontal: 4 },
  check: { width: 24, height: 24, borderRadius: R.pill, backgroundColor: C.soft, alignItems: 'center', justifyContent: 'center' },
  checked: { backgroundColor: C.accent },
  label: { flex: 1, fontSize: 14, color: C.ink, lineHeight: 22 },
  allText: { fontSize: 13, color: C.accentInk, fontWeight: '700' },
  small: { fontSize: 12, color: C.muted, lineHeight: 18 },
});
