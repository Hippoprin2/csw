import * as AppleAuthentication from 'expo-apple-authentication';
import { makeRedirectUri } from 'expo-auth-session';
import * as Crypto from 'expo-crypto';
import * as WebBrowser from 'expo-web-browser';
import { Platform } from 'react-native';

import { track } from './analytics';
import { supabase } from './supabase';

WebBrowser.maybeCompleteAuthSession(); // 웹 팝업 마무리용

// 이메일 링크용: csw://auth/callback (개발 빌드·스토어) / exp://…/--/auth/callback (Expo Go)
export const redirectTo = makeRedirectUri({ scheme: 'csw', path: 'auth/callback' });
// OAuth용: 항상 csw:// 고정. Supabase는 사설 IP(exp://192.168.x.x) 리다이렉트를 거부하고 site_url로 보내 버린다.
// iOS 인증 창(ASWebAuthenticationSession)은 csw:// 이동을 가로채 앱에 돌려주므로 Expo Go에서도 동작.
const OAUTH_REDIRECT = 'csw://auth/callback';

// OAuth·이메일 링크에서 돌아온 URL → 세션
export async function sessionFromUrl(url: string) {
  const params: Record<string, string> = {};
  for (const part of [url.split('#')[1], url.split('#')[0].split('?')[1]]) {
    if (part) new URLSearchParams(part).forEach((v, k) => { params[k] = v; });
  }
  if (params.error) throw new Error(params.error_description || params.error);
  if (params.code) {
    const { error } = await supabase.auth.exchangeCodeForSession(params.code);
    if (error) throw error;
    return true;
  }
  if (!params.access_token) return false;
  const { error } = await supabase.auth.setSession({ access_token: params.access_token, refresh_token: params.refresh_token });
  if (error) throw error;
  return true;
}

// 카카오·구글: 브라우저 OAuth (Expo Go에서도 동작)
export async function signInWithProvider(provider: 'kakao' | 'google') {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider,
    options: {
      redirectTo: OAUTH_REDIRECT,
      skipBrowserRedirect: true,
      // 카카오: Supabase가 account_email·profile_image·profile_nickname을 항상 요청 → 카카오 동의항목 3개 모두 설정 필요(안 하면 KOE205)
      queryParams: provider === 'google' ? { prompt: 'select_account' } : undefined,
    },
  });
  if (error) throw error;
  const res = await WebBrowser.openAuthSessionAsync(data.url, OAUTH_REDIRECT);
  if (res.type !== 'success') return false;
  const ok = await sessionFromUrl(res.url);
  if (ok) track('signed_in', { method: provider });
  return ok;
}

// Apple: iOS 네이티브 (App Store 규정상 iOS에서는 네이티브 사용). Expo Go에서도 테스트 가능.
export async function appleAvailable() {
  return Platform.OS === 'ios' && (await AppleAuthentication.isAvailableAsync());
}

export async function signInWithApple() {
  const rawNonce = Crypto.randomUUID();
  const hashed = await Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256, rawNonce);
  try {
    const cred = await AppleAuthentication.signInAsync({
      requestedScopes: [AppleAuthentication.AppleAuthenticationScope.EMAIL],
      nonce: hashed,
    });
    if (!cred.identityToken) throw new Error('no_identity_token');
    const { error } = await supabase.auth.signInWithIdToken({ provider: 'apple', token: cred.identityToken, nonce: rawNonce });
    if (error) throw error;
    track('signed_in', { method: 'apple' });
    return true;
  } catch (e) {
    if ((e as { code?: string }).code === 'ERR_REQUEST_CANCELED') return false;
    throw e;
  }
}
