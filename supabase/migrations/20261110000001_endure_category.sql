-- 9번째 분류 '버틴 하루'(endure): 해낸 일이 아니라 힘든 마음을 털어놓은 기록. 자해 표현이 감지된 기록도 여기로 (2026-11-10 대표 결정)
alter table public.wins drop constraint if exists wins_category_check;
alter table public.wins add constraint wins_category_check
  check (category in ('tidy','move','study','work','eat','care','people','cheer','endure'));
