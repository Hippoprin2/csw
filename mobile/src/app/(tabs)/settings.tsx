import { router } from 'expo-router';
import { useState } from 'react';
import { Linking, Platform, Pressable, ScrollView, Share, StyleSheet, Switch, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api, friendlyError } from '@/lib/api';
import { track } from '@/lib/analytics';
import { CATS } from '@/lib/categories';
import { askPermission } from '@/lib/notifications';
import { useApp } from '@/state/app';
import { Icon } from '@/ui/Icon';
import { Btn, H } from '@/ui/kit';
import { Confirm, Sheet, st as sheetSt } from '@/ui/Sheet';
import { openLegal } from '@/lib/legal';
import { C, H as HT, R, TAB_SPACE } from '@/ui/theme';

// 스토어 구독 관리 (계정을 지워도 스토어 구독은 따로 해지해야 결제가 멈춤 — 2026-11-18 B3)
const SUBSCRIPTIONS_URL = Platform.OS === 'android'
  ? 'https://play.google.com/store/account/subscriptions'
  : 'https://apps.apple.com/account/subscriptions';

const CONTACT = process.env.EXPO_PUBLIC_CONTACT_EMAIL;
const HOURS = Array.from({ length: 17 }, (_, i) => `${String(i + 7).padStart(2, '0')}:00`); // 07~23시

// 묶음별 흰 카드 (테두리 없이 바탕과의 면 색 차이로 구분). 줄 사이는 옅은 면 색 한 줄
function Group({ children }: { children: React.ReactNode }) {
  const rows = (Array.isArray(children) ? children : [children]).filter(Boolean);
  return (
    <View style={st.group}>
      {rows.map((r, i) => (
        <View key={i}>
          {i > 0 && <View style={st.divider} />}
          {r}
        </View>
      ))}
    </View>
  );
}

function Row({ label, onPress, right, danger }: { label: string; onPress?: () => void; right?: React.ReactNode; danger?: boolean }) {
  return (
    <Pressable onPress={onPress} disabled={!onPress} style={st.row} accessibilityRole={onPress ? 'button' : undefined}>
      <Text style={[st.rowText, danger && { color: C.danger, fontWeight: '700' }]}>{label}</Text>
      {right ?? (onPress && !danger ? <Icon name="chevronRight" size={18} color={C.muted} /> : null)}
    </Pressable>
  );
}

