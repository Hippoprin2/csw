-- 마당 (첫 업데이트, docs/WORLD.md 7장 · FEATURES 7장, 2026-11-10 대표 확정)
-- - 열림: 기록한 날 누적 7일(연속 아님). 한 번 열리면 영구(profiles.yard_opened_at)
-- - 구역: 1 무료 / 2 개울가 60 / 3 꽃언덕 숲길 120씨앗. 산 구역은 영구
-- - 소품 10개(합계 162, 자리 1개씩, 바꿔 끼우기 없음). 마당이 열려야 살 수 있음
-- - 추억 나무: 기록한 날 10/30/60일 단계(앱이 yard_state.record_days로 계산), 열매 = 지난 기록 카드(memory_card)
-- - 테스트 스위치: testers 표에 있는 계정(대표·테스트 계정)만

-- ───────── 테스터 (대표·테스트 계정). 관리자(service role)만 넣고 뺌 ─────────
create table if not exists public.testers (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);
alter table public.testers enable row level security;
revoke all on public.testers from anon, authenticated;

create or replace function public.is_tester() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.testers where user_id = auth.uid())
$$;

-- 테스트용 씨앗 지급 사유 추가
alter table public.seed_ledger drop constraint if exists seed_ledger_reason_check;
alter table public.seed_ledger add constraint seed_ledger_reason_check check (reason in ('win','onboarding_gift','purchase','dev'));

alter table public.profiles add column if not exists yard_opened_at timestamptz;
alter table public.profiles add column if not exists yard_dev_open boolean not null default false;

-- 전체 기록한 날 수 (KST, seed_ledger 'win' 기준 → 기록을 지워도 줄지 않음)
create or replace function public.record_days_total(p_uid uuid) returns int
language sql stable security definer set search_path = public as $$
  select count(distinct (created_at at time zone 'Asia/Seoul')::date)::int
    from public.seed_ledger where user_id = p_uid and reason = 'win'
$$;

-- 마당이 열렸는지 (처음 조건을 채우면 열린 시각을 남겨 영구로)
create or replace function public.yard_open(p_uid uuid) returns boolean
language plpgsql security definer set search_path = public as $$
declare p public.profiles;
begin
  select * into p from public.profiles where id = p_uid;
  if p.id is null then return false; end if;
  if p.yard_opened_at is not null or p.yard_dev_open then return true; end if;
  if public.record_days_total(p_uid) >= 7 then
    update public.profiles set yard_opened_at = now() where id = p_uid;
    return true;
  end if;
  return false;
end $$;

-- ───────── 구역 ─────────
create table if not exists public.yard_zones (
  user_id uuid not null references auth.users(id) on delete cascade,
  zone int not null check (zone in (2, 3)),
  created_at timestamptz not null default now(),
  primary key (user_id, zone)
);
alter table public.yard_zones enable row level security;
drop policy if exists "own zones read" on public.yard_zones;
create policy "own zones read" on public.yard_zones for select to authenticated using (user_id = (select auth.uid()));
revoke all on public.yard_zones from anon;
grant select on public.yard_zones to authenticated;

create or replace function public.zone_price(p_zone int) returns int
language sql immutable as $$ select case p_zone when 2 then 60 when 3 then 120 end $$;

create or replace function public.buy_zone(p_zone int) returns int
language plpgsql security definer set search_path = public as $$
declare uid uuid := auth.uid(); price int := public.zone_price(p_zone); bal int;
begin
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
end $$;

-- ───────── 마당 소품 10개 (자리 = 자기 id → 바꿔 끼우기 없음) ─────────
insert into public.items (id, name, emoji, price, sort, space, slot, layer) values
  ('flower_bed',  '화단',        '🌷', 9,  101, 'yard', 'flower_bed',  'mid'),
  ('pinwheel',    '바람개비',    '🎡', 9,  102, 'yard', 'pinwheel',    'mid'),
  ('duck_float',  '오리 튜브',   '🦆', 12, 103, 'yard', 'duck_float',  'mid'),
  ('mailbox',     '우체통',      '📮', 12, 104, 'yard', 'mailbox',     'mid'),
  ('garden_lamp', '정원등',      '🏮', 12, 105, 'yard', 'garden_lamp', 'mid'),
  ('bird_feeder', '새 모이통',   '🐦', 18, 106, 'yard', 'bird_feeder', 'mid'),
  ('bench',       '벤치',        '🪑', 18, 107, 'yard', 'bench',       'mid'),
  ('picnic_mat',  '피크닉 매트', '🧺', 18, 108, 'yard', 'picnic_mat',  'mid'),
  ('hammock',     '해먹',        '🌴', 24, 109, 'yard', 'hammock',     'mid'),
  ('tent',        '텐트',        '⛺', 30, 110, 'yard', 'tent',        'mid')
