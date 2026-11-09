-- 2단계: 방 소품 v1(자리·층) + 텃밭 (docs/WORLD.md, FEATURES.md 7장, 2026-11-09 대표 확정)
-- 원칙: 진행은 줄지 않음 / 죽거나 썩지 않음 / 기록 수가 아니라 "기록한 날" 기준(차등 없음)

-- ───────── 방 소품: 자리(slot) + 층(layer). 같은 자리 소품은 하나만 놓임(placed) ─────────
alter table public.items add column if not exists space text not null default 'room' check (space in ('room','yard'));
alter table public.items add column if not exists slot text;
alter table public.items add column if not exists layer text not null default 'mid' check (layer in ('back','mid','front'));
alter table public.owned_items add column if not exists placed boolean not null default true;

-- 출시 전이라 임시 소품은 정리 (테스트 계정 보유분 포함)
delete from public.owned_items where item_id not in
  ('frame','garland','cushion','mobile','big_plant','wall_clock','curtain','rug','squirrel','lamp','string_lights',
   'low_table','radio_stand','easel','guitar','bookshelf','aquarium','bed');
delete from public.items where id not in
  ('frame','garland','cushion','mobile','big_plant','wall_clock','curtain','rug','squirrel','lamp','string_lights',
   'low_table','radio_stand','easel','guitar','bookshelf','aquarium','bed');

insert into public.items (id, name, emoji, price, sort, space, slot, layer) values
  ('frame',         '액자',        '🖼️', 9,  1, 'room', 'wall_left',    'back'),
  ('garland',       '가랜드',      '🎏', 9,  2, 'room', 'wall_top',     'back'),
  ('cushion',       '쿠션',        '🟪', 9,  3, 'room', 'front_center', 'front'),
  ('mobile',        '모빌',        '🎐', 9,  4, 'room', 'ceiling',      'back'),
  ('big_plant',     '큰 화분',     '🪴', 9,  5, 'room', 'front_right',  'front'),
  ('wall_clock',    '벽시계',      '🕰️', 9,  6, 'room', 'wall_right',   'back'),
  ('curtain',       '커튼',        '🪟', 12, 7, 'room', 'window',       'back'),
  ('rug',           '러그',        '🟣', 12, 8, 'room', 'floor_center', 'back'),
  ('squirrel',      '다람쥐 인형', '🐿️', 12, 9, 'room', 'front_center', 'front'),
  ('lamp',          '스탠드',      '💡', 12, 10, 'room', 'front_left',  'front'),
  ('string_lights', '전구줄',      '✨', 12, 11, 'room', 'wall_top',    'back'),
  ('low_table',     '좌식 탁자',   '🍵', 18, 12, 'room', 'floor_right', 'mid'),
  ('radio_stand',   '협탁+라디오', '📻', 18, 13, 'room', 'bedside',     'back'),
  ('easel',         '이젤',        '🎨', 18, 14, 'room', 'lean',        'back'),
  ('guitar',        '기타',        '🎸', 18, 15, 'room', 'lean',        'back'),
  ('bookshelf',     '책장',        '📚', 24, 16, 'room', 'back_right',  'back'),
  ('aquarium',      '어항',        '🐠', 24, 17, 'room', 'bedside',     'back'),
  ('bed',           '포근한 침대', '🛏️', 30, 18, 'room', 'back_left',   'back')
on conflict (id) do update set name = excluded.name, emoji = excluded.emoji, price = excluded.price, sort = excluded.sort,
  space = excluded.space, slot = excluded.slot, layer = excluded.layer, active = true;


-- 사면 바로 그 자리에 놓임 (같은 자리 다른 소품은 내려감, 소유는 그대로)
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
  update public.owned_items o set placed = false from public.items i
   where o.user_id = uid and o.item_id = i.id and i.slot = it.slot;
  insert into public.owned_items (user_id, item_id, placed) values (uid, it.id, true);
  insert into public.seed_ledger (user_id, delta, reason, ref) values (uid, -it.price, 'purchase', it.id);
  return bal - it.price;
end $$;

-- 같은 자리 소품 바꿔 끼우기
create or replace function public.place_item(p_item_id text) returns void
language plpgsql security definer set search_path = public as $$
declare uid uuid := auth.uid(); s text;
begin
  select i.slot into s from public.items i join public.owned_items o on o.item_id = i.id and o.user_id = uid where i.id = p_item_id;
  if s is null then raise exception 'not_owned'; end if;
  update public.owned_items o set placed = (o.item_id = p_item_id) from public.items i
   where o.user_id = uid and o.item_id = i.id and i.slot = s;
end $$;

-- ───────── 텃밭 ─────────
create table public.crops (
  id text primary key,
  name text not null,
  emoji text not null,
  kind text not null check (kind in ('flower','edible')),
  price int not null default 3 check (price >= 0),
  deco_name text not null,          -- 처음 수확하면 창턱 선반에 생기는 장식
  deco_emoji text not null,
  sort int not null default 0,
  active boolean not null default true
);
insert into public.crops (id, name, emoji, kind, price, deco_name, deco_emoji, sort) values
  ('sweet_potato', '고구마',   '🍠', 'edible', 3, '고구마 바구니', '🧺', 1),
  ('tulip',        '튤립',     '🌷', 'flower', 3, '튤립 꽃병',     '🌷', 2),
  ('sunflower',    '해바라기', '🌻', 'flower', 3, '해바라기 꽃병', '🌻', 3),
  ('strawberry',   '딸기',     '🍓', 'edible', 3, '딸기 접시',     '🍓', 4);

