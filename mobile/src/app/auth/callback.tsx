import { useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Text, View } from 'react-native';
import * as Linking from 'expo-linking';

import { sessionFromUrl } from '@/lib/auth';
import { C } from '@/ui/theme';

// csw://auth/callback — 이메일 로그인 링크·OAuth가 앱으로 돌아오는 곳.
// 세션이 생기면 루트 가드가 온보딩/방으로 보낸다.
export default function AuthCallback() {
  const params = useLocalSearchParams();
  const url = Linking.useLinkingURL();
  const [err, setErr] = useState('');

  useEffect(() => {
    if (!url) return;
    const fail = () => setErr('링크가 만료됐거나 이미 쓰였어. 다시 시도해줘.');
    sessionFromUrl(url).then((ok) => { if (!ok) fail(); }).catch(fail);
  }, [url, params]);

  return (
    <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: C.bg, padding: 24 }}>
      {err ? <Text style={{ color: C.ink, textAlign: 'center' }}>{err}</Text> : <ActivityIndicator color={C.accent} />}
    </View>
  );
}
