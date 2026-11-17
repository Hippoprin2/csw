-- 2026-11-17 첫 실행 순서 변경: 가입을 첫 기록 축하 뒤로 (대표 결정 O1~O6, design/onboarding/README.md)
-- 가입 전 데이터 = Supabase 익명 계정(O5-A). ①에서 '시작하기' → signInAnonymously → ②이름 ③동의 ④첫 기록 ⑤축하 → ⑥가입(익명 → 정식 연결)

-- 1) 14일 무료: 가입(익명 → 정식 연결)한 때부터. 앱은 읽기만 (UPDATE 권한 안 줌)
alter table public.profiles add column if not exists trial_ends_at timestamptz;

-- 정식(가입한) 사용자인지: JWT의 is_anonymous
create or replace function public.is_member() returns boolean
language sql stable set search_path = public as $$
  select auth.uid() is not null and not coalesce((auth.jwt() ->> 'is_anonymous')::boolean, false)
$$;
create or replace function public.require_member() returns void
language plpgsql stable set search_path = public as $$
begin
  if not public.is_member() then raise exception 'signup_required'; end if;
end $$;

-- 처음부터 정식 계정으로 만든 사람('이미 계정이 있어요'로 새로 가입)은 만든 때부터 14일
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, trial_ends_at)
  values (new.id, case when coalesce(new.is_anonymous, false) then null else now() + interval '14 days' end)
  on conflict do nothing;
  return new;
end $$;

-- 익명 → 정식 연결된 순간: 무료 종료일 저장, 동의까지 마쳤으면 온보딩 완료 + 선물 씨앗 6개 (⑦ 방에서 말풍선)
create or replace function public.handle_user_linked()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if coalesce(old.is_anonymous, false) and not coalesce(new.is_anonymous, false) then
    update public.profiles
       set trial_ends_at = coalesce(trial_ends_at, now() + interval '14 days'),
           onboarded_at = case when consented_at is not null then coalesce(onboarded_at, now()) else onboarded_at end
     where id = new.id;
    if exists (select 1 from public.profiles where id = new.id and consented_at is not null) then
      insert into public.seed_ledger (user_id, delta, reason) values (new.id, 6, 'onboarding_gift') on conflict do nothing;
    end if;
  end if;
  return new;
end $$;
revoke execute on function public.handle_user_linked() from public, anon, authenticated;
drop trigger if exists on_auth_user_linked on auth.users;
create trigger on_auth_user_linked after update of is_anonymous on auth.users
  for each row execute function public.handle_user_linked();

-- 2) 익명 계정이 못 하는 것: 구매·심기·수확·꾸미기·테스트 스위치 (기록·분류·선물·삭제는 됨. 내보내기는 앱 화면이 가입 뒤에만 있음)
CREATE OR REPLACE FUNCTION public.buy_item(p_item_id text)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare
  uid uuid := auth.uid();
  it public.items;
  bal int;
begin
  perform public.require_member(); -- 익명(가입 전) 계정은 가입 뒤에 (2026-11-17 첫 실행 순서 변경)
  if uid is null then raise exception 'not_authenticated'; end if;
  perform pg_advisory_xact_lock(hashtext(uid::text));
  select * into it from public.items where id = p_item_id and active;
  if it.id is null then raise exception 'not_found'; end if;
  if it.space = 'yard' and not public.yard_open(uid) then raise exception 'yard_locked'; end if;
  if exists (select 1 from public.owned_items where user_id = uid and item_id = it.id) then raise exception 'already_owned'; end if;
  bal := public.seed_balance();
  if bal < it.price then raise exception 'not_enough_seeds'; end if;
  update public.owned_items o set placed = false from public.items i
   where o.user_id = uid and o.item_id = i.id and i.slot = it.slot;
  insert into public.owned_items (user_id, item_id, placed) values (uid, it.id, true);
  insert into public.seed_ledger (user_id, delta, reason, ref) values (uid, -it.price, 'purchase', it.id);
  return bal - it.price;
end $function$;

CREATE OR REPLACE FUNCTION public.buy_zone(p_zone integer)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare uid uuid := auth.uid(); price int := public.zone_price(p_zone); bal int;
begin
  perform public.require_member(); -- 익명(가입 전) 계정은 가입 뒤에 (2026-11-17 첫 실행 순서 변경)
  if uid is null then raise exception 'not_authenticated'; end if;
  perform pg_advisory_xact_lock(hashtext(uid::text));
  if price is null then raise exception 'not_found'; end if;
  if not public.yard_open(uid) then raise exception 'yard_locked'; end if;
  if exists (select 1 from public.yard_zones where user_id = uid and zone = p_zone) then raise exception 'already_owned'; end if;
  bal := public.seed_balance();
  if bal < price then raise exception 'not_enough_seeds'; end if;
  insert into public.yard_zones (user_id, zone) values (uid, p_zone);
  insert into public.seed_ledger (user_id, delta, reason, ref) values (uid, -price, 'purchase', 'zone:' || p_zone);
  return bal - price;
