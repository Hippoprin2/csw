// 자동 생성: design/world/export/v1/manifest.json → 수정하지 말고 다시 생성 (scripts/gen_world.py)
// 단위: 캔버스 px (정사각형). 앱은 (카드 너비 / CANVAS) 배율로 곱한다.
export const CANVAS = 1080;
export type Rect = { x: number; y: number; w: number; h: number };
export type PetPlace = Rect & { z: number };

export const ROOM = {
  background: require('@/assets/world/room/background.webp'),
  pet: { x: 308.3, y: 495.9, w: 435.0, h: 580.0, z: 18 } as PetPlace,
  // z 오름차순으로 그린다. 같은 slot은 하나만 (방 소품은 owned.placed, sill_vase는 튤립/해바라기 중 하나)
  items: [
    { id: 'curtain', slot: 'window', z: 0, x: 432, y: 267, w: 489, h: 386, source: require('@/assets/world/room/curtain.webp') },
    { id: 'frame', slot: 'wall_left', z: 1, x: 280, y: 328, w: 143, h: 139, source: require('@/assets/world/room/frame.webp') },
    { id: 'wall_clock', slot: 'wall_right', z: 2, x: 912, y: 383, w: 114, h: 132, source: require('@/assets/world/room/wall_clock.webp') },
    { id: 'garland', slot: 'wall_top', z: 3, x: 86, y: 96, w: 849, h: 165, source: require('@/assets/world/room/garland.webp') },
    { id: 'string_lights', slot: 'wall_top', z: 4, x: 87, y: 97, w: 847, h: 147, source: require('@/assets/world/room/string_lights.webp') },
    { id: 'mobile', slot: 'ceiling', z: 5, x: 267, y: 0, w: 246, h: 538, source: require('@/assets/world/room/mobile.webp') },
    { id: 'bookshelf', slot: 'back_right', z: 6, x: 693, y: 565, w: 387, h: 515, source: require('@/assets/world/room/bookshelf.webp') },
    { id: 'bed', slot: 'back_left', z: 7, x: 0, y: 717, w: 650, h: 309, source: require('@/assets/world/room/bed.webp') },
    { id: 'radio_stand', slot: 'bedside', z: 8, x: 0, y: 715, w: 162, h: 257, source: require('@/assets/world/room/radio_stand.webp') },
    { id: 'aquarium', slot: 'bedside', z: 9, x: 0, y: 742, w: 162, h: 230, source: require('@/assets/world/room/aquarium.webp') },
    { id: 'easel', slot: 'lean', z: 10, x: 665, y: 694, w: 186, h: 309, source: require('@/assets/world/room/easel.webp') },
    { id: 'guitar', slot: 'lean', z: 11, x: 723, y: 558, w: 103, h: 325, source: require('@/assets/world/room/guitar.webp') },
    { id: 'harvest_tulip', slot: 'sill_vase', z: 12, x: 624, y: 461, w: 73, h: 199, source: require('@/assets/world/room/harvest_tulip.webp') },
    { id: 'harvest_sunflower', slot: 'sill_vase', z: 13, x: 624, y: 465, w: 75, h: 195, source: require('@/assets/world/room/harvest_sunflower.webp') },
    { id: 'harvest_strawberry', slot: 'sill_plate', z: 14, x: 684, y: 583, w: 78, h: 96, source: require('@/assets/world/room/harvest_strawberry.webp') },
    { id: 'harvest_sweet_potato', slot: 'sill_basket', z: 15, x: 730, y: 558, w: 119, h: 124, source: require('@/assets/world/room/harvest_sweet_potato.webp') },
    { id: 'rug', slot: 'floor_center', z: 16, x: 202, y: 971, w: 660, h: 72, source: require('@/assets/world/room/rug.webp') },
    { id: 'low_table', slot: 'floor_right', z: 17, x: 669, y: 878, w: 252, h: 176, source: require('@/assets/world/room/low_table.webp') },
    { id: 'lamp', slot: 'front_left', z: 19, x: 0, y: 619, w: 234, h: 410, source: require('@/assets/world/room/lamp.webp') },
    { id: 'squirrel', slot: 'front_center', z: 20, x: 215, y: 832, w: 177, h: 219, source: require('@/assets/world/room/squirrel.webp') },
    { id: 'cushion', slot: 'front_center', z: 21, x: 206, y: 968, w: 183, h: 78, source: require('@/assets/world/room/cushion.webp') },
    { id: 'big_plant', slot: 'front_right', z: 22, x: 787, y: 802, w: 226, h: 278, source: require('@/assets/world/room/big_plant.webp') },
  ],
};

