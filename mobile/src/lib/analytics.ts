import { supabase } from './supabase';

// S9 이용 분석. 기록 본문은 절대 넣지 않는다 (카테고리·개수 같은 메타만).
export type EventName =
  | 'app_open' | 'signed_in' | 'onboarding_done' | 'win_recorded' | 'win_edited' | 'win_deleted'
  | 'item_bought' | 'notif_prompt' | 'safety_shown' | 'export_done' | 'weekly_viewed';

export function track(name: EventName, props: Record<string, string | number | boolean> = {}) {
  supabase.auth.getSession().then(({ data }) => {
    const uid = data.session?.user.id;
    if (!uid) return;
    supabase.from('app_events').insert({ user_id: uid, name, props }).then(() => {});
  });
}
