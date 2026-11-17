import * as AppleAuthentication from 'expo-apple-authentication';
import { makeRedirectUri } from 'expo-auth-session';
import * as Crypto from 'expo-crypto';
import * as Device from 'expo-device';
import * as WebBrowser from 'expo-web-browser';
import { Platform } from 'react-native';

import { track } from './analytics';
import { store } from './store';
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
  if (params.error) {
    // 웹: 가입(익명 → 정식 연결) 중 고른 카카오·구글이 이미 다른 계정 → 그 계정으로 로그인하고 첫 기록을 옮김 (claimPending)
    if (Platform.OS === 'web' && isAlreadyLinked(params.error_code, params.error_description) && store.get(LINK_PROVIDER_KEY)) {
      const provider = store.get(LINK_PROVIDER_KEY) as Provider;
      store.set(LINK_PROVIDER_KEY, '');
      await signInWithProvider(provider);
      return true;
    }
    throw new Error(params.error_description || params.error);
  }
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

type Provider = 'kakao' | 'google';
export type SignInMethod = 'apple' | Provider | 'email';

// ── 가입 = 익명 계정 → 정식 연결 (2026-11-17 첫 실행 순서 변경, O5-A)
// ⑥ 가입 시트에서 고른 방법을 지금 익명 계정에 '연결'(linkIdentity / updateUser email). 기록·이름·동의가 같은 계정에 그대로 남음.
// 그 방법이 이미 다른 계정이면(예전에 가입한 사람) 연결 대신 그 계정으로 로그인 → AppProvider가 claimPending()으로
// 익명 계정의 첫 기록을 그 계정으로 옮김(서버 함수 claim-anon, 익명 토큰으로 소유 확인) → 익명 계정 삭제.
const PENDING_CLAIM_KEY = 'csw.pendingClaim'; // 옮길 익명 계정의 access token (로그인 직전에 저장)
const LINK_PROVIDER_KEY = 'csw.linkProvider'; // 웹: 연결하러 떠난 OAuth (돌아와서 '이미 있는 계정'이면 로그인으로)
const LINK_UID_KEY = 'csw.linkUid'; // 웹: 연결하러 떠난 익명 계정 id (돌아오면 페이지가 새로 떠서 '방금 연결됨'을 이걸로 앎)
export const wasLinkingOnWeb = (uid: string) => store.get(LINK_UID_KEY) === uid;
export const JOINED_KEY = 'csw.joined'; // 방금 가입 → 방에서 선물 말풍선 + 알림 시트 1장 (⑦·⑧)

export async function currentAnonSession() {
  const { data } = await supabase.auth.getSession();
  return data.session?.user.is_anonymous ? data.session : null;
}

function isAlreadyLinked(code?: string, msg?: string) {
  return code === 'identity_already_exists' || code === 'email_exists' || code === 'user_already_exists'
    || /already (been )?(linked|registered)|already exists/i.test(msg ?? '');
}
const errCode = (e: unknown) => (e as { code?: string })?.code;
const errMsg = (e: unknown) => (e as { message?: string })?.message;
export const alreadyLinked = (e: unknown) => isAlreadyLinked(errCode(e), errMsg(e));

async function savePendingClaim() {
  const anon = await currentAnonSession();
  if (anon) store.set(PENDING_CLAIM_KEY, anon.access_token);
}
export const hasPendingClaim = () => !!store.get(PENDING_CLAIM_KEY);

// 정식 계정으로 로그인한 직후 AppProvider가 부름. 옮겼으면 { moved, target_new } (target_new = 막 만든 계정 → 가입과 같게 선물·무료)
export async function claimPending(): Promise<{ moved: number; target_new: boolean } | null> {
  const anonToken = store.get(PENDING_CLAIM_KEY);
  if (!anonToken) return null;
  store.set(PENDING_CLAIM_KEY, '');
  const { data, error } = await supabase.functions.invoke('claim-anon', { body: { anon_token: anonToken } });
  if (error) return null; // 못 옮긴 익명 계정은 7일 뒤 자동 삭제
  return data as { moved: number; target_new: boolean };
}

