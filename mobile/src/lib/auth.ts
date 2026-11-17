import * as AppleAuthentication from 'expo-apple-authentication';
import { makeRedirectUri } from 'expo-auth-session';
import * as Crypto from 'expo-crypto';
import * as Device from 'expo-device';
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
  // 시뮬레이터 테스트 로그인 (개발 전용): EXPO_PUBLIC_SIM_TEST=1로 빌드한 앱 + 시뮬레이터(실기기 아님)에서만.
  // scripts/sim_login.py가 테스트 계정 refresh_token을 csw://auth/callback?sim_refresh=… 로 넘김. 스토어 빌드엔 이 값이 없어 꺼짐
  if (process.env.EXPO_PUBLIC_SIM_TEST === '1' && !Device.isDevice && params.sim_refresh) {
    const { error } = await supabase.auth.refreshSession({ refresh_token: params.sim_refresh });
    if (error) throw error;
    return true;
  }
  // code만 받는다(PKCE). 이 기기가 로그인을 시작할 때 만든 검증값이 있어야 교환되므로,
  // 남이 만든 링크로는 세션이 바뀌지 않는다. 링크에 실린 access_token은 일부러 무시한다.
  if (!params.code) return false;
  const { error } = await supabase.auth.exchangeCodeForSession(params.code);
  if (error) throw error;
  return true;
}

// 카카오·구글: 브라우저 OAuth (Expo Go에서도 동작)
export async function signInWithProvider(provider: 'kakao' | 'google') {
  if (Platform.OS === 'web') {
    // 웹 테스트판(Vercel): 같은 창에서 카카오로 갔다가 <origin>/auth/callback?code= 로 돌아옴 → callback.tsx가 세션 교환.
    // Supabase uri_allow_list에 그 origin이 있어야 함 (scripts/deploy_web_app.py가 등록).
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
        queryParams: provider === 'google' ? { prompt: 'select_account' } : undefined,
      },
    });
    if (error) throw error;
    return false; // 페이지가 이동하므로 여기서 끝
  }
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
