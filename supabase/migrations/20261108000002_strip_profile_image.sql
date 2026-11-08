-- 카카오가 넘겨주는 프로필 사진 주소는 저장하지 않는다 (앱에서 안 씀, 개인정보 최소 보관).
-- Supabase 카카오 연동은 profile_image를 항상 요청하므로, 받은 즉시 메타데이터에서 지운다.
create or replace function public.strip_profile_image() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if tg_table_name = 'users' then
    new.raw_user_meta_data := coalesce(new.raw_user_meta_data, '{}'::jsonb) - 'avatar_url' - 'picture' - 'profile_image' - 'thumbnail_image';
  else
    new.identity_data := coalesce(new.identity_data, '{}'::jsonb) - 'avatar_url' - 'picture' - 'profile_image' - 'thumbnail_image';
  end if;
  return new;
end $$;
revoke execute on function public.strip_profile_image from public, anon, authenticated;

drop trigger if exists strip_profile_image_users on auth.users;
create trigger strip_profile_image_users before insert or update of raw_user_meta_data on auth.users
  for each row execute function public.strip_profile_image();

drop trigger if exists strip_profile_image_identities on auth.identities;
create trigger strip_profile_image_identities before insert or update of identity_data on auth.identities
  for each row execute function public.strip_profile_image();

-- 이미 저장된 것 정리
update auth.users set raw_user_meta_data = raw_user_meta_data - 'avatar_url' - 'picture' - 'profile_image' - 'thumbnail_image'
 where raw_user_meta_data ?| array['avatar_url','picture','profile_image','thumbnail_image'];
update auth.identities set identity_data = identity_data - 'avatar_url' - 'picture' - 'profile_image' - 'thumbnail_image'
 where identity_data ?| array['avatar_url','picture','profile_image','thumbnail_image'];
