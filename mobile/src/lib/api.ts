import { supabase } from './supabase';
import type { Category } from './categories';

export type Win = {
  id: string;
  text: string;
  category: Category;
  category_source: 'auto' | 'llm' | 'user';
  win_date: string;
  created_at: string;
  jar_no: number; // 들어간 유리병 번호 (넣는 순간 고정)
  note: string | null; // 크게 보기에서 덧붙인 한 줄 (C9 N2, 원문은 그대로)
  starred: boolean; // ☆ 다시 보고 싶은 기록 (C9 M3, 보상 차등 없음)
};
export type WinCounts = { cats: Partial<Record<Category, number>>; starred: number };
// 목록 화면 하나가 쓰는 필터: 분류 하나 또는 ☆ (C9 N3)
export type ListFilter = Category | 'star';
export const LIST_PAGE = 100;
export type JarInfo = { no: number; count: number; from: string; to: string; cats: Partial<Record<Category, number>> };
export type JarSummary = { current_jar: number; total: number; jars: JarInfo[] };
export type Profile = {
  id: string;
  pet_name: string;
  notify_enabled: boolean;
  notify_time: string; // 'HH:MM:SS'
  consented_at: string | null;
  sensitive_consented_at?: string | null;
  onboarded_at: string | null;
  first_crop_used: boolean;
};
export type Item = {
  id: string; name: string; emoji: string; price: number; sort: number;
  space: 'room' | 'yard'; slot: string; layer: 'back' | 'mid' | 'front';
};
export type Owned = { item_id: string; placed: boolean };
export type Crop = { id: string; name: string; emoji: string; kind: 'flower' | 'edible'; price: number; deco_name: string; deco_emoji: string; sort: number };
export type Plot = { slot: number; crop_id: string; planted_day: string; required_days: number; days: number };
export const FIRST_CROP = 'sweet_potato';
// 마당: 열림(기록한 날 누적 7일, 영구) · 전체 기록한 날(추억 나무) · 산 구역(2, 3) · 테스터(테스트 스위치)
export type YardState = { open: boolean; record_days: number; zones: number[]; tester: boolean; dev_open: boolean };
export type MemoryCard = { id: string; text: string; category: Category; win_date: string; kind: 'month' | 'past' };
export const ZONE_PRICE: Record<number, number> = { 2: 60, 3: 120 };

// 텃밭 단계: 0 심음(흙더미) · 1 싹 · 2 자람 · 3 다 자람. 기록한 날 3일마다 한 단계, 첫 작물은 1일에 바로 다 자람
export function plotStage(p: Plot): { stage: 0 | 1 | 2 | 3; dots: number } {
  if (p.days >= p.required_days) return { stage: 3, dots: 3 };
  if (p.required_days <= 1) return { stage: 0, dots: 0 };
  const stage = Math.min(2, Math.floor(p.days / 3)) as 0 | 1 | 2;
  return { stage, dots: p.days % 3 };
}

const ERR_KO: Record<string, string> = {
  daily_limit: '오늘은 충분히 많이 적었어. 내일 또 들려줘!',
  not_ready: '아직 자라는 중이야.',
  slot_taken: '이미 심은 칸이야.',
  empty_bag: '바구니가 비었어.',
  not_enough_seeds: '씨앗이 조금 모자라. 기록하면 씨앗이 생겨!',
  already_owned: '이미 방에 있어.',
  invalid_date: '오늘이나 어제 일만 적을 수 있어.',
  yard_locked: '마당이 열리면 살 수 있어.',
  forbidden: '테스트 계정에서만 쓸 수 있어.',
  too_long: '한 줄은 200자까지 남길 수 있어.',
};
export function friendlyError(e: unknown) {
  const msg = (e as { message?: string })?.message ?? String(e);
  const key = Object.keys(ERR_KO).find((k) => msg.includes(k));
  return key ? ERR_KO[key] : '잠깐 연결이 안 됐어. 다시 해볼래?';
}

export const newestFirst = (a: Win, b: Win) =>
  a.win_date !== b.win_date ? (a.win_date < b.win_date ? 1 : -1) : a.created_at < b.created_at ? 1 : -1;

async function rpc<T>(fn: string, args: Record<string, unknown> = {}): Promise<T> {
  const { data, error } = await supabase.rpc(fn, args);
  if (error) throw error;
  return data as T;
}

