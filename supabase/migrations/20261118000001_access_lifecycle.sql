-- 2026-11-18 DB 라이프사이클 검토 반영 (대표 결정: B1~B6 추천안, B7은 B안 = 끝나면 바로 잠금)
-- 가입 전 → 가입 → 무료 14일 → 구독 → 만료 → 재구독. 결제 연동(RevenueCat 웹훅)은 아직 — 표만 먼저 만들어 권한 함수가 보게 함

-- ───────── 1) 가입 시각 · 무료 끝 = 가입 + 14일을 그날 24시(KST)로 올림 (MONETIZATION 3장 1번, 약관 제7조 3항) ─────────
alter table public.profiles add column if not exists signed_up_at timestamptz;
alter table public.profiles add column if not exists consent_version text;

-- 가입 시각 → 무료 끝 시각. 11-01 15:00 KST 가입 → +14일 = 11-15 → 11-16 00:00 KST (= 화면의 "11월 15일까지 무료")
create or replace function public.trial_end_for(p_start timestamptz) returns timestamptz
language sql immutable set search_path = public as $$
  select (((p_start at time zone 'Asia/Seoul')::date + 15)::timestamp at time zone 'Asia/Seoul')
$$;
revoke execute on function public.trial_end_for(timestamptz) from public, anon, authenticated;

create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if coalesce(new.is_anonymous, false) then
    insert into public.profiles (id) values (new.id) on conflict do nothing;
  else
    insert into public.profiles (id, signed_up_at, trial_ends_at)
    values (new.id, now(), public.trial_end_for(now())) on conflict do nothing;
  end if;
  return new;
end $$;

create or replace function public.handle_user_linked()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if coalesce(old.is_anonymous, false) and not coalesce(new.is_anonymous, false) then
    update public.profiles
       set signed_up_at = coalesce(signed_up_at, now()),
           trial_ends_at = coalesce(trial_ends_at, public.trial_end_for(now())),
           onboarded_at = case when consented_at is not null then coalesce(onboarded_at, now()) else onboarded_at end
     where id = new.id;
    if exists (select 1 from public.profiles where id = new.id and consented_at is not null) then
      insert into public.seed_ledger (user_id, delta, reason) values (new.id, 6, 'onboarding_gift') on conflict do nothing;
    end if;
  end if;
  return new;
end $$;
revoke execute on function public.handle_user_linked() from public, anon, authenticated;

-- 기존 정식 계정 채우기: 가입 시각 = (있으면) 무료 끝 - 14일, 없으면 계정 만든 때. 무료 끝은 새 계산으로 다시
update public.profiles p
   set signed_up_at = coalesce(p.signed_up_at, p.trial_ends_at - interval '14 days', u.created_at)
  from auth.users u
 where u.id = p.id and not coalesce(u.is_anonymous, false);
update public.profiles p
   set trial_ends_at = public.trial_end_for(p.signed_up_at)
  from auth.users u
 where u.id = p.id and not coalesce(u.is_anonymous, false) and p.signed_up_at is not null;

-- ───────── 2) 동의: 서버 함수로만 저장 + 동의한 약관 판 (B6) ─────────
revoke update (consented_at, sensitive_consented_at) on public.profiles from authenticated;

-- p_version: 앱의 약관·처리방침 판(시행일 'YYYY-MM-DD'). p_onboard: '이미 계정이 있어요'로 새로 만든 정식 계정은 동의와 함께 온보딩 완료
create or replace function public.give_consent(p_version text, p_onboard boolean default false) returns void
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'not_authenticated'; end if;
  if coalesce(p_version, '') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'invalid_version'; end if;
  update public.profiles
     set consented_at = now(), sensitive_consented_at = now(), consent_version = p_version,
         onboarded_at = case when p_onboard then coalesce(onboarded_at, now()) else onboarded_at end
   where id = auth.uid();
end $$;
revoke execute on function public.give_consent(text, boolean) from public, anon;
grant execute on function public.give_consent(text, boolean) to authenticated;

create or replace function public.has_consent(p_uid uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.profiles where id = p_uid and consented_at is not null and sensitive_consented_at is not null)
$$;
revoke execute on function public.has_consent(uuid) from public, anon, authenticated;