end $function$;

CREATE OR REPLACE FUNCTION public.plant(p_slot integer, p_crop text)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare
  uid uuid := auth.uid();
  c public.crops;
  first boolean;
  bal int;
begin
  perform public.require_member(); -- 익명(가입 전) 계정은 가입 뒤에 (2026-11-17 첫 실행 순서 변경)
  if uid is null then raise exception 'not_authenticated'; end if;
  perform pg_advisory_xact_lock(hashtext(uid::text));
  if p_slot not between 1 and 3 then raise exception 'invalid_slot'; end if;
  if exists (select 1 from public.plots where user_id = uid and slot = p_slot) then raise exception 'slot_taken'; end if;
  select * into c from public.crops where id = p_crop and active;
  if c.id is null then raise exception 'not_found'; end if;
  select not first_crop_used into first from public.profiles where id = uid;
  bal := public.seed_balance();
  if first then
    if c.id <> 'sweet_potato' then raise exception 'first_crop_sweet_potato'; end if;
    update public.profiles set first_crop_used = true where id = uid;
    insert into public.plots (user_id, slot, crop_id, planted_day, required_days) values (uid, p_slot, c.id, public.kst_today(), 1);
    return bal;
  end if;
  if bal < c.price then raise exception 'not_enough_seeds'; end if;
  insert into public.plots (user_id, slot, crop_id, planted_day, required_days) values (uid, p_slot, c.id, public.kst_today(), 9);
  if c.price > 0 then
    insert into public.seed_ledger (user_id, delta, reason, ref) values (uid, -c.price, 'purchase', 'crop:' || c.id);
  end if;
  return bal - c.price;
end $function$;

CREATE OR REPLACE FUNCTION public.harvest(p_slot integer)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare
  uid uuid := auth.uid();
  p public.plots;
  new_unlock boolean;
begin
  perform public.require_member(); -- 익명(가입 전) 계정은 가입 뒤에 (2026-11-17 첫 실행 순서 변경)
  if uid is null then raise exception 'not_authenticated'; end if;
  select * into p from public.plots where user_id = uid and slot = p_slot for update;
  if p.crop_id is null then raise exception 'empty_slot'; end if;
  if public.record_days_since(uid, p.planted_day) < p.required_days then raise exception 'not_ready'; end if;
  delete from public.plots where user_id = uid and slot = p_slot;
  insert into public.harvest_bag (user_id, crop_id, count) values (uid, p.crop_id, 1)
    on conflict (user_id, crop_id) do update set count = harvest_bag.count + 1;
  insert into public.harvest_unlocks (user_id, crop_id) values (uid, p.crop_id) on conflict do nothing;
  get diagnostics new_unlock = row_count;
  return json_build_object('crop_id', p.crop_id, 'first_unlock', new_unlock);
end $function$;

CREATE OR REPLACE FUNCTION public.use_harvest(p_crop text)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare uid uuid := auth.uid(); n int;
begin
  perform public.require_member(); -- 익명(가입 전) 계정은 가입 뒤에 (2026-11-17 첫 실행 순서 변경)
  update public.harvest_bag set count = count - 1 where user_id = uid and crop_id = p_crop and count > 0 returning count into n;
  if n is null then raise exception 'empty_bag'; end if;
  return n;
end $function$;

CREATE OR REPLACE FUNCTION public.place_item(p_item_id text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare uid uuid := auth.uid(); s text;
begin
  perform public.require_member(); -- 익명(가입 전) 계정은 가입 뒤에 (2026-11-17 첫 실행 순서 변경)
  select i.slot into s from public.items i join public.owned_items o on o.item_id = i.id and o.user_id = uid where i.id = p_item_id;
  if s is null then raise exception 'not_owned'; end if;
  update public.owned_items o set placed = (o.item_id = p_item_id) from public.items i
   where o.user_id = uid and o.item_id = i.id and i.slot = s;
end $function$;

CREATE OR REPLACE FUNCTION public.dev_yard(p_open boolean)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform public.require_member(); -- 익명(가입 전) 계정은 가입 뒤에 (2026-11-17 첫 실행 순서 변경)
  if not public.is_tester() then raise exception 'forbidden'; end if;
  update public.profiles set yard_dev_open = p_open where id = auth.uid();
end $function$;

CREATE OR REPLACE FUNCTION public.dev_all_zones()
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform public.require_member(); -- 익명(가입 전) 계정은 가입 뒤에 (2026-11-17 첫 실행 순서 변경)
  if not public.is_tester() then raise exception 'forbidden'; end if;
  insert into public.yard_zones (user_id, zone) values (auth.uid(), 2), (auth.uid(), 3) on conflict do nothing;
end $function$;

CREATE OR REPLACE FUNCTION public.dev_seeds()
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform public.require_member(); -- 익명(가입 전) 계정은 가입 뒤에 (2026-11-17 첫 실행 순서 변경)
  if not public.is_tester() then raise exception 'forbidden'; end if;
  insert into public.seed_ledger (user_id, delta, reason, ref) values (auth.uid(), 500, 'dev', 'test_switch');
  return public.seed_balance();
end $function$;

-- 3) 이미 있는 계정으로 로그인했을 때: 익명 계정의 첫 기록(+씨앗·이벤트)을 그 계정으로 옮김.
-- 소유 확인은 claim-anon 함수가 익명 토큰으로 함 → 이 함수는 service_role만 부름. 옮긴 뒤 함수가 익명 계정 삭제
create or replace function public.claim_anon_data(p_anon uuid, p_target uuid)
returns json language plpgsql security definer set search_path = public, auth as $$
declare
  a_anon boolean; t_anon boolean;
  ap public.profiles; tp public.profiles;
  target_new boolean; w record; n int; moved int := 0;
