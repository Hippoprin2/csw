-- 보안 보강 (2026-11-09)
-- 1) 자해 감지 기록 익명화: 누가 감지됐는지는 민감한 건강 정보 → 사용자 ID 없이 날짜·출처별 횟수만
-- 2) AI 분류 호출 횟수 제한용 사용량 (본문 없음, 7일 지나면 지움)

drop table if exists public.safety_events;

create table public.safety_daily (
  day date not null,
  source text not null check (source in ('keyword','llm')),
  count int not null default 0,
  primary key (day, source)
);
alter table public.safety_daily enable row level security; -- 정책 없음 = 앱에서 읽기·쓰기 불가 (log_safety만)
revoke all on public.safety_daily from anon, authenticated;

create or replace function public.log_safety(p_source text) returns void
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'not_authenticated'; end if;
  if p_source not in ('keyword','llm') then raise exception 'invalid_source'; end if;
  insert into public.safety_daily (day, source, count) values (public.kst_today(), p_source, 1)
  on conflict (day, source) do update set count = safety_daily.count + 1;
end $$;

create table public.classify_usage (
  user_id uuid not null references auth.users(id) on delete cascade,
  day date not null,
  count int not null default 0,
  primary key (user_id, day)
);
alter table public.classify_usage enable row level security;
revoke all on public.classify_usage from anon, authenticated;

-- 분류 함수가 사용자 토큰으로 호출: 오늘 사용량 +1 후 값 반환 (한도 판단은 함수 쪽)
create or replace function public.bump_classify_usage() returns int
language plpgsql security definer set search_path = public as $$
declare uid uuid := auth.uid(); n int;
begin
  if uid is null then raise exception 'not_authenticated'; end if;
  insert into public.classify_usage (user_id, day, count) values (uid, public.kst_today(), 1)
  on conflict (user_id, day) do update set count = classify_usage.count + 1
  returning count into n;
  delete from public.classify_usage where user_id = uid and day < public.kst_today() - 7;
  return n;
end $$;

revoke execute on function public.log_safety, public.bump_classify_usage from public, anon;
grant execute on function public.log_safety, public.bump_classify_usage to authenticated;
