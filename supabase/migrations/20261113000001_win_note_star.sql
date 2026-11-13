-- 기록 다시 보기 C9 (2026-11-13 대표 결정, FEATURES C9)
-- N2: 크게 보기 시트의 "+ 한 줄 더 남기기" = 기록에 덧붙이는 메모 한 줄 (원문은 그대로). 자해 감지는 돌리지 않음(대표 결정)
-- M3: ☆ 다시 보고 싶은 기록. 씨앗·구슬 차등 없음 (표시만)
alter table public.wins add column if not exists note text;
alter table public.wins add column if not exists starred boolean not null default false;
alter table public.wins drop constraint if exists wins_note_len;
alter table public.wins add constraint wins_note_len check (note is null or char_length(note) between 1 and 200);

create index if not exists wins_user_starred on public.wins (user_id, win_date desc, created_at desc) where starred;
create index if not exists wins_user_cat on public.wins (user_id, category, win_date desc, created_at desc);

-- 메모: 빈 글자면 지움(null). 내 기록만. 씨앗·병·분류는 건드리지 않는다
create or replace function public.set_win_note(p_id uuid, p_note text)
returns public.wins
language plpgsql security definer set search_path = public as $$
declare w public.wins; n text := nullif(btrim(coalesce(p_note, '')), '');
begin
  if auth.uid() is null then raise exception 'not_authenticated'; end if;
  if n is not null and char_length(n) > 200 then raise exception 'too_long'; end if;
  update public.wins set note = n, updated_at = now()
   where id = p_id and user_id = auth.uid() returning * into w;
  if w.id is null then raise exception 'not_found'; end if;
  return w;
end $$;

-- ☆ 켜기/끄기
create or replace function public.set_win_star(p_id uuid, p_on boolean)
returns public.wins
language plpgsql security definer set search_path = public as $$
declare w public.wins;
begin
  if auth.uid() is null then raise exception 'not_authenticated'; end if;
  update public.wins set starred = coalesce(p_on, false), updated_at = now()
   where id = p_id and user_id = auth.uid() returning * into w;
  if w.id is null then raise exception 'not_found'; end if;
  return w;
end $$;

-- 분류별 기록 수 (유리병 탭 분류 칩 숫자) + ☆ 수
create or replace function public.win_counts()
returns json
language sql stable security definer set search_path = public as $$
  select json_build_object(
    'cats', coalesce((select json_object_agg(category, n) from (
      select category, count(*)::int as n from public.wins where user_id = auth.uid() group by category) c), '{}'::json),
    'starred', (select count(*)::int from public.wins where user_id = auth.uid() and starred)
  );
$$;

revoke execute on function public.set_win_note, public.set_win_star, public.win_counts from public, anon;
grant execute on function public.set_win_note, public.set_win_star, public.win_counts to authenticated;
