import { router } from 'expo-router';
import * as Linking from 'expo-linking';

// 약관·처리방침 열기: 공개 주소(EXPO_PUBLIC_*_URL)가 있으면 그 주소, 없으면 앱 안 화면(/legal/[doc], data/legal.ts)
const URLS = { privacy: process.env.EXPO_PUBLIC_PRIVACY_URL, terms: process.env.EXPO_PUBLIC_TERMS_URL };

export function openLegal(doc: 'privacy' | 'terms') {
  const url = URLS[doc];
  if (url) Linking.openURL(url);
  else router.push(`/legal/${doc}`);
}
