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

// 한 줄 안내 + 고지·동의 1화면 (FEATURES 3장, D4)
// 민감정보는 다른 동의와 나눠 따로 받는다 (J4, 처리방침 2장). 모두 필수.
type Item = { key: string; label: string; detail?: string; doc?: 'terms' | 'privacy' };
const ITEMS: Item[] = [
  { key: 'age', label: '만 14세 이상이에요' },
  { key: 'notCounsel', label: '이 앱은 상담·치료 서비스가 아니라는 걸 알아요' },
  { key: 'terms', label: '[필수] 이용약관에 동의해요', doc: 'terms' },
  { key: 'privacy', label: '[필수] 개인정보 수집·이용에 동의해요', doc: 'privacy',
    detail: '받는 정보: 로그인 이메일, 기록·메모, 단짝·공간 진행, 알림 설정. 기록을 분류하려고 기록 한 줄만 이름 없이 OpenAI(미국)로 보내요.' },
];
const SENSITIVE: Item = {
  key: 'sensitive', label: '[필수] 민감정보 처리에 동의해요', doc: 'privacy',
  detail: '기록에 건강이나 마음 상태를 써도 괜찮아요. 그 내용도 저장·분류·안전 안내에만 쓰고, 분류를 위해 기록 한 줄이 OpenAI(미국)로 전송돼요. 다른 목적으로 쓰지 않아요.',
};
const ALL = [...ITEMS, SENSITIVE];

export default function Notice() {
  const { updateProfile, refresh, anonymous } = useApp();
  const [ok, setOk] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);
  const all = ALL.every((i) => ok[i.key]);

  const toggle = (k: string) => setOk((o) => ({ ...o, [k]: !o[k] }));

  async function start() {
    setBusy(true);
    try {
      const now = new Date().toISOString();
      if (anonymous) {
        // 가입 전(익명): 동의만 저장하고 ④ 첫 기록으로. 선물 씨앗 6개·무료 기간·온보딩 완료는 ⑥ 가입(연결) 때 서버가 (2026-11-17)
        await updateProfile({ consented_at: now, sensitive_consented_at: now });
        track('ob_consent_done');
        router.replace('/onboarding/first');
        return;
      }
      // 정식 계정인데 온보딩 전 = '이미 계정이 있어요'에서 처음 만든 계정 → 선물 받고 바로 방 (⑦ 선물 말풍선·⑧ 알림 시트)
      await api.gift(); // 온보딩 선물 씨앗 6개 → 첫날 첫 소품 구매 가능
      await updateProfile({ consented_at: now, sensitive_consented_at: now, onboarded_at: now });
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
          {ITEMS.map((i) => <Check key={i.key} item={i} on={!!ok[i.key]} toggle={() => toggle(i.key)} />)}
        </View>
        <View style={st.box}>
          <Check item={SENSITIVE} on={!!ok.sensitive} toggle={() => toggle('sensitive')} />
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
