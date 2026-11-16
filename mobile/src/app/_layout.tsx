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
  const { ready, session, profile } = useApp();
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
  const signedIn = !!session;
  const onboarded = !!profile?.onboarded_at;
  return (
    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: C.bg } }}>
      <Stack.Protected guard={!signedIn}>
        <Stack.Screen name="auth" />
      </Stack.Protected>
      <Stack.Protected guard={signedIn && !onboarded}>
        <Stack.Screen name="onboarding" />
      </Stack.Protected>
      <Stack.Protected guard={signedIn && onboarded}>
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
