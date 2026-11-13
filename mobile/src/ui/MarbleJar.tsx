import * as Haptics from 'expo-haptics';
import { router } from 'expo-router';
import { Image } from 'expo-image';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Animated, Easing, Platform, Pressable, StyleSheet, Text, View, type LayoutChangeEvent } from 'react-native';
import { GestureDetector, useCompetingGestures, usePanGesture, useTapGesture } from 'react-native-gesture-handler';

import type { Win } from '@/lib/api';
import { track } from '@/lib/analytics';
import { CATS, type Category } from '@/lib/categories';
import { formatDay } from '@/lib/dates';
import { store } from '@/lib/store';
import { useReduceMotion } from '@/lib/useReduceMotion';
import { useWinSheet } from '@/ui/WinSheet';
import { C, R } from '@/ui/theme';

// 유리병 + 구슬 쓸어 보기 (C9 N5, 시안 records_mock/sheet4.png)
// - 0.3초 꾹 누르면 시작(톡 진동). 그 전에 손가락이 움직이면 실패 → 화면 스크롤 그대로
// - 쓸어 가는 동안 손가락 아래 구슬이 바뀔 때마다 아주 약한 진동(selectionAsync) + 구슬 위쪽 말풍선(손가락에 안 가리게)
// - 손 떼면 마지막 구슬 말풍선 유지 → 말풍선 탭 = 크게 보기 / 빈 곳 탭 = 닫힘. 구슬 짧게 톡 = 같은 말풍선
// - 병 아래 "목록으로 보기" = 이 병 구슬 목록 (다 읽기·VoiceOver용)
// - 처음 안내 "구슬을 꾹 누른 채로 쓸어 봐" — 한 번 쓸어 보면 사라짐 (기기에 저장)
// wins: 넣은 순서(오래된 것 먼저). 병은 아래 줄부터 채움
const HINT_KEY = 'csw.marbleSwipeHintDone';
const LONG_PRESS_MS = 300;
const HIT_R = 22; // 구슬 지름 31 — 가장 가까운 구슬을 이 거리 안에서 고름 (빈틈에서도 이어지게 반지름보다 조금 크게)
const BUBBLE_W = 236;
const GAP = 8;

type Rect = { x: number; y: number; w: number; h: number };

// J1 병 그림 = (A) 둥근 방 유리장 병 (2026-11-13 대표 결정, 시안 design/features/jar_redesign/sheet3_roundA.png)
// 병 껍데기만 3D 렌더 2장(뒤 유리 jar_back + 앞 뚜껑·반사 jar_front, 800×1000) 사이에 앱이 3D 구슬 그림을 한 겹으로.
// 숨는 구슬 없음 → 쓸어 보기. 자리는 계산으로 (onLayout은 웹에서 GestureDetector 안 좌표가 어긋남) — 시안 sheet2.html과 같은 식
const JAR_W = 290, K = JAR_W / 800, JAR_H = Math.round(1000 * K);
const IN_X0 = 96 * K, IN_X1 = 704 * K, IN_YB = 918 * K; // 앞 유리면 안쪽 (렌더 좌표 → pt)
const M = 31, ROW_H = M * 0.88, PER_ROW = 7; // 가로 7 × 8줄 = 50 (병 1개 분량)
const START = IN_X0 + (IN_X1 - IN_X0 - PER_ROW * M) / 2;
const marbleRect = (i: number): Rect => {
  const row = Math.floor(i / PER_ROW), col = i % PER_ROW;
  return { x: START + col * M + (row % 2 ? M * 0.12 : -M * 0.12), y: IN_YB - M - row * ROW_H, w: M, h: M };
};
const JAR_BACK = require('@/assets/world/jar/jar_back.webp');
const JAR_FRONT = require('@/assets/world/jar/jar_front.webp');
const MARBLE: Record<Category, number> = {
  tidy: require('@/assets/world/jar/marble_tidy.webp'), move: require('@/assets/world/jar/marble_move.webp'),
  study: require('@/assets/world/jar/marble_study.webp'), work: require('@/assets/world/jar/marble_work.webp'),
  eat: require('@/assets/world/jar/marble_eat.webp'), care: require('@/assets/world/jar/marble_care.webp'),
  people: require('@/assets/world/jar/marble_people.webp'), cheer: require('@/assets/world/jar/marble_cheer.webp'),
  endure: require('@/assets/world/jar/marble_endure.webp'),
};

