-- 2026-11-27 대표 결정: 민감정보 별도 동의(J4) 철회 — ChatGPT·Claude처럼 기록 속 건강·마음 내용은 일반 기록으로 다룸.
-- 동의 화면에서 민감정보 체크를 뺐으므로, 새로 받지 않은 동의 시각을 기록하지 않고 기록 권한도 일반 동의만 확인한다.
-- 이미 동의한 사용자의 sensitive_consented_at은 이력으로 그대로 둔다(컬럼 유지).

create or replace function public.give_consent(p_version text, p_onboard boolean default false) returns void
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then raise exception 'not_authenticated'; end if;
  if coalesce(p_version, '') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'invalid_version'; end if;
  update public.profiles
     set consented_at = now(), consent_version = p_version,
         onboarded_at = case when p_onboard then coalesce(onboarded_at, now()) else onboarded_at end
   where id = auth.uid();
end $$;
revoke execute on function public.give_consent(text, boolean) from public, anon;
grant execute on function public.give_consent(text, boolean) to authenticated;

create or replace function public.has_consent(p_uid uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.profiles where id = p_uid and consented_at is not null)
$$;
revoke execute on function public.has_consent(uuid) from public, anon, authenticated;
