// 기기 안 작은 설정 저장 (안내를 봤는지 등). 네이티브는 expo-sqlite localStorage(supabase.ts에서 설치), 웹은 브라우저 localStorage
export const store = {
  get: (k: string) => { try { return globalThis.localStorage?.getItem(k) ?? null; } catch { return null; } },
  set: (k: string, v: string) => { try { globalThis.localStorage?.setItem(k, v); } catch {} },
};
