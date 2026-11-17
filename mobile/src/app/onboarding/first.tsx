import { router, useIsFocused } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { track } from '@/lib/analytics';
import type { Category } from '@/lib/categories';
import { RoomPage } from '@/screens/RoomPage';
import { useApp } from '@/state/app';
import { Sheet, st as sheetSt } from '@/ui/Sheet';
import { SignInButtons } from '@/ui/SignInButtons';
import { C } from '@/ui/theme';

// ④ 첫 기록 → ⑤ 축하 + 씨앗 → ⑥ 가입 시트 (2026-11-17 첫 실행 순서 변경, design/onboarding sheet2·3 O6-A)
// ④⑤는 홈 무대(RoomPage firstRun)를 그대로 씀 — 기록·분류·자해 감지 경로가 RoomPage submit과 같음.
// ⑥은 필수('나중에' 없음). 가입 안 하고 앱을 닫으면 다음 실행 때 여기로 와서 바로 ⑥ (첫 기록은 익명 계정에 남아 있음)
const CELEBRATE_MS = 3600; // 축하 동작·'+3 씨앗'을 보고 나서 시트
const SAFETY_MS = 7000; // 자해 감지(곁에 앉기 + 말풍선)면 더 오래 기다림

// 무료 끝 날짜: 가입한 날 + 14일 (서버 trial_ends_at = 연결 시각 + 14일을 그날 24시 KST로 올림 → 이 날짜 끝까지)
function trialEndLabel() {
  const d = new Date(Date.now() + 14 * 86400000 + 9 * 3600000); // KST
  return `${d.getUTCMonth() + 1}월 ${d.getUTCDate()}일`;
}

// 이름 끝 받침에 따라 이/가
function withJosa(name: string) {
  const c = name.charCodeAt(name.length - 1);
  const batchim = c >= 0xac00 && c <= 0xd7a3 && (c - 0xac00) % 28 !== 0;
  return name + (batchim ? '이' : '가');
}

export default function FirstWin() {
  const { wins, profile } = useApp();
  const focused = useIsFocused(); // 이메일 화면으로 가면 시트(Modal)를 내림 — 안 내리면 새 화면 위에 남음
  const [had] = useState(() => wins.length > 0); // 들어올 때 이미 첫 기록이 있음 = 앱을 닫았다 다시 연 것 → 바로 ⑥
  const [done, setDone] = useState(had);
  const [signup, setSignup] = useState(had);
  const shownLogged = useRef(false);

  useEffect(() => {
    if (signup && !shownLogged.current) {
      shownLogged.current = true;
      track('ob_signup_shown', { resumed: had });
    }
  }, [signup, had]);

  function onWin(category: Category, unsafe: boolean) {
    track('ob_first_win', category === 'endure' ? {} : { category });
    setDone(true);
    setTimeout(() => setSignup(true), unsafe ? SAFETY_MS : CELEBRATE_MS);
  }

  return (
    <View style={{ flex: 1, backgroundColor: C.bg }}>
      <RoomPage firstRun={{ onWin, done }} />
      <Sheet visible={signup && focused} onClose={() => {}} locked>
        <View style={st.head}>
          <Text style={[sheetSt.title, { marginBottom: 0 }]}>첫 기록, 잘 간직할게</Text>
        </View>
        <Text style={sheetSt.body}>계정을 연결하면 폰을 바꿔도 기록이랑 {withJosa(profile?.pet_name ?? '단짝')} 그대로 남아.</Text>
        <SignInButtons onEmail={() => router.push('/auth/email')} />
        <Text style={st.trial}>
          <Text style={st.trialStrong}>{trialEndLabel()}까지 무료</Text> · 카드 등록 없음{'\n'}그 뒤엔 월 3,000원 또는 연 24,000원 · 그때 골라도 돼
        </Text>
      </Sheet>
    </View>
  );
}

const st = StyleSheet.create({
  head: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  trial: { fontSize: 12, color: C.muted, textAlign: 'center', lineHeight: 18, marginTop: 12 },
  trialStrong: { fontWeight: '800', color: C.ink },
});
