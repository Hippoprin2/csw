import { supabase } from './supabase';
import type { Category } from './categories';

export type Win = {
  id: string;
  text: string;
  category: Category;
  category_source: 'auto' | 'llm' | 'user';
  win_date: string;
  created_at: string;
};
export type Profile = {
  id: string;
  pet_name: string;
  notify_enabled: boolean;
  notify_time: string; // 'HH:MM:SS'
  consented_at: string | null;
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
};
export function friendlyError(e: unknown) {
  const msg = (e as { message?: string })?.message ?? String(e);
  const key = Object.keys(ERR_KO).find((k) => msg.includes(k));
  return key ? ERR_KO[key] : '잠깐 연결이 안 됐어. 다시 해볼래?';
}

async function rpc<T>(fn: string, args: Record<string, unknown> = {}): Promise<T> {
  const { data, error } = await supabase.rpc(fn, args);
  if (error) throw error;
  return data as T;
}

export const api = {
  recordWin: (text: string, category: Category, source: 'auto' | 'llm' | 'user', winDate: string) =>
    rpc<{ win: Win; earned: number; balance: number; first: boolean }>('record_win', {
      p_text: text, p_category: category, p_source: source, p_win_date: winDate,
    }),
  editWin: (id: string, text: string, category: Category) => rpc<Win>('edit_win', { p_id: id, p_text: text, p_category: category }),
  deleteWin: async (id: string) => {
    const { error } = await supabase.from('wins').delete().eq('id', id);
    if (error) throw error;
  },
  balance: () => rpc<number>('seed_balance'),
  gift: () => rpc<number>('grant_onboarding_gift'),
  buy: (itemId: string) => rpc<number>('buy_item', { p_item_id: itemId }),
  deleteAllWins: () => rpc<void>('delete_all_wins'),
  placeItem: (itemId: string) => rpc<void>('place_item', { p_item_id: itemId }),
  gardenState: () => rpc<Plot[]>('garden_state'),
  plant: (slot: number, cropId: string) => rpc<number>('plant', { p_slot: slot, p_crop: cropId }),
  harvest: (slot: number) => rpc<{ crop_id: string; first_unlock: boolean }>('harvest', { p_slot: slot }),
  useHarvest: (cropId: string) => rpc<number>('use_harvest', { p_crop: cropId }),
  touchSeen: () => rpc<string | null>('touch_seen'),
  deleteAccount: () => rpc<void>('delete_my_account'),

  async classify(text: string): Promise<{ category: Category; self_harm: boolean } | null> {
    try {
      const timeout = new Promise<null>((r) => setTimeout(() => r(null), 5000));
      const call = supabase.functions.invoke('classify', { body: { text } }).then(({ data, error }) =>
        error || !data?.category ? null : (data as { category: Category; self_harm: boolean }),
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