-- ───────── 3) 구독 이력 + 웹훅 원본 (B2: 탈퇴해도 사용자 연결만 끊고 5년 보관) ─────────
-- 구독 기간(갱신 1회)마다 한 줄. 재구독은 새 줄 → 이전 이력을 덮어쓰지 않음. 결제 유예는 expires_at을 유예 끝으로 늘려 처리
create table if not exists public.subscriptions (
  id bigint generated always as identity primary key,
  user_id uuid references auth.users(id) on delete set null,
  store text not null check (store in ('app_store', 'play_store', 'test')),
  product_id text not null,
  original_transaction_id text not null,
  transaction_id text not null,
  period_start timestamptz not null,
  expires_at timestamptz not null,
  status text not null check (status in ('active', 'cancelled', 'grace', 'billing_retry', 'expired', 'refunded')),
  environment text not null default 'production' check (environment in ('production', 'sandbox')),
  user_deleted_at timestamptz, -- 계정 삭제 시각 (이 뒤로는 법정 보관용 기록만)
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (store, transaction_id)
);
create index if not exists subscriptions_user_exp on public.subscriptions (user_id, expires_at desc);
alter table public.subscriptions enable row level security;
drop policy if exists "own subscriptions read" on public.subscriptions;
create policy "own subscriptions read" on public.subscriptions for select to authenticated using (user_id = (select auth.uid()));
revoke all on public.subscriptions from anon, authenticated;
grant select on public.subscriptions to authenticated;

-- 결제 연동 업체 웹훅 원본: 같은 알림이 두 번 와도 id(업체 이벤트 id)로 한 번만 처리. service_role만
create table if not exists public.subscription_events (
  id text primary key,
  provider text not null default 'revenuecat',
  user_id uuid references auth.users(id) on delete set null,
  type text not null,
  payload jsonb not null,
  received_at timestamptz not null default now(),
  processed_at timestamptz,
  user_deleted_at timestamptz
);
alter table public.subscription_events enable row level security;
revoke all on public.subscription_events from anon, authenticated;

-- ───────── 4) 기록 권한: 테스터 · 무료 끝 전 · 유효한 구독 (B7-B: 끝나면 어제 기록도 바로 잠금) ─────────
create or replace function public.has_access(p_uid uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.testers where user_id = p_uid)
      or exists (select 1 from public.profiles where id = p_uid and trial_ends_at > now())
      or exists (select 1 from public.subscriptions where user_id = p_uid
                  and status in ('active', 'cancelled', 'grace') and expires_at > now())
$$;
revoke execute on function public.has_access(uuid) from public, anon, authenticated;

-- 앱이 설정·구독 시트에서 읽는 상태
create or replace function public.access_state() returns json
language sql stable security definer set search_path = public as $$
  select json_build_object(
    'access', public.has_access(auth.uid()),
    'tester', exists (select 1 from public.testers where user_id = auth.uid()),
    'trial_ends_at', (select trial_ends_at from public.profiles where id = auth.uid()),
    'sub_expires_at', (select max(expires_at) from public.subscriptions where user_id = auth.uid()
                        and status in ('active', 'cancelled', 'grace')),
    'sub_status', (select status from public.subscriptions where user_id = auth.uid() order by expires_at desc limit 1)
  )
$$;
revoke execute on function public.access_state() from public, anon;
grant execute on function public.access_state() to authenticated;

-- record_win: 동의 확인(B6) · 가입 전 계정은 기록 1개까지(B5) · 정식 계정은 기록 권한(has_access)
create or replace function public.record_win(p_text text, p_category text, p_source text default 'auto', p_win_date date default null)
returns json
language plpgsql security definer set search_path = public as $$
declare
  uid uuid := auth.uid();
  today date := public.kst_today();
  d date := coalesce(p_win_date, public.kst_today());
  created_today int;
  rewarded_today int;
  earned int := 0;
  w public.wins;
  first boolean;
  n int;