// 새로 들어온 구슬: 위에서 톡 떨어져 살짝 튀기 (방 팝과 같은 느낌). 처음 그릴 때 있던 구슬은 가만히
function Marble({ cat, r, on, drop }: { cat: Category; r: Rect; on: boolean; drop: boolean }) {
  const [y] = useState(() => new Animated.Value(drop ? -70 : 0));
  useEffect(() => {
    if (!drop) return;
    Animated.sequence([
      Animated.timing(y, { toValue: 0, duration: 320, easing: Easing.in(Easing.quad), useNativeDriver: true }),
      Animated.timing(y, { toValue: -7, duration: 110, easing: Easing.out(Easing.quad), useNativeDriver: true }),
      Animated.timing(y, { toValue: 0, duration: 120, easing: Easing.in(Easing.quad), useNativeDriver: true }),
    ]).start();
  }, [drop, y]);
  return (
    <Animated.View style={[st.marble, { left: r.x, top: r.y, transform: [{ translateY: y }, { scale: on ? 1.3 : 1 }] }, on && st.marbleOnBox]}>
      <Image source={MARBLE[cat]} style={st.marbleImg} />
      {on && <View style={st.marbleRing} />}
    </Animated.View>
  );
}

function haptic(kind: 'start' | 'tick') {
  if (Platform.OS === 'web') return; // 웹은 진동 없음
  (kind === 'start' ? Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light) : Haptics.selectionAsync()).catch(() => {});
}

export function MarbleJar({ wins, label, listHref, onScrollLock, onChange, empty }: {
  wins: Win[]; label: string; listHref?: string; onScrollLock?: (lock: boolean) => void;
  onChange?: (w: Win, deleted: boolean) => void; empty?: React.ReactNode;
}) {
  const { openWin } = useWinSheet();
  // 고른 구슬 + 그 자리 (이벤트 때 잰 값). 목록이 바뀌면(지움·새 기록) sig가 달라져 말풍선이 저절로 닫힘
  const [picked, setPicked] = useState<{ i: number; r: Rect; sig: string } | null>(null);
  const [hint, setHint] = useState(() => store.get(HINT_KEY) !== '1');
  const [boxW, setBoxW] = useState(0); // 병은 감싸는 칸 맨 위 가운데 (웹 onLayout 좌표가 GestureDetector 때문에 어긋나 계산으로)
  const [bubbleH, setBubbleH] = useState(74);
  const live = useRef({ sel: null as number | null, swiped: false });
  const reduce = useReduceMotion();
  // 처음 그릴 때 있던 구슬 id (이후 새로 생긴 것만 떨어지는 움직임)
  const [seen] = useState(() => new Set(wins.map((w) => w.id)));

  const sig = wins.map((w) => w.id).join(',');
  const sel = picked && picked.sig === sig ? picked.i : null;
  const close = () => { live.current.sel = null; setPicked(null); };

  function hit(x: number, y: number): number | null {
    let best: number | null = null, bd = HIT_R * HIT_R;
    wins.forEach((_, i) => {
      const r = marbleRect(i);
      const dx = x - (r.x + r.w / 2), dy = y - (r.y + r.h / 2), d = dx * dx + dy * dy;
      if (d <= bd) { bd = d; best = i; }
    });
    return best;
  }
  const fx = useRef({ hit: (_x: number, _y: number): number | null => null, pick: (_i: number | null, _tick: boolean) => {}, start: () => {}, end: () => {} });
  useEffect(() => { fx.current = {
    hit,
    pick: (i, tick) => {
      if (i === live.current.sel) return;
      if (i === null) return; // 구슬 사이 빈틈: 마지막 말풍선 유지
      if (i < 0) { close(); return; } // 짧게 톡 = 빈 곳이면 닫힘
      live.current.sel = i; setPicked({ i, r: marbleRect(i), sig });
      if (tick) haptic('tick');
    },
    start: () => {
      haptic('start'); onScrollLock?.(true);
      if (!live.current.swiped) {
        live.current.swiped = true; track('marble_swiped');
        if (hint) { setHint(false); store.set(HINT_KEY, '1'); }
      }
    },
    end: () => onScrollLock?.(false),
  }; });

  const pan = usePanGesture(useMemo(() => ({
    activateAfterLongPress: LONG_PRESS_MS, maxPointers: 1, runOnJS: true,
    onActivate: (e: { x: number; y: number }) => { fx.current.start(); fx.current.pick(fx.current.hit(e.x, e.y), false); },
    onUpdate: (e: { x: number; y: number }) => { fx.current.pick(fx.current.hit(e.x, e.y), true); },
    onFinalize: () => fx.current.end(),
  }), []));
  const tap = useTapGesture(useMemo(() => ({
    maxDistance: 8, runOnJS: true,
    onDeactivate: (e: { canceled: boolean; x: number; y: number }) => {
      if (e.canceled) return;
      const i = fx.current.hit(e.x, e.y);
      if (i === null) fx.current.pick(-1, false); else fx.current.pick(i, false);
    },
  }), []));
  const gesture = useCompetingGestures(pan, tap);

  const r = sel !== null && picked ? picked.r : null;
  const w = sel !== null ? wins[sel] : null;
  const bw = Math.min(BUBBLE_W, boxW || BUBBLE_W);
  const jarX = (boxW - JAR_W) / 2;
  const bLeft = r ? Math.max(0, Math.min(boxW - bw, jarX + r.x + r.w / 2 - bw / 2)) : 0;
  const bTop = r ? r.y - bubbleH - GAP : 0;

  return (
    <View
      style={st.wrap}
      onLayout={(e: LayoutChangeEvent) => setBoxW(e.nativeEvent.layout.width)}
    >
      {/* 말풍선이 떠 있을 때 병 밖 빈 곳을 누르면 닫힘 */}
      {sel !== null && <Pressable style={StyleSheet.absoluteFill} onPress={close} accessible={false} />}
      <GestureDetector gesture={gesture}>
        <View style={st.jar} accessible accessibilityLabel={label}>
          <Image source={JAR_BACK} style={StyleSheet.absoluteFill} contentFit="contain" />
          {wins.map((m, i) => (
            <Marble key={m.id} cat={m.category} r={marbleRect(i)} on={sel === i} drop={!reduce && !seen.has(m.id)} />
          ))}
          <Image source={JAR_FRONT} style={[StyleSheet.absoluteFill, st.front]} contentFit="contain" pointerEvents="none" />
        </View>
      </GestureDetector>

      {w && r && (
        <Pressable
          style={[st.bubble, { width: bw, left: bLeft, top: bTop }]}
          onLayout={(e) => { const h = Math.round(e.nativeEvent.layout.height); if (h !== bubbleH) setBubbleH(h); }}
          onPress={() => openWin(w, onChange)}
          accessibilityRole="button" accessibilityHint="눌러서 크게 보기"
        >
          <Text style={st.bMeta}>{formatDay(w.win_date)} · {CATS[w.category].name}</Text>
          <Text style={st.bText} numberOfLines={2}>{w.text}</Text>
          <Text style={st.bLink}>눌러서 크게 보기 ›</Text>
        </Pressable>
      )}

      {wins.length === 0 && empty}
      {hint && wins.length >= 2 && <Text style={st.hint}>구슬을 꾹 누른 채로 쓸어 봐</Text>}
      {listHref && wins.length > 0 && (
        <Pressable onPress={() => router.push(listHref as never)} style={st.listLink} accessibilityRole="link" hitSlop={8}>
          <Text style={st.listLinkText}>목록으로 보기</Text>
        </Pressable>
      )}
    </View>
  );
}