// 카카오·구글: 브라우저 OAuth (Expo Go에서도 동작). 익명 세션이면 연결, 아니면 로그인
export async function signInWithProvider(provider: Provider) {
  const anon = await currentAnonSession();
  if (Platform.OS === 'web') {
    // 웹 테스트판(Vercel): 같은 창에서 카카오로 갔다가 <origin>/auth/callback?code= 로 돌아옴 → callback.tsx가 세션 교환.
    // Supabase uri_allow_list에 그 origin이 있어야 함 (scripts/deploy_web_app.py가 등록).
    const options = {
      redirectTo: `${window.location.origin}/auth/callback`,
      queryParams: provider === 'google' ? { prompt: 'select_account' } : undefined,
    };
    if (anon) {
      store.set(LINK_PROVIDER_KEY, provider);
      store.set(LINK_UID_KEY, anon.user.id);
      store.set(PENDING_CLAIM_KEY, anon.access_token); // 이미 있는 계정이면 돌아와서 로그인 → 옮김. 연결되면 AppProvider가 지움
      const { error } = await supabase.auth.linkIdentity({ provider, options });
      if (error) throw error;
      return false;
    }
    const { error } = await supabase.auth.signInWithOAuth({ provider, options });
    if (error) throw error;
    return false; // 페이지가 이동하므로 여기서 끝
  }
  const options = {
    redirectTo: OAUTH_REDIRECT,
    skipBrowserRedirect: true,
    // 카카오: Supabase가 account_email·profile_image·profile_nickname을 항상 요청 → 카카오 동의항목 3개 모두 설정 필요(안 하면 KOE205)
    queryParams: provider === 'google' ? { prompt: 'select_account' } : undefined,
  };
  if (anon) {
    const { data, error } = await supabase.auth.linkIdentity({ provider, options });
    if (error) throw error;
    const res = await WebBrowser.openAuthSessionAsync(data.url, OAUTH_REDIRECT);
    if (res.type !== 'success') return false;
    try {
      const ok = await sessionFromUrl(res.url);
      if (ok) track('signed_in', { method: provider, linked: true });
      return ok;
    } catch (e) {
      if (!alreadyLinked(e) && !/already/i.test(String(res.url))) throw e;
      await savePendingClaim(); // 이미 있는 계정 → 그 계정으로 로그인 (아래), 첫 기록은 옮김
    }
  }
  const { data, error } = await supabase.auth.signInWithOAuth({ provider, options });
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
    const token = { provider: 'apple' as const, token: cred.identityToken, nonce: rawNonce };
    if (await currentAnonSession()) {
      // 익명 계정에 Apple 연결 (signInWithIdToken 대신 linkIdentity + id_token). 이미 있는 Apple 계정이면 그 계정으로 로그인 → 옮김
      const { error } = await supabase.auth.linkIdentity(token);
      if (!error) { track('signed_in', { method: 'apple', linked: true }); return true; }
      if (!alreadyLinked(error)) throw error;
      await savePendingClaim();
    }
    const { error } = await supabase.auth.signInWithIdToken(token);
    if (error) throw error;
    track('signed_in', { method: 'apple' });
    return true;
  } catch (e) {
    if ((e as { code?: string }).code === 'ERR_REQUEST_CANCELED') return false;
    throw e;
  }
}

// 이메일: 익명이면 updateUser(email) → 새 주소로 온 6자리(email_change)로 연결. 이미 가입한 주소면 일반 로그인 코드(email)로
export async function sendEmailCode(email: string): Promise<'link' | 'login'> {
  if (await currentAnonSession()) {
    const { error } = await supabase.auth.updateUser({ email }, { emailRedirectTo: redirectTo });
    if (!error) return 'link';
    if (!alreadyLinked(error)) throw error;
    await savePendingClaim();
  }
  const { error } = await supabase.auth.signInWithOtp({ email, options: { shouldCreateUser: true, emailRedirectTo: redirectTo } });
  if (error) throw error;
  return 'login';
}

export async function verifyEmailCode(email: string, token: string, mode: 'link' | 'login') {
  const { error } = await supabase.auth.verifyOtp({ email, token, type: mode === 'link' ? 'email_change' : 'email' });
  if (error) throw error;
  track('signed_in', { method: 'email', ...(mode === 'link' ? { linked: true } : {}) });
}

// ① '시작하기': 익명 계정으로 바로 시작 (가입은 첫 기록 축하 뒤 ⑥)
export async function startAnonymous() {
  const { error } = await supabase.auth.signInAnonymously();
  if (error) throw error;
  track('ob_start');
}

export function clearLinkState() {
  store.set(LINK_PROVIDER_KEY, '');
  store.set(LINK_UID_KEY, '');
  store.set(PENDING_CLAIM_KEY, '');
}