export default function Settings() {
  const { profile, updateProfile, setWins, reloadJars, signOut, session } = useApp();
  const [nameEdit, setNameEdit] = useState(false);
  const [name, setName] = useState(profile?.pet_name ?? '');
  const [timeEdit, setTimeEdit] = useState(false);
  const [step, setStep] = useState<null | 'wins1' | 'wins2' | 'acct1' | 'acct2'>(null);
  const [msg, setMsg] = useState('');

  const time = profile?.notify_time.slice(0, 5) ?? '21:00';

  async function toggleNotify(v: boolean) {
    setMsg('');
    if (v && Platform.OS !== 'web') {
      const ok = await askPermission();
      if (!ok) { setMsg('휴대폰 설정에서 알림을 허용해줘야 보낼 수 있어.'); return; }
    }
    await updateProfile({ notify_enabled: v });
  }

  async function exportAll() {
    try {
      const all = await api.allWins();
      // 덧붙인 한 줄(C9 N2)은 다음 줄에 '  └ ', ☆는 끝에
      const lines = all.map((w) => `${w.win_date} · ${w.text} · ${CATS[w.category].name}${w.starred ? ' · ☆' : ''}${w.note ? `\n  └ ${w.note}` : ''}`);
      const message = `나의 작은 승리 기록 (${all.length}개)\n\n${lines.join('\n')}`;
      await Share.share({ message });
      track('export_done', { count: all.length });
    } catch (e) { setMsg(friendlyError(e)); }
  }

  async function deleteAllWins() {
    try {
      await api.deleteAllWins();
      setWins([]);
      reloadJars().catch(() => {});
      setStep(null);
      setMsg('기록을 모두 지웠어. 단짝과 방, 씨앗은 그대로야.');
    } catch (e) { setMsg(friendlyError(e)); setStep(null); }
  }

  async function deleteAccount() {
    try {
      await api.deleteAccount();
      setStep(null);
      await signOut();
    } catch (e) { setMsg(friendlyError(e)); setStep(null); }
  }

  const open = (url?: string) => (url ? Linking.openURL(url) : setMsg('준비 중이야.'));

  return (
    <SafeAreaView style={st.wrap} edges={['top']}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: TAB_SPACE + 16 }}>
        <H>설정</H>
        {msg ? <Text style={st.msg}>{msg}</Text> : null}

        <Text style={st.sec}>단짝</Text>
        <Group>
          <Row label={`이름: ${profile?.pet_name ?? ''}`} onPress={() => { setName(profile?.pet_name ?? ''); setNameEdit(true); }} />
        </Group>

        <Text style={st.sec}>알림</Text>
        <Group>
          <Row label="하루 한 번 물어보기" right={<Switch value={!!profile?.notify_enabled} onValueChange={toggleNotify} trackColor={{ true: C.accent, false: C.track }} thumbColor={C.white} />} />
          {profile?.notify_enabled ? <Row label={`시간: ${time}`} onPress={() => setTimeEdit(true)} /> : null}
        </Group>

        <Text style={st.sec}>내 기록</Text>
        <Group>
          <Row label="텍스트로 내보내기" onPress={exportAll} />
          <Row label="모든 기록 지우기" onPress={() => setStep('wins1')} danger />
        </Group>

        <Text style={st.sec}>도움 · 정보</Text>
        <Group>
          <Row label="도움받을 수 있는 곳" onPress={() => router.push('/help')} />
          <Row label="개인정보처리방침" onPress={() => openLegal('privacy')} />
          <Row label="이용약관" onPress={() => openLegal('terms')} />
          <Row label="문의하기" onPress={() => open(CONTACT ? `mailto:${CONTACT}` : undefined)} />
        </Group>

        <Text style={st.sec}>계정</Text>
        <Group>
          <Row label={session?.user.email ?? '로그인됨'} />
          <Row label="로그아웃" onPress={signOut} />
          <Row label="계정 삭제" onPress={() => setStep('acct1')} />
        </Group>
      </ScrollView>

      <Sheet visible={nameEdit} onClose={() => setNameEdit(false)}>
        <Text style={sheetSt.title}>단짝 이름 바꾸기</Text>
        <TextInput style={st.input} value={name} onChangeText={setName} maxLength={12} accessibilityLabel="단짝 이름" />
        <View style={sheetSt.col}>
          <Btn title="저장" disabled={!name.trim()} onPress={async () => { await updateProfile({ pet_name: name.trim() }); setNameEdit(false); }} />
          <Btn title="취소" kind="ghost" onPress={() => setNameEdit(false)} />
        </View>
      </Sheet>

      <Sheet visible={timeEdit} onClose={() => setTimeEdit(false)}>
        <Text style={sheetSt.title}>몇 시에 물어볼까?</Text>
        <View style={st.hours}>
          {HOURS.map((h) => (
            <Pressable key={h} onPress={async () => { await updateProfile({ notify_time: `${h}:00` }); setTimeEdit(false); }}
              style={[st.hour, h === time && { backgroundColor: C.accentBg }]} accessibilityState={{ selected: h === time }}>
              <Text style={{ color: h === time ? C.accentInk : C.ink, fontSize: 13, fontWeight: h === time ? '700' : '400' }}>{h}</Text>
            </Pressable>
          ))}
        </View>
      </Sheet>

      <Confirm visible={step === 'wins1'} title="모든 기록을 지울까?" body="유리병의 기록이 모두 사라져. 단짝과 방, 씨앗은 그대로 남아." confirm="다음" danger
        onConfirm={() => setStep('wins2')} onCancel={() => setStep(null)} />
      <Confirm visible={step === 'wins2'} title="정말 지울까?" body="지운 기록은 되돌릴 수 없어. 먼저 내보내기로 저장해둘 수 있어." confirm="모두 지우기" danger
        onConfirm={deleteAllWins} onCancel={() => setStep(null)} />
      <Confirm visible={step === 'acct1'} title="계정을 삭제할까?" body={"기록, 단짝, 방, 씨앗이 모두 바로 삭제돼.\n구독 중이라면 계정을 지워도 결제는 멈추지 않아. 구독 관리에서 먼저 해지해 줘."} confirm="다음" danger
        link={{ title: '구독 관리 열기', onPress: () => Linking.openURL(SUBSCRIPTIONS_URL) }}
        onConfirm={() => setStep('acct2')} onCancel={() => setStep(null)} />
      <Confirm visible={step === 'acct2'} title="정말 삭제할까?" body="삭제하면 되돌릴 수 없어. 백업에 남은 사본은 보관 기간이 지나면 사라져." confirm="계정 삭제" danger
        onConfirm={deleteAccount} onCancel={() => setStep(null)} />
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, maxWidth: 520, width: '100%', alignSelf: 'center' },
  sec: { fontSize: 13, color: C.muted, fontWeight: '700', marginTop: 22, marginBottom: 8, marginLeft: 6 },
  group: { backgroundColor: C.card, borderRadius: R.card, overflow: 'hidden' },
  divider: { height: 1, backgroundColor: C.divider, marginHorizontal: 18 },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 14, paddingHorizontal: 18, minHeight: 54 },
  rowText: { fontSize: 15, color: C.ink, flex: 1 },
  msg: { backgroundColor: C.soft, borderRadius: R.card, paddingVertical: 14, paddingHorizontal: 18, fontSize: 13, color: C.ink, marginTop: 8, overflow: 'hidden' },
  input: { fontSize: 16, height: HT.input, paddingHorizontal: 22, borderRadius: R.pill, backgroundColor: C.card, color: C.ink, marginBottom: 12 },
  hours: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 8 },
  hour: { height: HT.chip, justifyContent: 'center', paddingHorizontal: 14, borderRadius: R.pill, backgroundColor: C.soft },
});