begin
  if uid is null then raise exception 'not_authenticated'; end if;
  if not public.has_consent(uid) then raise exception 'consent_required'; end if;
  if not public.is_member() then
    if exists (select 1 from public.wins where user_id = uid) then raise exception 'signup_required'; end if;
  elsif not public.has_access(uid) then
    raise exception 'subscription_required';
  end if;
  if d not in (today, today - 1) then raise exception 'invalid_date'; end if;
  if p_source not in ('auto','llm','user') then raise exception 'invalid_source'; end if;

  select count(*) into created_today from public.wins
   where user_id = uid and (created_at at time zone 'Asia/Seoul')::date = today;
  if created_today >= 50 then raise exception 'daily_limit'; end if;

  select not exists (select 1 from public.wins where user_id = uid) into first;

  -- 행 잠금으로 동시 기록에도 번호가 겹치지 않음
  update public.profiles set marbles_total = marbles_total + 1 where id = uid returning marbles_total into n;
  if n is null then raise exception 'not_found'; end if;

  insert into public.wins (user_id, text, category, category_source, win_date, jar_no)
  values (uid, btrim(p_text), p_category, p_source, d, (n - 1) / 50 + 1) returning * into w;

  select count(*) into rewarded_today from public.seed_ledger
   where user_id = uid and reason = 'win' and (created_at at time zone 'Asia/Seoul')::date = today;
  if rewarded_today < 5 then
    earned := 3;
    insert into public.seed_ledger (user_id, delta, reason, ref) values (uid, earned, 'win', w.id::text);
  end if;

  return json_build_object('win', row_to_json(w), 'earned', earned, 'balance', public.seed_balance(),
    'first', first, 'sealed', n % 50 = 0, 'capped', earned = 0);
end $$;

-- AI 분류도 동의 뒤에만 (B6). classify 함수는 이 호출이 실패하면 OpenAI로 보내지 않고 오류 → 앱은 키워드 분류
create or replace function public.bump_classify_usage() returns int
language plpgsql security definer set search_path = public as $$
declare uid uuid := auth.uid(); n int;
begin
  if uid is null then raise exception 'not_authenticated'; end if;
  if not public.has_consent(uid) then raise exception 'consent_required'; end if;
  insert into public.classify_usage (user_id, day, count) values (uid, public.kst_today(), 1)
  on conflict (user_id, day) do update set count = classify_usage.count + 1
  returning count into n;
  delete from public.classify_usage where user_id = uid and day < public.kst_today() - 7;
  return n;
end $$;

-- ───────── 5) 익명 기록 옮기기: 받는 계정에 기록 권한이 없으면 기록만 옮기고 씨앗(= 기록한 날 수)은 안 옮김 (B5) ─────────
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
  elsif ap.pet_name is distinct from '꼬마하마' and tp.pet_name = '꼬마하마' then
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
end $$;
create index if not exists app_events_user on public.app_events (user_id);

-- 계정이 지워지기 직전: 정식 계정의 이용 통계는 지금처럼 같이 삭제, 결제 기록엔 삭제 시각만 찍음(연결은 FK set null이 끊음)
create or replace function public.handle_user_deleting()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  delete from public.app_events where user_id = old.id;
  update public.subscriptions set user_deleted_at = now() where user_id = old.id;
  update public.subscription_events set user_deleted_at = now() where user_id = old.id;
  return old;
end $$;
revoke execute on function public.handle_user_deleting() from public, anon, authenticated;
drop trigger if exists on_auth_user_deleting on auth.users;
create trigger on_auth_user_deleting before delete on auth.users
  for each row execute function public.handle_user_deleting();

create or replace function public.purge_stale_anon() returns int
language plpgsql security definer set search_path = public, auth as $$
declare n int;
begin
  create temp table stale_anon on commit drop as
    select id, gen_random_uuid() as alias from auth.users
     where is_anonymous and created_at < now() - interval '7 days';
  update public.app_events e set user_id = s.alias from stale_anon s where e.user_id = s.id;
  delete from auth.users u using stale_anon s where u.id = s.id;
  get diagnostics n = row_count;
  return n;
end $$;
revoke execute on function public.purge_stale_anon() from public, anon, authenticated;

-- 결제 기록 법정 보관(전자상거래법 5년) 끝난 것 정리: 계정이 지워진 줄만. 매일 03:27 UTC
create or replace function public.purge_billing_records() returns int
language plpgsql security definer set search_path = public as $$
declare n int; m int;
begin
  delete from public.subscriptions where user_id is null and expires_at < now() - interval '5 years';
  get diagnostics n = row_count;
  delete from public.subscription_events where user_id is null and received_at < now() - interval '5 years';
  get diagnostics m = row_count;
  return n + m;
end $$;
revoke execute on function public.purge_billing_records() from public, anon, authenticated;
select cron.schedule('purge-billing-5y', '27 3 * * *', 'select public.purge_billing_records()');