alter table public.profiles add column if not exists first_crop_used boolean not null default false;
alter table public.profiles add column if not exists last_seen_at timestamptz;

create table public.plots (
  user_id uuid not null references auth.users(id) on delete cascade,
  slot int not null check (slot between 1 and 3),
  crop_id text not null references public.crops(id),
  planted_day date not null,         -- KST. 이 날 "다음"부터 기록한 날을 센다
  required_days int not null,        -- 9 (첫 작물은 1)
  created_at timestamptz not null default now(),
  primary key (user_id, slot)
);
create table public.harvest_bag (
  user_id uuid not null references auth.users(id) on delete cascade,
  crop_id text not null references public.crops(id),
  count int not null default 0 check (count >= 0),
  primary key (user_id, crop_id)
);
create table public.harvest_unlocks (
  user_id uuid not null references auth.users(id) on delete cascade,
  crop_id text not null references public.crops(id),
  created_at timestamptz not null default now(),
  primary key (user_id, crop_id)
);

alter table public.crops enable row level security;
alter table public.plots enable row level security;
alter table public.harvest_bag enable row level security;
alter table public.harvest_unlocks enable row level security;
create policy "crops read" on public.crops for select to authenticated using (active);
create policy "own plots read" on public.plots for select to authenticated using (user_id = (select auth.uid()));
create policy "own bag read" on public.harvest_bag for select to authenticated using (user_id = (select auth.uid()));
create policy "own unlocks read" on public.harvest_unlocks for select to authenticated using (user_id = (select auth.uid()));
revoke all on public.crops, public.plots, public.harvest_bag, public.harvest_unlocks from anon;
grant select on public.crops, public.plots, public.harvest_bag, public.harvest_unlocks to authenticated;

-- 기록한 날 수: seed_ledger 'win' 행 기준 (기록을 지워도 남음 → 성장이 줄지 않음).
-- 하루 첫 기록은 항상 씨앗을 받으므로 기록한 날마다 최소 1행이 있다.
create or replace function public.record_days_since(p_uid uuid, p_day date) returns int
language sql stable security definer set search_path = public as $$
  select count(distinct (created_at at time zone 'Asia/Seoul')::date)::int
    from public.seed_ledger where user_id = p_uid and reason = 'win'
     and (created_at at time zone 'Asia/Seoul')::date > p_day
$$;

-- 텃밭 상태 한 번에: 칸마다 작물·기록한 날·필요한 날
create or replace function public.garden_state() returns json
language sql stable security definer set search_path = public as $$
  select coalesce(json_agg(json_build_object(
    'slot', p.slot, 'crop_id', p.crop_id, 'planted_day', p.planted_day,
    'required_days', p.required_days, 'days', public.record_days_since(p.user_id, p.planted_day)) order by p.slot), '[]'::json)
  from public.plots p where p.user_id = auth.uid()
$$;

-- 심기: 첫 작물은 고구마 고정·무료·다음 기록한 날 수확. 그 뒤는 3씨앗·기록한 날 9일
create or replace function public.plant(p_slot int, p_crop text) returns int
language plpgsql security definer set search_path = public as $$
declare
  uid uuid := auth.uid();
  c public.crops;
  first boolean;
  bal int;
begin
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
end $$;

-- 수확: 다 자랐을 때만. 바구니 +1, 처음이면 장식 생김
create or replace function public.harvest(p_slot int) returns json
language plpgsql security definer set search_path = public as $$
declare
  uid uuid := auth.uid();
  p public.plots;
  new_unlock boolean;
begin
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
end $$;

-- 먹이기(채소·열매) / 선물하기(꽃): 바구니에서 1개. 장식은 그대로
create or replace function public.use_harvest(p_crop text) returns int
language plpgsql security definer set search_path = public as $$
declare uid uuid := auth.uid(); n int;
begin
  update public.harvest_bag set count = count - 1 where user_id = uid and crop_id = p_crop and count > 0 returning count into n;
  if n is null then raise exception 'empty_bag'; end if;
  return n;
end $$;

-- 접속 기록: 이전 접속 시각을 돌려준다 (3일 이상이면 텃밭이 "졸고 있음")
create or replace function public.touch_seen() returns timestamptz
language plpgsql security definer set search_path = public as $$
declare prev timestamptz;
begin
  select last_seen_at into prev from public.profiles where id = auth.uid();
  update public.profiles set last_seen_at = now() where id = auth.uid();
  return prev;
end $$;

revoke execute on function public.place_item, public.record_days_since, public.garden_state, public.plant,
  public.harvest, public.use_harvest, public.touch_seen from public, anon;
grant execute on function public.place_item, public.garden_state, public.plant,
  public.harvest, public.use_harvest, public.touch_seen to authenticated;
revoke execute on function public.record_days_since from authenticated;
