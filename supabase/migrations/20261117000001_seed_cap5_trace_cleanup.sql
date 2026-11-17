-- 하루 씨앗 받는 기록 10 → 5개 (2026-11-15 대표 결정 I1~I3, WORLD 3장 '하루 씨앗 상한')
-- 기록·구슬·축하는 그대로 무제한(하루 50개 남용 방지만). 이미 받은 씨앗은 회수 안 함.
-- 응답에 capped(이번 기록은 상한이라 씨앗 없음) 추가 → 앱이 처음 한 번만 안내.
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
  if rewarded_today < 5 then
    earned := 3;
    insert into public.seed_ledger (user_id, delta, reason, ref) values (uid, earned, 'win', w.id::text);
  end if;

  return json_build_object('win', row_to_json(w), 'earned', earned, 'balance', public.seed_balance(),
    'first', first, 'sealed', n % 50 = 0, 'capped', earned = 0);
end $$;


-- 자해·남 해치는 표현 판정 흔적 정리 (LAUNCH 2장, 2026-11-14): 이용 통계 win_recorded에 '버틴 하루' 분류 값을 남기지 않는다.
update public.app_events set props = props - 'category'
 where name = 'win_recorded' and props->>'category' = 'endure';

revoke execute on function public.record_win from public, anon;
grant execute on function public.record_win to authenticated;
