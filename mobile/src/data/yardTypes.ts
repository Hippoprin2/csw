// 마당 export(manifest spaces.yard) 형식. 좌표는 큰 캔버스 px
export type Pt = [number, number];
export type Poly = Pt[];
export type RectArr = [number, number, number, number]; // x, y, w, h

export type YardSprite = { id?: string; file: string; x: number; y: number; w: number; h: number; sort_y?: number; note?: string; needs?: string };
export type YardItem = YardSprite & {
  id: string; price: number; name_ko: string; layer: 'ground' | 'pond' | 'sorted';
  sort_y: number; sort_line?: Poly; night_file?: string;
};
export type YardZone = {
  rect: RectArr; price: number | null; name_ko: string; note?: string;
  area: Poly | null; blocked?: Record<string, Poly>; gate?: Pt;
};
export type YardInteract = { stand: Pt; face: string; action: string; enter?: Pt; note?: string };

export type YardData = {
  canvas: [number, number];
  tile: number;
  px_per_unit: number;
  tiles: (YardSprite & { night_file: string })[];
  locks: Record<string, YardSprite>;
  items: YardItem[];
  bed_flowers: (YardSprite & { sort_y: number; spot: number; flower: string })[];
  tree: (YardSprite & { sort_y: number; stage: number; fruits: Pt[] })[];
  fruit: { file: string; size: [number, number]; note?: string };
  extras: Record<string, YardSprite & { anchor?: Pt }>;
  camera: { peek: number; follow_lerp: number; dead_zone: number; return_wait_s: number; return_s: number; zoom_min: number; [k: string]: unknown };
  night: { overlay: [number, number, number, number]; [k: string]: unknown };
  walk: {
    zones: Record<string, YardZone>;
    blocked: Record<string, Poly>;
    item_blocked: Record<string, Poly>;
    interact: Record<string, YardInteract>;
    home: Pt;
    pet: { feet_to_center: Pt; w: number; h: number; note?: string };
    [k: string]: unknown;
  };
  [k: string]: unknown;
};
