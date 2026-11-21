// 이름 끝 받침에 따라 조사 고르기 ('단단' → '단단이', '보리' → '보리가'). 한글이 아니면 받침 없음으로
export function hasBatchim(name: string) {
  const c = name.trim().charCodeAt(name.trim().length - 1);
  return c >= 0xac00 && c <= 0xd7a3 && (c - 0xac00) % 28 !== 0;
}
export const iGa = (name: string) => name + (hasBatchim(name) ? '이' : '가');
