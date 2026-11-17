import { Stack } from 'expo-router';

import { C } from '@/ui/theme';

// ① 인사·'이미 계정이 있어요'·이메일·OAuth 콜백. 루트 가드가 정식 계정이면 이 그룹을 닫음.
// 익명(가입 전)도 열려 있음: ⑥ 가입 시트에서 이메일 화면·콜백을 써서. ①은 세션이 있으면 스스로 ② 이름으로 넘김(index.tsx)
export default function AuthLayout() {
  return <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: C.bg } }} />;
}
