import { supabase } from './supabase';

// S9 이용 분석. 기록 본문은 절대 넣지 않는다 (카테고리·개수 같은 메타만).
export type EventName =
  | 'app_open' | 'signed_in' | 'onboarding_done' | 'win_recorded' | 'win_edited' | 'win_deleted'
  | 'item_bought' | 'item_placed' | 'notif_prompt' | 'safety_shown' | 'export_done' | 'weekly_viewed'
  | 'planted' | 'harvested' | 'harvest_used' | 'garden_woke' | 'space_viewed'
  | 'jar_sealed' | 'jar_viewed'
  | 'yard_zone_bought' | 'memory_fruit'
  | 'win_viewed' | 'win_note_saved' | 'win_starred' | 'records_list_viewed' | 'day_viewed' | 'marble_swiped';

export function track(name: EventName, props: Record<string, string | number | boolean> = {}) {
  supabase.auth.getSession().then(({ data }) => {
    const uid = data.session?.user.id;
    if (!uid) return;
    supabase.from('app_events').insert({ user_id: uid, name, props }).then(() => {});
  });
}
