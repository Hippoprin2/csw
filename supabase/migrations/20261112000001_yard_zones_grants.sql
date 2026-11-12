-- 보안 정리 (2026-11-12 점검): yard_zones만 authenticated의 기본 권한(ALL)이 남아 있었다.
-- RLS에 쓰기 정책이 없어 악용은 안 되지만, 다른 표와 같은 규칙(전부 회수 후 필요한 것만)으로 맞춘다.
-- 쓰기는 buy_zone / dev_all_zones(security definer)로만.
revoke all on public.yard_zones from anon, authenticated;
grant select on public.yard_zones to authenticated;
