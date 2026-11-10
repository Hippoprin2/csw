-- 유리병 앨범 (FEATURES C6 J1-A, 2026-11-10 대표 결정)
-- 기록마다 들어간 병 번호(jar_no)를 넣는 순간 고정한다 → 기록을 지워도 다른 병 내용이 밀리지 않음.
-- 병 하나 = 구슬 50개. profiles.marbles_total = 지금까지 넣은 구슬 수(지워도 줄지 않는 카운터, 모든 기록 지우기 때만 0).

alter table public.profiles add column if not exists marbles_total int not null default 0;
alter table public.wins add column if not exists jar_no int;

with r as (
  select id, row_number() over (partition by user_id order by created_at, id) as rn from public.wins
)
update public.wins w set jar_no = (r.rn - 1) / 50 + 1 from r where r.id = w.id and w.jar_no is null;

update public.profiles p set marbles_total = c.n
  from (select user_id, count(*)::int as n from public.wins group by user_id) c
 where c.user_id = p.id;

alter table public.wins alter column jar_no set not null;
create index if not exists wins_user_jar on public.wins (user_id, jar_no, created_at);

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
  if rewarded_today < 10 then
    earned := 3;
    insert into public.seed_ledger (user_id, delta, reason, ref) values (uid, earned, 'win', w.id::text);
  end if;

  return json_build_object('win', row_to_json(w), 'earned', earned, 'balance', public.seed_balance(),
    'first', first, 'sealed', n % 50 = 0);
end $$;

-- 모든 기록 지우기: wins + 병 카운터. 펫·방·씨앗 유지.
create or replace function public.delete_all_wins() returns void
language sql security definer set search_path = public as $$
  delete from public.wins where user_id = auth.uid();
  update public.profiles set marbles_total = 0 where id = auth.uid();
$$;

-- 병 목록 요약 (선반): 병마다 구슬 수·기간·카테고리별 수. 본문은 안 보냄.
create or replace function public.jar_summary() returns json
language sql stable security invoker set search_path = public as $$
  select json_build_object(
    'current_jar', (select marbles_total / 50 + 1 from public.profiles where id = auth.uid()),
    'total', (select count(*) from public.wins where user_id = auth.uid()),
    'jars', coalesce((
      select json_agg(j order by j.no) from (
        select jar_no as no, count(*)::int as count, min(win_date) as "from", max(win_date) as "to",
               (select json_object_agg(category, c) from (
                  select category, count(*)::int as c from public.wins w2
                   where w2.user_id = auth.uid() and w2.jar_no = w.jar_no group by category) x) as cats
          from public.wins w where user_id = auth.uid() group by jar_no
      ) j), '[]'::json)
  )
$$;

revoke execute on function public.record_win, public.delete_all_wins, public.jar_summary from public, anon;
grant execute on function public.record_win, public.delete_all_wins, public.jar_summary to authenticated;
