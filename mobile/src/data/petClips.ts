// 자동 생성: design/character/export/v1/manifest.json → 수정하지 말고 다시 생성 (scripts/gen_pet_clips.py)
export type ClipKey = 'idle' | 'tidy' | 'move' | 'study' | 'work' | 'eat' | 'care' | 'people' | 'cheer' | 'sit_in' | 'sit_loop' | 'sit_out' | 'eat_strawberry' | 'garden_idle' | 'garden_cheer' | 'walk_front' | 'walk_side' | 'walk_back' | 'sit_bench_in' | 'sit_bench_loop' | 'sit_bench_out' | 'sit_eat_in' | 'sit_eat_loop' | 'sit_eat_strawberry' | 'sit_eat_sweetpotato' | 'sit_eat_out' | 'lie_in' | 'lie_loop' | 'lie_out' | 'splash_in' | 'splash_loop' | 'splash_out' | 'sniff' | 'show_fruit';
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
  eat_strawberry: { source: require('@/assets/pet/hippo_eat_strawberry.webp'), durationMs: 2167, loop: false },
  garden_idle: { source: require('@/assets/pet/hippo_garden_idle.webp'), durationMs: 2000, loop: true },
  garden_cheer: { source: require('@/assets/pet/hippo_garden_cheer.webp'), durationMs: 1667, loop: false },
  walk_front: { source: require('@/assets/pet/hippo_walk_front.webp'), durationMs: 2000, loop: true },
  walk_side: { source: require('@/assets/pet/hippo_walk_side.webp'), durationMs: 2000, loop: true },
  walk_back: { source: require('@/assets/pet/hippo_walk_back.webp'), durationMs: 2000, loop: true },
  sit_bench_in: { source: require('@/assets/pet/hippo_sit_bench_in.webp'), durationMs: 1250, loop: false },
  sit_bench_loop: { source: require('@/assets/pet/hippo_sit_bench_loop.webp'), durationMs: 4000, loop: true },
  sit_bench_out: { source: require('@/assets/pet/hippo_sit_bench_out.webp'), durationMs: 1083, loop: false },
  sit_eat_in: { source: require('@/assets/pet/hippo_sit_eat_in.webp'), durationMs: 1000, loop: false },
  sit_eat_loop: { source: require('@/assets/pet/hippo_sit_eat_loop.webp'), durationMs: 4000, loop: true },
  sit_eat_strawberry: { source: require('@/assets/pet/hippo_sit_eat_strawberry.webp'), durationMs: 2333, loop: false },
  sit_eat_sweetpotato: { source: require('@/assets/pet/hippo_sit_eat_sweetpotato.webp'), durationMs: 2333, loop: false },
  sit_eat_out: { source: require('@/assets/pet/hippo_sit_eat_out.webp'), durationMs: 833, loop: false },
  lie_in: { source: require('@/assets/pet/hippo_lie_in.webp'), durationMs: 1667, loop: false },
  lie_loop: { source: require('@/assets/pet/hippo_lie_loop.webp'), durationMs: 4000, loop: true },
  lie_out: { source: require('@/assets/pet/hippo_lie_out.webp'), durationMs: 1500, loop: false },
  splash_in: { source: require('@/assets/pet/hippo_splash_in.webp'), durationMs: 1333, loop: false },
  splash_loop: { source: require('@/assets/pet/hippo_splash_loop.webp'), durationMs: 2000, loop: true },
  splash_out: { source: require('@/assets/pet/hippo_splash_out.webp'), durationMs: 1333, loop: false },
  sniff: { source: require('@/assets/pet/hippo_sniff.webp'), durationMs: 3000, loop: false },
  show_fruit: { source: require('@/assets/pet/hippo_show_fruit.webp'), durationMs: 3500, loop: false },
};
export const PET_FPS = 24;
// 마당 자리 동작 (manifest yard_actions): parts = in/loop/out 또는 한 번, stand = 발 위치(마당 캔버스 px)
export type YardAction = { parts: ClipKey[]; stand: [number, number]; enter?: [number, number]; eat?: ClipKey[] };
export const PET_YARD_ACTIONS: Record<string, YardAction> = {
  sit_bench: {"parts": ["sit_bench_in", "sit_bench_loop", "sit_bench_out"], "stand": [437.7, 911.6]},
  sit_eat: {"parts": ["sit_eat_in", "sit_eat_loop", "sit_eat_out"], "stand": [392.2, 1434.4], "eat": ["sit_eat_strawberry", "sit_eat_sweetpotato"]},
  lie: {"parts": ["lie_in", "lie_loop", "lie_out"], "stand": [207.7, 1231.6]},
  splash: {"parts": ["splash_in", "splash_loop", "splash_out"], "stand": [681.1, 1092.2], "enter": [429.1, 1063.6]},
  sniff: {"parts": ["sniff"], "stand": [845.5, 1402.3]},
  show_fruit: {"parts": ["show_fruit"], "stand": [288.6, 855.3]},
};
export const PET_POSTER = require('@/assets/pet/hippo_idle_poster.png');
