-- 보안 정리: Supabase 기본 권한(authenticated에 테이블 ALL)이 남아 있어 profiles의 모든 열을 본인이 고칠 수 있었다
-- (예: first_crop_used를 false로 되돌려 무료 작물 반복). RLS가 막는 테이블도 권한 자체를 최소로 다시 준다.
revoke all on public.profiles, public.wins, public.seed_ledger, public.items, public.owned_items,
  public.safety_events, public.app_events, public.crops, public.plots, public.harvest_bag, public.harvest_unlocks
  from authenticated;

grant select on public.profiles to authenticated;
grant update (pet_name, notify_enabled, notify_time, consented_at, onboarded_at) on public.profiles to authenticated;
grant select, delete on public.wins to authenticated;
grant select on public.seed_ledger, public.items, public.owned_items, public.crops, public.plots,
  public.harvest_bag, public.harvest_unlocks to authenticated;
grant insert (user_id, source) on public.safety_events to authenticated;
grant insert (user_id, name, props) on public.app_events to authenticated;