begin
  select is_anonymous into a_anon from auth.users where id = p_anon;
  select is_anonymous into t_anon from auth.users where id = p_target;
  if a_anon is distinct from true then raise exception 'not_anonymous'; end if;
  if t_anon is null or t_anon or p_anon = p_target then raise exception 'bad_target'; end if;
  select * into ap from public.profiles where id = p_anon;
  select * into tp from public.profiles where id = p_target for update;
  target_new := tp.onboarded_at is null; -- 방금 새로 만든 계정 = 가입과 같게 (선물·무료 안내)

  for w in select id from public.wins where user_id = p_anon order by created_at loop
    update public.profiles set marbles_total = marbles_total + 1 where id = p_target returning marbles_total into n;
    update public.wins set user_id = p_target, jar_no = (n - 1) / 50 + 1 where id = w.id;
    moved := moved + 1;
  end loop;
  update public.seed_ledger set user_id = p_target where user_id = p_anon and reason <> 'onboarding_gift';
  update public.app_events set user_id = p_target where user_id = p_anon;

  if target_new then
    update public.profiles
       set pet_name = ap.pet_name,
           consented_at = coalesce(tp.consented_at, ap.consented_at),
           sensitive_consented_at = coalesce(tp.sensitive_consented_at, ap.sensitive_consented_at),
           onboarded_at = case when coalesce(tp.consented_at, ap.consented_at) is not null then now() end
     where id = p_target;
    if ap.consented_at is not null then
      insert into public.seed_ledger (user_id, delta, reason) values (p_target, 6, 'onboarding_gift') on conflict do nothing;
    end if;
  elsif ap.pet_name is distinct from '꼬마하마' and tp.pet_name = '꼬마하마' then
    -- 기존 계정은 이름을 지은 적 없을 때만 새 이름으로 (이미 지은 이름은 덮어쓰지 않음)
    update public.profiles set pet_name = ap.pet_name where id = p_target;
  end if;
  return json_build_object('moved', moved, 'target_new', target_new);
end $$;
revoke execute on function public.claim_anon_data(uuid, uuid) from public, anon, authenticated;
grant execute on function public.claim_anon_data(uuid, uuid) to service_role;

-- 4) 가입 안 한 익명 계정은 7일 뒤 자동 삭제 (기록·씨앗 등은 cascade로 같이). 매일 03:17 UTC
create extension if not exists pg_cron;
create or replace function public.purge_stale_anon() returns int
language sql security definer set search_path = public, auth as $$
  with d as (delete from auth.users where is_anonymous and created_at < now() - interval '7 days' returning 1)
  select count(*)::int from d
$$;
revoke execute on function public.purge_stale_anon() from public, anon, authenticated;
select cron.schedule('purge-stale-anon', '17 3 * * *', 'select public.purge_stale_anon()');

-- 5) 익명 계정 남발 막기: 분류(classify) IP 기준 하루 한도 (익명 계정만 셈, IP는 해시로만 저장)
create table if not exists public.classify_ip_usage (
  ip_hash text not null, day date not null, count int not null default 0, primary key (ip_hash, day)
);
alter table public.classify_ip_usage enable row level security;
create or replace function public.bump_classify_ip(p_ip_hash text) returns int
language plpgsql security definer set search_path = public as $$
declare n int;
begin
  if auth.uid() is null then raise exception 'not_authenticated'; end if;
  if public.is_member() or coalesce(p_ip_hash, '') = '' then return 0; end if;
  insert into public.classify_ip_usage (ip_hash, day, count) values (p_ip_hash, public.kst_today(), 1)
  on conflict (ip_hash, day) do update set count = classify_ip_usage.count + 1 returning count into n;
  delete from public.classify_ip_usage where day < public.kst_today() - 2;
  return n;
end $$;
revoke execute on function public.bump_classify_ip(text) from public, anon;
grant execute on function public.bump_classify_ip(text) to authenticated;
