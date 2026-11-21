-- 2026-11-21 출시 전 개발 3
-- 1) S25 동작 요청: '그 밖의 승리'로 축하받은 뒤 "단짝이 이 동작을 했으면 좋겠어" → 짧은 키워드만 저장 (기록 본문은 저장 안 함)
-- 2) 3년 미접속 계정 삭제 (처리방침 4장): 마지막 접속 3년 + 안내 메일 보낸 지 30일 + 구독 유지 중 아님 → 삭제

-- ───────── 1) motion_requests ─────────
create table if not exists public.motion_requests (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  category text not null,
  keyword text not null check (char_length(keyword) between 1 and 20),
  created_at timestamptz not null default now()
);
create index if not exists motion_requests_time on public.motion_requests (created_at);
alter table public.motion_requests enable row level security;
-- 정책 없음 = 앱에서 직접 읽기·쓰기 불가. 아래 RPC로만 넣음. 집계는 service role(운영자)만

create or replace function public.request_motion(p_keyword text, p_category text) returns void
language plpgsql security definer set search_path = public as $$
declare k text := btrim(regexp_replace(coalesce(p_keyword, ''), '\s+', ' ', 'g'));
begin
  perform public.require_member();
  if char_length(k) < 1 or char_length(k) > 20 then raise exception 'bad_keyword'; end if;
  if (select count(*) from public.motion_requests where user_id = auth.uid() and created_at > now() - interval '1 day') >= 10 then
    raise exception 'too_many';
  end if;
  insert into public.motion_requests (user_id, category, keyword) values (auth.uid(), coalesce(p_category, 'cheer'), k);
end $$;
revoke execute on function public.request_motion(text, text) from public, anon;
grant execute on function public.request_motion(text, text) to authenticated;

-- ───────── 2) 3년 미접속 계정 삭제 ─────────
alter table public.profiles add column if not exists inactive_notice_at timestamptz; -- 30일 전 안내 메일 보낸 시각

-- 안내 메일 보낼 대상 (메일 발송 업체 연동 뒤 매일 이 목록에 보내고 inactive_notice_at = now() 기록)
create or replace function public.inactive_notice_due() returns table (user_id uuid, email text)
language sql stable security definer set search_path = public as $$
  select p.id, u.email from public.profiles p join auth.users u on u.id = p.id
  where not u.is_anonymous and u.email is not null
    and coalesce(p.last_seen_at, p.created_at) < now() - interval '3 years'
    and (p.inactive_notice_at is null or p.inactive_notice_at < coalesce(p.last_seen_at, p.created_at))
    and not exists (select 1 from public.subscriptions s where s.user_id = p.id
                    and s.status in ('active', 'cancelled', 'grace') and s.expires_at > now())
$$;
revoke execute on function public.inactive_notice_due() from public, anon, authenticated;

-- 안내 후 30일 지나도록 접속이 없으면 삭제. 안내를 못 보낸 계정은 지우지 않음(안전한 쪽)
create or replace function public.purge_inactive_accounts() returns int
language plpgsql security definer set search_path = public as $$
declare n int;
begin
  with gone as (
    delete from auth.users u using public.profiles p
    where p.id = u.id and not u.is_anonymous
      and coalesce(p.last_seen_at, p.created_at) < now() - interval '3 years'
      and p.inactive_notice_at is not null
      and p.inactive_notice_at >= coalesce(p.last_seen_at, p.created_at)
      and p.inactive_notice_at < now() - interval '30 days'
      and not exists (select 1 from public.subscriptions s where s.user_id = p.id
                      and s.status in ('active', 'cancelled', 'grace') and s.expires_at > now())
    returning u.id
  ) select count(*) into n from gone;
  return n;
end $$;
revoke execute on function public.purge_inactive_accounts() from public, anon, authenticated;

select cron.schedule('purge-inactive-3y', '37 3 * * *', 'select public.purge_inactive_accounts()');
