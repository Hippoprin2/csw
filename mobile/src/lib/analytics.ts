import { supabase } from './supabase';

// S9 이용 분석. 익명(가입 전) 세션도 user_id = 익명 계정 id로 저장됨 (RLS: 본인 행 insert). 기록 본문은 절대 넣지 않는다 (카테고리·개수 같은 메타만).
export type EventName =
  | 'app_open' | 'signed_in' | 'onboarding_done' | 'win_recorded' | 'win_edited' | 'win_deleted'
  | 'item_bought' | 'item_placed' | 'notif_prompt' | 'export_done' | 'weekly_viewed'
  | 'planted' | 'harvested' | 'harvest_used' | 'garden_woke' | 'space_viewed'
  | 'jar_sealed' | 'jar_viewed'
  | 'yard_zone_bought' | 'memory_fruit' | 'pet_tapped'
  | 'win_viewed' | 'win_note_saved' | 'win_starred' | 'records_list_viewed' | 'day_viewed' | 'marble_swiped'
  // 첫 실행 단계 (O4, 2026-11-17). 가입 전 단계는 익명 계정(O5-A)으로 저장 — 익명 계정 7일 삭제 때 개수만 anon_funnel_daily에 남김
  | 'ob_start' | 'ob_name_done' | 'ob_consent_done' | 'ob_first_win' | 'ob_signup_shown';

export function track(name: EventName, props: Record<string, string | number | boolean> = {}) {
  supabase.auth.getSession().then(({ data }) => {
    const uid = data.session?.user.id;
    if (!uid) return;
    supabase.from('app_events').insert({ user_id: uid, name, props }).then(() => {});
  });
}
