-- '공부·일'을 공부(study)와 업무(work)로 분리 (STATUS 결정 2026-11-08). 기존 study 기록은 그대로 둔다.
alter table public.wins drop constraint if exists wins_category_check;
alter table public.wins add constraint wins_category_check
  check (category in ('tidy','move','study','work','eat','care','people','cheer'));
