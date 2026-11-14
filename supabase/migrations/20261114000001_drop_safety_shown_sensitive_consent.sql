-- J2 (2026-11-13 대표 결정): 자해 안내 노출을 계정과 연결해 남기지 않는다.
-- 앱은 track('safety_shown') 를 더 이상 보내지 않음. 이미 쌓인 행 삭제 + 다시 못 쌓이게 막음. 익명 safety_daily(날짜·출처·개수)만 유지.
delete from public.app_events where name = 'safety_shown';
alter table public.app_events add constraint app_events_no_safety check (name <> 'safety_shown');

-- J4: 민감정보 별도 필수 동의 시각 (consented_at = 나머지 필수 동의)
alter table public.profiles add column if not exists sensitive_consented_at timestamptz;
grant update (sensitive_consented_at) on public.profiles to authenticated;
