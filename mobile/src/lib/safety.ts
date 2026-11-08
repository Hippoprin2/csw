import keywords from '@/data/safety-keywords.json';

// 1차 감지: 기기 안 키워드 (즉시·오프라인). 공백 무시하고 비교.
const KW: string[] = keywords;
export function safetyKeywordHit(text: string) {
  const t = text.replace(/\s+/g, '');
  return KW.some((k) => t.includes(k));
}

export const HELP_LINES = [
  { name: '자살예방상담전화', number: '109', note: '24시간' },
  { name: '정신건강상담', number: '1577-0199', note: '24시간' },
  { name: '청소년상담', number: '1388', note: '24시간' },
  { name: '위급할 때', number: '112', note: '경찰 · 119 구급' },
];