on conflict (id) do update set name = excluded.name, emoji = excluded.emoji, price = excluded.price, sort = excluded.sort,
  space = excluded.space, slot = excluded.slot, layer = excluded.layer, active = true;

-- 사면 바로 그 자리에 놓임. 마당 소품은 마당이 열려야 살 수 있음
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
  if it.space = 'yard' and not public.yard_open(uid) then raise exception 'yard_locked'; end if;
  if exists (select 1 from public.owned_items where user_id = uid and item_id = it.id) then raise exception 'already_owned'; end if;
  bal := public.seed_balance();
  if bal < it.price then raise exception 'not_enough_seeds'; end if;
  update public.owned_items o set placed = false from public.items i
   where o.user_id = uid and o.item_id = i.id and i.slot = it.slot;
  insert into public.owned_items (user_id, item_id, placed) values (uid, it.id, true);
  insert into public.seed_ledger (user_id, delta, reason, ref) values (uid, -it.price, 'purchase', it.id);
  return bal - it.price;
end $$;

-- ───────── 마당 상태 한 번에 ─────────
create or replace function public.yard_state() returns json
language plpgsql security definer set search_path = public as $$
declare uid uuid := auth.uid();
begin
  if uid is null then raise exception 'not_authenticated'; end if;
  return json_build_object(
    'open', public.yard_open(uid),
    'record_days', public.record_days_total(uid),
    'zones', coalesce((select json_agg(zone order by zone) from public.yard_zones where user_id = uid), '[]'::json),
    'tester', public.is_tester(),
    'dev_open', coalesce((select yard_dev_open from public.profiles where id = uid), false));
end $$;

-- ───────── 추억 나무 열매 = 지난 기록 카드 (FEATURES S11) ─────────
-- "한 달 전 오늘" 기록이 있으면 그것, 없으면 7일 이상 지난 기록 중 무작위. '버틴 하루'(힘든 마음·자해 표현)는 꺼내지 않음.
-- p_seen: 이번에 이미 보여준 기록(열매마다 다른 카드)
create or replace function public.memory_card(p_seen uuid[] default '{}') returns json
language plpgsql stable security definer set search_path = public as $$
declare uid uuid := auth.uid(); w public.wins; kind text := 'month';
begin
  if uid is null then raise exception 'not_authenticated'; end if;
  select * into w from public.wins
   where user_id = uid and category <> 'endure' and not (id = any(p_seen))
     and win_date = (public.kst_today() - interval '1 month')::date
   order by random() limit 1;
  if w.id is null then
    kind := 'past';
    select * into w from public.wins
     where user_id = uid and category <> 'endure' and not (id = any(p_seen))
       and win_date <= public.kst_today() - 7
     order by random() limit 1;
  end if;
  if w.id is null then return null; end if;
  return json_build_object('id', w.id, 'text', w.text, 'category', w.category, 'win_date', w.win_date, 'kind', kind);
end $$;

-- ───────── 테스트 스위치 (테스터만) ─────────
create or replace function public.dev_yard(p_open boolean) returns void
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_tester() then raise exception 'forbidden'; end if;
  update public.profiles set yard_dev_open = p_open where id = auth.uid();
end $$;

create or replace function public.dev_all_zones() returns void
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_tester() then raise exception 'forbidden'; end if;
  insert into public.yard_zones (user_id, zone) values (auth.uid(), 2), (auth.uid(), 3) on conflict do nothing;
end $$;

create or replace function public.dev_seeds() returns int
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_tester() then raise exception 'forbidden'; end if;
  insert into public.seed_ledger (user_id, delta, reason, ref) values (auth.uid(), 500, 'dev', 'test_switch');
  return public.seed_balance();
end $$;

revoke execute on function public.is_tester, public.record_days_total, public.yard_open, public.zone_price, public.buy_zone,
  public.buy_item, public.yard_state, public.memory_card, public.dev_yard, public.dev_all_zones, public.dev_seeds from public, anon;
revoke execute on function public.record_days_total, public.yard_open, public.is_tester from authenticated;
grant execute on function public.buy_zone, public.buy_item, public.yard_state, public.memory_card,
  public.dev_yard, public.dev_all_zones, public.dev_seeds, public.zone_price to authenticated;

-- 대표 계정(카카오·Apple·이메일)을 테스터로
insert into public.testers (user_id) select id from auth.users
 where id in ('bf372674-64b9-43f8-9bf4-e8b806eea08e', '0b2f7bd4-651e-43b5-808b-51d5885414a8', '00c423ae-968e-413b-ab90-c88cefbadb16')
on conflict do nothing;