export const GARDEN = {
  background: require('@/assets/world/garden/background.webp'),
  pet: { x: 303.4, y: 191.1, w: 435.0, h: 580.0, z: 0 } as PetPlace,
  cropSize: 600,
  // 그리는 순서: 배경 → 단짝 → 작물(0,1,2) → UI. 앱 plots.slot = index + 1
  plots: [
    { cropX: -120.6, cropY: 312.8, cx: 179.4, cy: 612.8, tap: { x: 10, y: 487, w: 338, h: 367 } },
    { cropX: 219.2, cropY: 363.5, cx: 519.2, cy: 663.5, tap: { x: 350, y: 538, w: 338, h: 367 } },
    { cropX: 559.0, cropY: 414.3, cx: 859.0, cy: 714.3, tap: { x: 690, y: 589, w: 338, h: 367 } },
  ],
  crops: {
    mound: require('@/assets/world/garden/crops/mound.webp'),
    strawberry_1: require('@/assets/world/garden/crops/strawberry_1.webp'),
    strawberry_1_doze: require('@/assets/world/garden/crops/strawberry_1_doze.webp'),
    strawberry_2: require('@/assets/world/garden/crops/strawberry_2.webp'),
    strawberry_2_doze: require('@/assets/world/garden/crops/strawberry_2_doze.webp'),
    strawberry_3: require('@/assets/world/garden/crops/strawberry_3.webp'),
    strawberry_3_doze: require('@/assets/world/garden/crops/strawberry_3_doze.webp'),
    sunflower_1: require('@/assets/world/garden/crops/sunflower_1.webp'),
    sunflower_1_doze: require('@/assets/world/garden/crops/sunflower_1_doze.webp'),
    sunflower_2: require('@/assets/world/garden/crops/sunflower_2.webp'),
    sunflower_2_doze: require('@/assets/world/garden/crops/sunflower_2_doze.webp'),
    sunflower_3: require('@/assets/world/garden/crops/sunflower_3.webp'),
    sunflower_3_doze: require('@/assets/world/garden/crops/sunflower_3_doze.webp'),
    sweet_potato_1: require('@/assets/world/garden/crops/sweet_potato_1.webp'),
    sweet_potato_1_doze: require('@/assets/world/garden/crops/sweet_potato_1_doze.webp'),
    sweet_potato_2: require('@/assets/world/garden/crops/sweet_potato_2.webp'),
    sweet_potato_2_doze: require('@/assets/world/garden/crops/sweet_potato_2_doze.webp'),
    sweet_potato_3: require('@/assets/world/garden/crops/sweet_potato_3.webp'),
    sweet_potato_3_doze: require('@/assets/world/garden/crops/sweet_potato_3_doze.webp'),
    tulip_1: require('@/assets/world/garden/crops/tulip_1.webp'),
    tulip_1_doze: require('@/assets/world/garden/crops/tulip_1_doze.webp'),
    tulip_2: require('@/assets/world/garden/crops/tulip_2.webp'),
    tulip_2_doze: require('@/assets/world/garden/crops/tulip_2_doze.webp'),
    tulip_3: require('@/assets/world/garden/crops/tulip_3.webp'),
    tulip_3_doze: require('@/assets/world/garden/crops/tulip_3_doze.webp'),
  } as Record<string, number>,
};

export const THUMBS: Record<string, number> = {
  aquarium: require('@/assets/world/thumbs/aquarium.webp'),
  bed: require('@/assets/world/thumbs/bed.webp'),
  big_plant: require('@/assets/world/thumbs/big_plant.webp'),
  bookshelf: require('@/assets/world/thumbs/bookshelf.webp'),
  curtain: require('@/assets/world/thumbs/curtain.webp'),
  cushion: require('@/assets/world/thumbs/cushion.webp'),
  easel: require('@/assets/world/thumbs/easel.webp'),
  frame: require('@/assets/world/thumbs/frame.webp'),
  garland: require('@/assets/world/thumbs/garland.webp'),
  guitar: require('@/assets/world/thumbs/guitar.webp'),
  lamp: require('@/assets/world/thumbs/lamp.webp'),
  low_table: require('@/assets/world/thumbs/low_table.webp'),
  mobile: require('@/assets/world/thumbs/mobile.webp'),
  radio_stand: require('@/assets/world/thumbs/radio_stand.webp'),
  rug: require('@/assets/world/thumbs/rug.webp'),
  squirrel: require('@/assets/world/thumbs/squirrel.webp'),
  string_lights: require('@/assets/world/thumbs/string_lights.webp'),
  wall_clock: require('@/assets/world/thumbs/wall_clock.webp'),
};

export const ICONS: Record<string, number> = {
  packet_strawberry: require('@/assets/world/icons/packet_strawberry.webp'),
  packet_sunflower: require('@/assets/world/icons/packet_sunflower.webp'),
  packet_sweet_potato: require('@/assets/world/icons/packet_sweet_potato.webp'),
  packet_tulip: require('@/assets/world/icons/packet_tulip.webp'),
  produce_strawberry: require('@/assets/world/icons/produce_strawberry.webp'),
  produce_sunflower: require('@/assets/world/icons/produce_sunflower.webp'),
  produce_sweet_potato: require('@/assets/world/icons/produce_sweet_potato.webp'),
  produce_tulip: require('@/assets/world/icons/produce_tulip.webp'),
};
