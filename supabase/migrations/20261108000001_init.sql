-- CSW MVP schema v1 (docs/FEATURES.md 2장)
-- 원칙: 성취 크기 차등 없음 / 잃는 장치 없음 / 경쟁 없음
-- 쓰기 규칙(씨앗 지급, 구매, 하루 한도)은 전부 서버 함수에서 강제한다. 클라이언트는 wins/ledger에 직접 insert 못 함.

create extension if not exists pgcrypto;

-- KST 기준 "오늘" (MVP는 한국 사용자만)
create or replace function public.kst_today() returns date
language sql stable as $$ select (now() at time zone 'Asia/Seoul')::date $$;

-- ───────── profiles ─────────
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  pet_name text not null default '꼬마하마' check (char_length(pet_name) between 1 and 12),
  notify_enabled boolean not null default false,
  notify_time time not null default '21:00',
  consented_at timestamptz,          -- 약관·개인정보·14세 이상·국외이전(분류 LLM) 동의
  onboarded_at timestamptz,
  created_at timestamptz not null default now()
);

-- 가입 시 프로필 자동 생성
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id) values (new.id) on conflict do nothing;
  return new;
end $$;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

-- ───────── wins (성취 기록) ─────────
create table public.wins (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  text text not null check (char_length(btrim(text)) between 1 and 100),
  category text not null check (category in ('tidy','move','study','eat','care','people','cheer')),
  category_source text not null default 'auto' check (category_source in ('auto','llm','user')),
  win_date date not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index wins_user_date on public.wins (user_id, win_date desc, created_at desc);

-- ───────── seeds ─────────
create table public.seed_ledger (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  delta int not null,
  reason text not null check (reason in ('win','onboarding_gift','purchase')),
  ref text,
  created_at timestamptz not null default now()
);
create index seed_ledger_user on public.seed_ledger (user_id, created_at);
-- 온보딩 선물은 1회만
create unique index seed_ledger_gift_once on public.seed_ledger (user_id) where reason = 'onboarding_gift';

-- ───────── items (상점 소품, 공개 카탈로그) ─────────
create table public.items (
  id text primary key,
  name text not null,
  emoji text not null,
  price int not null check (price > 0),
  sort int not null default 0,
  active boolean not null default true
);

create table public.owned_items (
  user_id uuid not null references auth.users(id) on delete cascade,
  item_id text not null references public.items(id),
  created_at timestamptz not null default now(),
  primary key (user_id, item_id)
);

-- ───────── safety_events (본문 저장 안 함) ─────────
create table public.safety_events (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  source text not null check (source in ('keyword','llm')),
  created_at timestamptz not null default now()
);

-- ───────── app_events (S9 분석, 기록 본문 금지) ─────────
create table public.app_events (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null check (name ~ '^[a-z_]{2,40}$'),
  props jsonb not null default '{}'::jsonb check (pg_column_size(props) < 1024),
  created_at timestamptz not null default now()
);
create index app_events_name_time on public.app_events (name, created_at);

-- ───────── RLS: 전 테이블 본인 행만 ─────────
alter table public.profiles enable row level security;
alter table public.wins enable row level security;
alter table public.seed_ledger enable row level security;
alter table public.items enable row level security;
alter table public.owned_items enable row level security;
alter table public.safety_events enable row level security;
alter table public.app_events enable row level security;

create policy "own profile read" on public.profiles for select to authenticated using (id = (select auth.uid()));
create policy "own profile update" on public.profiles for update to authenticated using (id = (select auth.uid())) with check (id = (select auth.uid()));

create policy "own wins read" on public.wins for select to authenticated using (user_id = (select auth.uid()));
create policy "own wins delete" on public.wins for delete to authenticated using (user_id = (select auth.uid()));
-- 수정은 edit_win() 함수로만 (insert/update 정책 없음)

create policy "own ledger read" on public.seed_ledger for select to authenticated using (user_id = (select auth.uid()));
create policy "items read" on public.items for select to authenticated using (active);
create policy "own items read" on public.owned_items for select to authenticated using (user_id = (select auth.uid()));
create policy "own safety insert" on public.safety_events for insert to authenticated with check (user_id = (select auth.uid()));
create policy "own events insert" on public.app_events for insert to authenticated with check (user_id = (select auth.uid()));

revoke all on public.profiles, public.wins, public.seed_ledger, public.items, public.owned_items, public.safety_events, public.app_events from anon;
grant select, update (pet_name, notify_enabled, notify_time, consented_at, onboarded_at) on public.profiles to authenticated;
grant select, delete on public.wins to authenticated;
grant select on public.seed_ledger, public.items, public.owned_items to authenticated;
grant insert (user_id, source) on public.safety_events to authenticated;
grant insert (user_id, name, props) on public.app_events to authenticated;

-- ───────── 서버 함수 ─────────
create or replace function public.seed_balance() returns int
language sql stable security definer set search_path = public as $$
  select coalesce(sum(delta), 0)::int from public.seed_ledger where user_id = auth.uid()
$$;

-- 기록 1개 = 씨앗 3개, 하루(KST, 기록한 날 기준) 10개까지 보상. 기록 자체는 하루 50개(남용 방지)까지.
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
begin
  if uid is null then raise exception 'not_authenticated'; end if;
  if d not in (today, today - 1) then raise exception 'invalid_date'; end if;
  if p_source not in ('auto','llm','user') then raise exception 'invalid_source'; end if;

  select count(*) into created_today from public.wins
   where user_id = uid and (created_at at time zone 'Asia/Seoul')::date = today;
  if created_today >= 50 then raise exception 'daily_limit'; end if;

  select not exists (select 1 from public.wins where user_id = uid) into first;

  insert into public.wins (user_id, text, category, category_source, win_date)
  values (uid, btrim(p_text), p_category, p_source, d) returning * into w;

  select count(*) into rewarded_today from public.seed_ledger
   where user_id = uid and reason = 'win' and (created_at at time zone 'Asia/Seoul')::date = today;
  if rewarded_today < 10 then
    earned := 3;
    insert into public.seed_ledger (user_id, delta, reason, ref) values (uid, earned, 'win', w.id::text);
  end if;

  return json_build_object('win', row_to_json(w), 'earned', earned, 'balance', public.seed_balance(), 'first', first);
end $$;

-- 수정: 내용·카테고리만. 이미 받은 씨앗은 그대로.
create or replace function public.edit_win(p_id uuid, p_text text, p_category text)
returns public.wins
language plpgsql security definer set search_path = public as $$
declare w public.wins;
begin
  update public.wins set text = btrim(p_text), category = p_category, category_source = 'user', updated_at = now()
   where id = p_id and user_id = auth.uid() returning * into w;
  if w.id is null then raise exception 'not_found'; end if;
  return w;
end $$;

create or replace function public.grant_onboarding_gift() returns int
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'not_authenticated'; end if;
  insert into public.seed_ledger (user_id, delta, reason) values (auth.uid(), 6, 'onboarding_gift')
  on conflict do nothing;
  return public.seed_balance();
end $$;

create or replace function public.buy_item(p_item_id text) returns int
language plpgsql security definer set search_path = public as $$
declare
  uid uuid := auth.uid();
  it public.items;
  bal int;
begin
  if uid is null then raise exception 'not_authenticated'; end if;
  perform pg_advisory_xact_lock(hashtext(uid::text));
  select * into it from public.items where id = p_item_id and active;
  if it.id is null then raise exception 'not_found'; end if;
  if exists (select 1 from public.owned_items where user_id = uid and item_id = it.id) then raise exception 'already_owned'; end if;
  bal := public.seed_balance();
  if bal < it.price then raise exception 'not_enough_seeds'; end if;
  insert into public.owned_items (user_id, item_id) values (uid, it.id);
  insert into public.seed_ledger (user_id, delta, reason, ref) values (uid, -it.price, 'purchase', it.id);
  return bal - it.price;
end $$;

-- 모든 기록 지우기: wins만. 펫·방·씨앗 유지.
create or replace function public.delete_all_wins() returns void
language sql security definer set search_path = public as $$
  delete from public.wins where user_id = auth.uid()
$$;

-- 계정 삭제: auth 사용자 삭제 → 모든 행 cascade
create or replace function public.delete_my_account() returns void
language plpgsql security definer set search_path = public, auth as $$
begin
  if auth.uid() is null then raise exception 'not_authenticated'; end if;
  delete from auth.users where id = auth.uid();
end $$;

revoke execute on function public.record_win, public.edit_win, public.grant_onboarding_gift, public.buy_item,
  public.delete_all_wins, public.delete_my_account, public.seed_balance from public, anon;
grant execute on function public.record_win, public.edit_win, public.grant_onboarding_gift, public.buy_item,
  public.delete_all_wins, public.delete_my_account, public.seed_balance to authenticated;
revoke execute on function public.handle_new_user from public, anon, authenticated;

-- ───────── 소품 카탈로그 (임시 18개, 최종 목록·가격은 docs/WORLD.md 스레드가 정함) ─────────
insert into public.items (id, name, emoji, price, sort) values
  ('star',      '별 장식',   '⭐', 6, 1),
  ('plant',     '화분',     '🪴', 9, 2),
  ('mug',       '머그컵',   '☕', 9, 3),
  ('rug',       '러그',     '🟫', 12, 4),
  ('books',     '책 더미',   '📚', 12, 5),
  ('frame',     '액자',     '🖼️', 15, 6),
  ('clock',     '벽시계',   '🕰️', 15, 7),
  ('lamp',      '스탠드',   '💡', 18, 8),
  ('sofa',      '소파',     '🛋️', 24, 9),
  ('cake',      '케이크',   '🎂', 21, 10),
  ('flowers',   '꽃병',     '💐', 18, 11),
  ('radio',     '라디오',   '📻', 24, 12),
  ('window',    '창문 화분', '🌵', 21, 13),
  ('balloon',   '풍선',     '🎈', 12, 14),
  ('teddy',     '곰인형',   '🧸', 27, 15),
  ('guitar',    '기타',     '🎸', 30, 16),
  ('bed',       '포근한 침대', '🛏️', 36, 17),
  ('aquarium',  '어항',     '🐠', 33, 18);
