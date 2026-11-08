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
};
export type Item = { id: string; name: string; emoji: string; price: number; sort: number };

const ERR_KO: Record<string, string> = {
  daily_limit: '오늘은 충분히 많이 적었어. 내일 또 들려줘!',
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

  async logSafety(userId: string, source: 'keyword' | 'llm') {
    await supabase.from('safety_events').insert({ user_id: userId, source });
  },
};