export const api = {
  recordWin: (text: string, category: Category, source: 'auto' | 'llm' | 'user', winDate: string) =>
    rpc<{ win: Win; earned: number; balance: number; first: boolean; sealed: boolean }>('record_win', {
      p_text: text, p_category: category, p_source: source, p_win_date: winDate,
    }),
  editWin: (id: string, text: string, category: Category) => rpc<Win>('edit_win', { p_id: id, p_text: text, p_category: category }),
  deleteWin: async (id: string) => {
    const { error } = await supabase.from('wins').delete().eq('id', id);
    if (error) throw error;
  },
  balance: () => rpc<number>('seed_balance'),
  jarSummary: () => rpc<JarSummary>('jar_summary'),
  jarWins: async (no: number) => {
    const { data, error } = await supabase.from('wins').select('*').eq('jar_no', no).order('created_at', { ascending: false });
    if (error) throw error;
    return data as Win[];
  },
  // 글자로 찾기 (최근 것부터 100개). 기록 글 + 덧붙인 메모 둘 다 (C9 N2: 메모도 찾기에 포함)
  // or() 필터는 쉼표·괄호가 든 검색어에서 깨지므로 두 번 찾아서 합친다
  searchWins: async (q: string) => {
    const pat = `%${q.replace(/[\\%_]/g, (c) => '\\' + c)}%`;
    const one = (col: 'text' | 'note') => supabase.from('wins').select('*').ilike(col, pat)
      .order('win_date', { ascending: false }).order('created_at', { ascending: false }).limit(100);
    const [a, b] = await Promise.all([one('text'), one('note')]);
    if (a.error) throw a.error;
    if (b.error) throw b.error;
    const m = new Map<string, Win>();
    [...(a.data as Win[]), ...(b.data as Win[])].forEach((w) => m.set(w.id, w));
    return [...m.values()].sort(newestFirst).slice(0, 100);
  },
  // 목록 화면 (분류 하나 / ☆): 최근 것부터 LIST_PAGE개씩
  listWins: async (f: ListFilter, page: number) => {
    let qy = supabase.from('wins').select('*');
    qy = f === 'star' ? qy.eq('starred', true) : qy.eq('category', f);
    const { data, error } = await qy.order('win_date', { ascending: false }).order('created_at', { ascending: false })
      .range(page * LIST_PAGE, page * LIST_PAGE + LIST_PAGE - 1);
    if (error) throw error;
    return data as Win[];
  },
  // 하루 한 장: 그날 기록 + 기록이 있는 바로 앞·뒤 날 (빈 날은 건너뜀)
  dayWins: async (d: string) => {
    const [w, prev, next] = await Promise.all([
      supabase.from('wins').select('*').eq('win_date', d).order('created_at'),
      supabase.from('wins').select('win_date').lt('win_date', d).order('win_date', { ascending: false }).limit(1),
      supabase.from('wins').select('win_date').gt('win_date', d).order('win_date').limit(1),
    ]);
    if (w.error) throw w.error;
    return {
      wins: w.data as Win[],
      prev: (prev.data?.[0]?.win_date as string | undefined) ?? null,
      next: (next.data?.[0]?.win_date as string | undefined) ?? null,
    };
  },
  winCounts: () => rpc<WinCounts>('win_counts'),
  setNote: (id: string, note: string) => rpc<Win>('set_win_note', { p_id: id, p_note: note }),
  setStar: (id: string, on: boolean) => rpc<Win>('set_win_star', { p_id: id, p_on: on }),
  // 내보내기용 전체 기록 (1,000개씩 나눠 받기)
  allWins: async () => {
    const out: Win[] = [];
    for (let from = 0; ; from += 1000) {
      const { data, error } = await supabase.from('wins').select('*').order('created_at').range(from, from + 999);
      if (error) throw error;
      out.push(...(data as Win[]));
      if (data.length < 1000) return out;
    }
  },
  gift: () => rpc<number>('grant_onboarding_gift'),
  buy: (itemId: string) => rpc<number>('buy_item', { p_item_id: itemId }),
  deleteAllWins: () => rpc<void>('delete_all_wins'),
  placeItem: (itemId: string) => rpc<void>('place_item', { p_item_id: itemId }),
  gardenState: () => rpc<Plot[]>('garden_state'),
  plant: (slot: number, cropId: string) => rpc<number>('plant', { p_slot: slot, p_crop: cropId }),
  harvest: (slot: number) => rpc<{ crop_id: string; first_unlock: boolean }>('harvest', { p_slot: slot }),
  useHarvest: (cropId: string) => rpc<number>('use_harvest', { p_crop: cropId }),
  touchSeen: () => rpc<string | null>('touch_seen'),
  yardState: () => rpc<YardState>('yard_state'),
  buyZone: (zone: number) => rpc<number>('buy_zone', { p_zone: zone }),
  memoryCard: (seen: string[]) => rpc<MemoryCard | null>('memory_card', { p_seen: seen }),
  devYard: (open: boolean) => rpc<void>('dev_yard', { p_open: open }),
  devAllZones: () => rpc<void>('dev_all_zones'),
  devSeeds: () => rpc<number>('dev_seeds'),
  deleteAccount: () => rpc<void>('delete_my_account'),

  async classify(text: string): Promise<{ category: Category; self_harm: boolean; harm_others?: boolean } | null> {
    try {
      const timeout = new Promise<null>((r) => setTimeout(() => r(null), 5000));
      const call = supabase.functions.invoke('classify', { body: { text } }).then(({ data, error }) =>
        error || !data?.category ? null : (data as { category: Category; self_harm: boolean; harm_others?: boolean }),
      );
      return await Promise.race([call, timeout]);
    } catch {
      return null;
    }
  },

  // 익명 집계: 누가 감지됐는지는 남기지 않고 날짜·출처별 횟수만 (safety_daily)
  async logSafety(source: 'keyword' | 'llm') {
    await supabase.rpc('log_safety', { p_source: source });
  },
};