const st = StyleSheet.create({
  wrap: { alignSelf: 'stretch', alignItems: 'center', marginBottom: 8, zIndex: 2 },
  jar: { width: JAR_W, height: JAR_H },
  front: { zIndex: 4 },
  marble: { position: 'absolute', width: M, height: M },
  marbleImg: { width: M, height: M },
  marbleOnBox: { zIndex: 3 },
  marbleRing: { position: 'absolute', left: -2, top: -2, right: -2, bottom: -2, borderRadius: M, borderWidth: 2, borderColor: C.accentInk }, // 고른 구슬: 1.3배 + 초록 테 (시안 sheet2)
  bubble: { position: 'absolute', zIndex: 5, backgroundColor: C.bg, borderRadius: R.card, paddingVertical: 11, paddingHorizontal: 15, shadowColor: C.shadow, shadowOpacity: 0.16, shadowRadius: 14, shadowOffset: { width: 0, height: 4 }, elevation: 6 },
  bMeta: { fontSize: 11, color: C.muted, marginBottom: 3 },
  bText: { fontSize: 14, fontWeight: '800', color: C.ink, lineHeight: 19 },
  bLink: { fontSize: 12, color: C.accentInk, fontWeight: '700', marginTop: 4 },
  hint: { fontSize: 13, color: C.muted, marginTop: 8 },
  listLink: { marginTop: 8, paddingHorizontal: 8, paddingVertical: 2 },
  listLinkText: { fontSize: 13, color: C.accentInk, fontWeight: '700', textDecorationLine: 'underline' },
});
