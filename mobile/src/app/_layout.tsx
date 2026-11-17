import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

import '@/lib/webViewport'; // 웹: html·body 화면 고정 (사파리 위 잘림)
import { AppProvider, useApp } from '@/state/app';
import { C } from '@/ui/theme';
import { WinSheetProvider } from '@/ui/WinSheet';

SplashScreen.preventAutoHideAsync();

function Gate() {
  const { ready, session, anonymous, profile } = useApp();
  useEffect(() => {
    if (ready) SplashScreen.hideAsync();
  }, [ready]);

  if (!ready) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: C.bg }}>
        <ActivityIndicator color={C.accent} />
      </View>
    );
  }
  // 첫 실행 순서 (2026-11-17, design/onboarding/README.md): 세션 없음 → ① 인사(auth) / 익명 → ②이름 ③동의 ④첫 기록 ⑤축하 ⑥가입(onboarding)
  // / 정식 + 온보딩 끝 → 탭. 정식인데 온보딩 전(‘이미 계정이 있어요’로 처음 만든 계정) → ②③ 뒤 바로 방
  // auth 그룹은 익명에게도 열어 둠: ⑥에서 이메일 화면·OAuth 콜백(auth/callback)을 써야 해서 (그룹 안에서 화면별로 막음)
  const member = !!session && !anonymous;
  const onboarded = member && !!profile?.onboarded_at;
  return (
    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: C.bg } }}>
      <Stack.Protected guard={!!session && !onboarded}>
        <Stack.Screen name="onboarding" />
      </Stack.Protected>
      <Stack.Protected guard={!member}>
        <Stack.Screen name="auth" />
      </Stack.Protected>
      <Stack.Protected guard={onboarded}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="help" options={{ presentation: 'modal' }} />
        <Stack.Screen name="jar/[no]" />
        <Stack.Screen name="jar/search" />
        <Stack.Screen name="jar/list/[f]" />
        <Stack.Screen name="jar/day/[d]" />
      </Stack.Protected>
      <Stack.Screen name="legal/[doc]" options={{ presentation: 'modal' }} />
    </Stack>
  );
}

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <AppProvider>
        <StatusBar style="dark" />
        {/* 기록 '크게 보기' 시트: 방·유리병·목록 어디서든 같은 시트 (C9) */}
        <WinSheetProvider>
          <Gate />
        </WinSheetProvider>
      </AppProvider>
    </GestureHandlerRootView>
  );
}
