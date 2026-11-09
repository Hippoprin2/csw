import 'expo-sqlite/localStorage/install';
import { createClient } from '@supabase/supabase-js';
import aesjs from 'aes-js';
import * as Crypto from 'expo-crypto';
import * as SecureStore from 'expo-secure-store';

// 로그인 정보(세션) 저장: 내용은 AES-256으로 암호화해 앱 저장공간(localStorage)에, 열쇠는 기기 보안 저장소(iOS 키체인)에.
// SecureStore는 값 크기 제한(약 2KB)이 있어 세션 전체를 넣을 수 없음 → Supabase 공식 예시(LargeSecureStore) 방식.
// 쓸 때마다 새 열쇠를 만든다 (CTR 모드에서 열쇠·카운터 재사용 방지).
const secureKey = (k: string) => k.replace(/[^A-Za-z0-9._-]/g, '_');

const encryptedStorage = {
  async getItem(key: string): Promise<string | null> {
    const stored = localStorage.getItem(key);
    if (!stored) return null;
    const hexKey = await SecureStore.getItemAsync(secureKey(key));
    if (!hexKey) {
      // 이전 버전이 평문으로 저장한 세션 → 한 번 읽고 암호화해서 다시 저장 (로그아웃 없이 전환)
      if (stored.startsWith('{')) {
        await encryptedStorage.setItem(key, stored);
        return stored;
      }
      return null;
    }
    const cipher = new aesjs.ModeOfOperation.ctr(aesjs.utils.hex.toBytes(hexKey), new aesjs.Counter(1));
    return aesjs.utils.utf8.fromBytes(cipher.decrypt(aesjs.utils.hex.toBytes(stored)));
  },
  async setItem(key: string, value: string) {
    const k = Crypto.getRandomBytes(32);
    const cipher = new aesjs.ModeOfOperation.ctr(k, new aesjs.Counter(1));
    const encrypted = cipher.encrypt(aesjs.utils.utf8.toBytes(value));
    await SecureStore.setItemAsync(secureKey(key), aesjs.utils.hex.fromBytes(k), {
      keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY, // 백그라운드 토큰 갱신 허용, 백업으로 다른 기기에 안 넘어감
    });
    localStorage.setItem(key, aesjs.utils.hex.fromBytes(encrypted));
  },
  async removeItem(key: string) {
    localStorage.removeItem(key);
    await SecureStore.deleteItemAsync(secureKey(key));
  },
};

export const supabase = createClient(
  process.env.EXPO_PUBLIC_SUPABASE_URL!,
  process.env.EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
  {
    auth: { storage: encryptedStorage, autoRefreshToken: true, persistSession: true, detectSessionInUrl: false },
  },
);
