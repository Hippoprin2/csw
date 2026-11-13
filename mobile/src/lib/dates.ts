// 날짜는 KST 기준 (서버 kst_today()와 같게)
const KST = 9 * 3600 * 1000;
export const kstDate = (offsetDays = 0) => new Date(Date.now() + KST + offsetDays * 86400000).toISOString().slice(0, 10);
export const kstToday = () => kstDate(0);
export const kstYesterday = () => kstDate(-1);

const DOW = ['일', '월', '화', '수', '목', '금', '토'];
export function formatDay(d: string) {
  if (d === kstToday()) return '오늘';
  if (d === kstYesterday()) return '어제';
  const dt = new Date(d + 'T00:00:00Z');
  // 올해가 아니면 연도도 (지난 병·검색 결과는 해를 넘김)
  const year = d.slice(0, 4) === kstToday().slice(0, 4) ? '' : `${d.slice(0, 4)}년 `;
  return `${year}${dt.getUTCMonth() + 1}월 ${dt.getUTCDate()}일 (${DOW[dt.getUTCDay()]})`;
}

export function todayLabel() {
  const dt = new Date(kstToday() + 'T00:00:00Z');
  return `${dt.getUTCMonth() + 1}월 ${dt.getUTCDate()}일 ${DOW[dt.getUTCDay()]}요일`;
}

// 기록한 시각 (KST): '오후 7:12'
export function formatTime(iso: string) {
  const dt = new Date(Date.parse(iso) + KST);
  const h = dt.getUTCHours(), m = dt.getUTCMinutes();
  return `${h < 12 ? '오전' : '오후'} ${h % 12 === 0 ? 12 : h % 12}:${String(m).padStart(2, '0')}`;
}

// 하루 한 장 제목: '11월 10일 월요일' (올해가 아니면 연도도)
export function longDay(d: string) {
  const dt = new Date(d + 'T00:00:00Z');
  const year = d.slice(0, 4) === kstToday().slice(0, 4) ? '' : `${d.slice(0, 4)}년 `;
  return `${year}${dt.getUTCMonth() + 1}월 ${dt.getUTCDate()}일 ${DOW[dt.getUTCDay()]}요일`;
}

// 목록 오른쪽 짧은 날짜: '11/10' (올해가 아니면 '25/11/10')
export function shortDay(d: string) {
  const [y, m, dd] = d.split('-');
  return `${y === kstToday().slice(0, 4) ? '' : y.slice(2) + '/'}${Number(m)}/${Number(dd)}`;
}

// 월요일 시작 주. 반환: 그 주 월요일 'YYYY-MM-DD'
export function weekStart(d: string) {
  const dt = new Date(d + 'T00:00:00Z');
  const back = (dt.getUTCDay() + 6) % 7;
  dt.setUTCDate(dt.getUTCDate() - back);
  return dt.toISOString().slice(0, 10);
}

export function addDays(d: string, n: number) {
  const dt = new Date(d + 'T00:00:00Z');
  dt.setUTCDate(dt.getUTCDate() + n);
  return dt.toISOString().slice(0, 10);
}
