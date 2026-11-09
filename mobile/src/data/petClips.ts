// 자동 생성: design/character/export/v1/manifest.json → 수정하지 말고 다시 생성 (scripts/gen_pet_clips.py)
export type ClipKey = 'idle' | 'tidy' | 'move' | 'study' | 'work' | 'eat' | 'care' | 'people' | 'cheer' | 'sit_in' | 'sit_loop' | 'sit_out';
export const PET_ASPECT = 800 / 600; // 높이 / 너비
export const PET_CLIPS: Record<ClipKey, { source: number; durationMs: number; loop: boolean }> = {
  idle: { source: require('@/assets/pet/hippo_idle.webp'), durationMs: 2000, loop: true },
  tidy: { source: require('@/assets/pet/hippo_tidy.webp'), durationMs: 2000, loop: false },
  move: { source: require('@/assets/pet/hippo_move.webp'), durationMs: 1667, loop: false },
  study: { source: require('@/assets/pet/hippo_study.webp'), durationMs: 2667, loop: false },
  work: { source: require('@/assets/pet/hippo_work.webp'), durationMs: 2667, loop: false },
  eat: { source: require('@/assets/pet/hippo_eat.webp'), durationMs: 2167, loop: false },
  care: { source: require('@/assets/pet/hippo_care.webp'), durationMs: 2500, loop: false },
  people: { source: require('@/assets/pet/hippo_people.webp'), durationMs: 2167, loop: false },
  cheer: { source: require('@/assets/pet/hippo_cheer.webp'), durationMs: 1667, loop: false },
  sit_in: { source: require('@/assets/pet/hippo_sit_in.webp'), durationMs: 1000, loop: false },
  sit_loop: { source: require('@/assets/pet/hippo_sit_loop.webp'), durationMs: 3000, loop: true },
  sit_out: { source: require('@/assets/pet/hippo_sit_out.webp'), durationMs: 833, loop: false },
};
export const PET_POSTER = require('@/assets/pet/hippo_idle_poster.png');
