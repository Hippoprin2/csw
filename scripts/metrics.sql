-- ============================================================================
-- CSW 사용 지표 (continue/kill 판단용)
-- ----------------------------------------------------------------------------
-- 목적: 가입(온보딩) 추이, D1/D7 재방문율, 주간 활성 기록자 수,
--       1인당 주간 기록 수(평균/중앙값), 첫 7일 내 3일 이상 기록한 비율.
-- 모든 날짜 집계는 KST(Asia/Seoul) 기준. public.kst_today() 참고.
-- 내부 테스트 계정(public.testers)과 스크립트로 생성한 시딩용 계정
-- (이메일이 'csw-test-%' 또는 'csw-ui-test%' 패턴, scripts/sb.py temp_user()가 만드는 계정)
-- 은 전부 제외한다.
-- 실행: psql 접속 불가 시 scripts/metrics.py 가 psycopg2로 이 파일을 그대로 실행한다.
-- ============================================================================

-- 분석 대상 유저 집합: 테스터 테이블 + 시딩용 이메일 패턴을 제외한 온보딩 완료 유저
with base_users as (
  select p.id as user_id,
         (p.onboarded_at at time zone 'Asia/Seoul')::date as onboard_day_kst,
         p.onboarded_at
  from public.profiles p
  join auth.users u on u.id = p.id
  where p.onboarded_at is not null
    and p.id not in (select user_id from public.testers)
    and u.email not like 'csw-test-%'
    and u.email not like 'csw-ui-test%'
),

-- 유저가 "방문/기록했다"고 볼 수 있는 모든 날(KST): app_events(app_open 등 전체 이벤트) OR wins 기록일
activity_days as (
  select user_id, (created_at at time zone 'Asia/Seoul')::date as day_kst
  from public.app_events
  where user_id in (select user_id from base_users)
  union
  select user_id, win_date as day_kst
  from public.wins
  where user_id in (select user_id from base_users)
)

-- ── 1) 일별 가입(온보딩) 수 ────────────────────────────────────────────────
select '1_signups_per_day' as metric, onboard_day_kst::text as key, count(*)::text as value
from base_users
group by onboard_day_kst

union all

-- ── 2) D1 재방문율: 온보딩일+1일에 활동 기록이 있는 유저 비율 ───────────────
select '2_retention', 'D1', round(
  100.0 * count(*) filter (
    where exists (
      select 1 from activity_days a
      where a.user_id = b.user_id and a.day_kst = b.onboard_day_kst + 1
    )
  ) / greatest(count(*), 1), 1
)::text
from base_users b

union all

-- ── 3) D7 재방문율: 온보딩일+7일에 활동 기록이 있는 유저 비율 ───────────────
select '3_retention', 'D7', round(
  100.0 * count(*) filter (
    where exists (
      select 1 from activity_days a
      where a.user_id = b.user_id and a.day_kst = b.onboard_day_kst + 7
    )
  ) / greatest(count(*), 1), 1
)::text
from base_users b

union all

-- ── 4) 주간 활성 기록자 수: 해당 주(월요일 시작, KST)에 wins를 1건 이상 남긴 유저 수 ─
select '4_weekly_active_recorders', date_trunc('week', w.win_date)::date::text,
       count(distinct w.user_id)::text
from public.wins w
where w.user_id in (select user_id from base_users)
group by date_trunc('week', w.win_date)

union all

-- ── 5) 1인당 주간 기록 수 (활성 기록자만, 평균/중앙값) ──────────────────────
select '5_records_per_active_user_per_week',
       'mean', round(avg(cnt), 2)::text
from (
  select user_id, date_trunc('week', win_date) as wk, count(*) as cnt
  from public.wins
  where user_id in (select user_id from base_users)
  group by user_id, date_trunc('week', win_date)
) t

union all

select '5_records_per_active_user_per_week',
       'median', (
         select percentile_cont(0.5) within group (order by cnt)
         from (
           select user_id, date_trunc('week', win_date) as wk, count(*) as cnt
           from public.wins
           where user_id in (select user_id from base_users)
           group by user_id, date_trunc('week', win_date)
         ) t2
       )::text

union all

-- ── 6) 첫 7일(온보딩일 포함 0~6일) 내 3일 이상 기록한 유저 비율 ─────────────
select '6_pct_users_3plus_recording_days_in_first7', 'pct', round(
  100.0 * count(*) filter (
    where (
      select count(distinct w.win_date)
      from public.wins w
      where w.user_id = b.user_id
        and w.win_date between b.onboard_day_kst and b.onboard_day_kst + 6
    ) >= 3
  ) / greatest(count(*), 1), 1
)::text
from base_users b

order by 1, 2;
