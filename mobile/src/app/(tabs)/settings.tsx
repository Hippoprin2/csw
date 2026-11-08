import { router } from 'expo-router';
import { useState } from 'react';
import { Linking, Platform, Pressable, ScrollView, Share, StyleSheet, Switch, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api, friendlyError } from '@/lib/api';
import { track } from '@/lib/analytics';
import { CATS } from '@/lib/categories';
import { askPermission } from '@/lib/notifications';
import { useApp } from '@/state/app';
import { Btn, H } from '@/ui/kit';
import { Confirm, Sheet, st as sheetSt } from '@/ui/Sheet';
import { C, R } from '@/ui/theme';

const PRIVACY_URL = process.env.EXPO_PUBLIC_PRIVACY_URL;
const TERMS_URL = process.env.EXPO_PUBLIC_TERMS_URL;
const CONTACT = process.env.EXPO_PUBLIC_CONTACT_EMAIL;
const HOURS = Array.from({ length: 17 }, (_, i) => `${String(i + 7).padStart(2, '0')}:00`); // 07~23시

function Row({ label, onPress, right, danger }: { label: string; onPress?: () => void; right?: React.ReactNode; danger?: boolean }) {
  return (
    <Pressable onPress={onPress} disabled={!onPress} style={st.row} accessibilityRole={onPress ? 'button' : undefined}>
      <Text style={[st.rowText, danger && { color: '#c0392b' }]}>{label}</Text>
      {right ?? (onPress ? <Text style={st.chev}>›</Text> : null)}
    </Pressable>
  );
}

export default function Settings() {
  const { profile, updateProfile, wins, setWins, signOut, session } = useApp();
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
    const lines = [...wins].reverse().map((w) => `${w.win_date} · ${w.text} · ${CATS[w.category].name}`);
    const message = `나의 작은 승리 기록 (${wins.length}개)\n\n${lines.join('\n')}`;
    try {
      await Share.share({ message });
      track('export_done', { count: wins.length });
    } catch (e) { setMsg(friendlyError(e)); }
  }

  async function deleteAllWins() {
    try {
      await api.deleteAllWins();
      setWins([]);
      setStep(null);
      setMsg('기록을 모두 지웠어. 펫과 방, 씨앗은 그대로야.');
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
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
        <H>설정</H>
        {msg ? <Text style={st.msg}>{msg}</Text> : null}

        <Text style={st.sec}>펫</Text>
        <View style={st.group}>
          <Row label={`이름: ${profile?.pet_name ?? ''}`} onPress={() => { setName(profile?.pet_name ?? ''); setNameEdit(true); }} />
        </View>

        <Text style={st.sec}>알림</Text>
        <View style={st.group}>
          <Row label="하루 한 번 물어보기" right={<Switch value={!!profile?.notify_enabled} onValueChange={toggleNotify} trackColor={{ true: C.accent }} />} />
          {profile?.notify_enabled ? <Row label={`시간: ${time}`} onPress={() => setTimeEdit(true)} /> : null}
        </View>

        <Text style={st.sec}>내 기록</Text>
        <View style={st.group}>
          <Row label="텍스트로 내보내기" onPress={exportAll} />
          <Row label="모든 기록 지우기" onPress={() => setStep('wins1')} danger />
        </View>

        <Text style={st.sec}>도움 · 정보</Text>
        <View style={st.group}>
          <Row label="도움받을 수 있는 곳" onPress={() => router.push('/help')} />
          <Row label="개인정보처리방침" onPress={() => open(PRIVACY_URL)} />
          <Row label="이용약관" onPress={() => open(TERMS_URL)} />
          <Row label="문의하기" onPress={() => open(CONTACT ? `mailto:${CONTACT}` : undefined)} />
        </View>

        <Text style={st.sec}>계정</Text>
        <View style={st.group}>
          <Row label={session?.user.email ?? '로그인됨'} />
          <Row label="로그아웃" onPress={signOut} />
          <Row label="계정 삭제" onPress={() => setStep('acct1')} danger />
        </View>
      </ScrollView>

      <Sheet visible={nameEdit} onClose={() => setNameEdit(false)}>
        <Text style={sheetSt.title}>펫 이름 바꾸기</Text>
        <TextInput style={st.input} value={name} onChangeText={setName} maxLength={12} accessibilityLabel="펫 이름" />
        <View style={sheetSt.row}>
          <Btn title="취소" kind="ghost" onPress={() => setNameEdit(false)} style={{ flex: 1 }} />
          <Btn title="저장" disabled={!name.trim()} onPress={async () => { await updateProfile({ pet_name: name.trim() }); setNameEdit(false); }} style={{ flex: 1 }} />
        </View>
      </Sheet>

      <Sheet visible={timeEdit} onClose={() => setTimeEdit(false)}>
        <Text style={sheetSt.title}>몇 시에 물어볼까?</Text>
        <View style={st.hours}>
          {HOURS.map((h) => (
            <Pressable key={h} onPress={async () => { await updateProfile({ notify_time: `${h}:00` }); setTimeEdit(false); }}
              style={[st.hour, h === time && { borderColor: C.accent, backgroundColor: '#fff' }]}>
              <Text style={{ color: C.ink, fontSize: 13 }}>{h}</Text>
            </Pressable>
          ))}
        </View>
      </Sheet>

      <Confirm visible={step === 'wins1'} title="모든 기록을 지울까?" body="유리병의 기록이 모두 사라져. 펫과 방, 씨앗은 그대로 남아." confirm="다음" danger
        onConfirm={() => setStep('wins2')} onCancel={() => setStep(null)} />
      <Confirm visible={step === 'wins2'} title="정말 지울까?" body="지운 기록은 되돌릴 수 없어. 먼저 내보내기로 저장해둘 수 있어." confirm="모두 지우기" danger
        onConfirm={deleteAllWins} onCancel={() => setStep(null)} />
      <Confirm visible={step === 'acct1'} title="계정을 삭제할까?" body="기록, 펫, 방, 씨앗이 모두 바로 삭제돼." confirm="다음" danger
        onConfirm={() => setStep('acct2')} onCancel={() => setStep(null)} />
      <Confirm visible={step === 'acct2'} title="정말 삭제할까?" body="삭제하면 되돌릴 수 없어. 백업에 남은 사본은 보관 기간이 지나면 사라져." confirm="계정 삭제" danger
        onConfirm={deleteAccount} onCancel={() => setStep(null)} />
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, maxWidth: 520, width: '100%', alignSelf: 'center' },
  sec: { fontSize: 12, color: C.muted, fontWeight: '700', marginTop: 18, marginBottom: 6, marginLeft: 4 },
  group: { backgroundColor: '#fff', borderRadius: R.card, borderWidth: 1, borderColor: C.line, overflow: 'hidden' },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 14, paddingHorizontal: 16, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: C.line, minHeight: 50 },
  rowText: { fontSize: 15, color: C.ink, flex: 1 },
  chev: { fontSize: 20, color: C.muted },
  msg: { backgroundColor: '#fff', borderRadius: 12, padding: 12, fontSize: 13, color: C.ink, marginTop: 8, borderWidth: 1, borderColor: C.line },
  input: { fontSize: 16, padding: 12, borderRadius: R.input, borderWidth: 1.5, borderColor: C.line, backgroundColor: '#fff', color: C.ink, marginBottom: 12 },
  hours: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  hour: { paddingVertical: 8, paddingHorizontal: 12, borderRadius: R.pill, borderWidth: 1, borderColor: C.line, backgroundColor: C.room },
});
