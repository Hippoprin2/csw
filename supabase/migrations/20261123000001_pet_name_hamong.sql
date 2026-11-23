-- 캐릭터 이름 하몽 확정(2026-11-23, 대표) → 기본 단짝 이름 '꼬마하마' → '하몽'
alter table public.profiles alter column pet_name set default '하몽';
-- 출시 전: 기본값 그대로 둔 계정만 새 기본 이름으로 (직접 지은 이름은 그대로)
update public.profiles set pet_name = '하몽' where pet_name = '꼬마하마';

-- claim_anon_data: 기본 이름 판정에 '하몽'(새 기본)과 '꼬마하마'(옛 기본) 둘 다
create or replace function public.claim_anon_data(p_anon uuid, p_target uuid)
returns json language plpgsql security definer set search_path = public, auth as $$
declare
  a_anon boolean; t_anon boolean;
  ap public.profiles; tp public.profiles;
  target_new boolean; with_seeds boolean; w record; n int; moved int := 0;
begin
  select is_anonymous into a_anon from auth.users where id = p_anon;
  select is_anonymous into t_anon from auth.users where id = p_target;
  if a_anon is distinct from true then raise exception 'not_anonymous'; end if;
  if t_anon is null or t_anon or p_anon = p_target then raise exception 'bad_target'; end if;
  select * into ap from public.profiles where id = p_anon;
  select * into tp from public.profiles where id = p_target for update;
  target_new := tp.onboarded_at is null; -- 방금 새로 만든 계정 = 가입과 같게 (선물·무료 안내)
  with_seeds := public.has_access(p_target);

  for w in select id from public.wins where user_id = p_anon order by created_at loop
    update public.profiles set marbles_total = marbles_total + 1 where id = p_target returning marbles_total into n;
    update public.wins set user_id = p_target, jar_no = (n - 1) / 50 + 1 where id = w.id;
    moved := moved + 1;
  end loop;
  -- 기록한 날 수(텃밭·마당)는 seed_ledger 'win' 줄로 셈 → 권한 없는 계정엔 안 옮겨서 우회 이득이 없게. 남은 줄은 익명 계정과 함께 삭제
  if with_seeds then
    update public.seed_ledger set user_id = p_target where user_id = p_anon and reason <> 'onboarding_gift';
  end if;
  update public.app_events set user_id = p_target where user_id = p_anon;

  if target_new then
    update public.profiles
       set pet_name = ap.pet_name,
           consented_at = coalesce(tp.consented_at, ap.consented_at),
           sensitive_consented_at = coalesce(tp.sensitive_consented_at, ap.sensitive_consented_at),
           consent_version = case when tp.consented_at is not null then tp.consent_version else ap.consent_version end,
           onboarded_at = case when coalesce(tp.consented_at, ap.consented_at) is not null then now() end
     where id = p_target;
    if ap.consented_at is not null then
      insert into public.seed_ledger (user_id, delta, reason) values (p_target, 6, 'onboarding_gift') on conflict do nothing;
    end if;
  elsif ap.pet_name not in ('하몽', '꼬마하마') and tp.pet_name in ('하몽', '꼬마하마') then
    update public.profiles set pet_name = ap.pet_name where id = p_target;
  end if;
  return json_build_object('moved', moved, 'target_new', target_new, 'seeds_moved', with_seeds);
end $$;
revoke execute on function public.claim_anon_data(uuid, uuid) from public, anon, authenticated;
grant execute on function public.claim_anon_data(uuid, uuid) to service_role;

-- ───────── 6) 이용 통계: 가입 안 한 익명 계정이 지워져도 이벤트는 남기고 누구 것인지만 지움 (B1) ─────────
-- FK cascade를 없애고, 계정 삭제 때 지우는 일은 아래 트리거가 함. 7일 정리는 지우기 전에 이벤트의 user_id를 새 무작위 값으로 바꿈
do $$
declare c text;
begin
  for c in select conname from pg_constraint
            where conrelid = 'public.app_events'::regclass and contype = 'f' loop
    execute format('alter table public.app_events drop constraint %I', c);
  end loop;
