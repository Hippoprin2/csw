import * as Haptics from 'expo-haptics';
import { router } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Platform, Pressable, StyleSheet, Text, View, type LayoutChangeEvent } from 'react-native';
import { GestureDetector, useCompetingGestures, usePanGesture, useTapGesture } from 'react-native-gesture-handler';

import type { Win } from '@/lib/api';
import { track } from '@/lib/analytics';
import { CATS } from '@/lib/categories';
import { formatDay } from '@/lib/dates';
import { store } from '@/lib/store';
import { useWinSheet } from '@/ui/WinSheet';
import { ART, C, R } from '@/ui/theme';

// 유리병 + 구슬 쓸어 보기 (C9 N5, 시안 records_mock/sheet4.png)
// - 0.3초 꾹 누르면 시작(톡 진동). 그 전에 손가락이 움직이면 실패 → 화면 스크롤 그대로
// - 쓸어 가는 동안 손가락 아래 구슬이 바뀔 때마다 아주 약한 진동(selectionAsync) + 구슬 위쪽 말풍선(손가락에 안 가리게)
// - 손 떼면 마지막 구슬 말풍선 유지 → 말풍선 탭 = 크게 보기 / 빈 곳 탭 = 닫힘. 구슬 짧게 톡 = 같은 말풍선
// - 병 아래 "목록으로 보기" = 이 병 구슬 목록 (다 읽기·VoiceOver용)
// - 처음 안내 "구슬을 꾹 누른 채로 쓸어 봐" — 한 번 쓸어 보면 사라짐 (기기에 저장)
// wins: 넣은 순서(오래된 것 먼저). 병은 아래 줄부터 채움
const HINT_KEY = 'csw.marbleSwipeHintDone';
const LONG_PRESS_MS = 300;
const HIT_R = 18; // 손가락 대비 구슬(14)이 작아서 가장 가까운 구슬을 이 거리 안에서 고름
const BUBBLE_W = 236;
const GAP = 8;

type Rect = { x: number; y: number; w: number; h: number };

// 병 안 구슬 자리는 계산으로 (onLayout은 웹에서 wrap-reverse 자식 좌표가 어긋남). 병 테두리 바깥 기준
const JAR_W = 150, JAR_H = 170, BORDER = 4, BORDER_TOP = 10, PAD = 9, M = 14, M_GAP = 3;
const PER_ROW = Math.floor((JAR_W - BORDER * 2 - PAD * 2 + M_GAP) / (M + M_GAP)); // 7
const marbleRect = (i: number): Rect => {
  const row = Math.floor(i / PER_ROW), col = i % PER_ROW;
  return { x: BORDER + PAD + col * (M + M_GAP), y: JAR_H - BORDER - PAD - M - row * (M + M_GAP), w: M, h: M };
};

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
        <View
          style={st.jar}
          accessible accessibilityLabel={label}
        >
          {wins.map((m, i) => (
            <View
              key={m.id}
              style={[st.marble, { backgroundColor: CATS[m.category].color }, sel === i && st.marbleOn]}
            />
          ))}
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
  // 병 그림 (유리병 자체는 화면 속 소품이라 선을 유지)
  jar: { width: JAR_W, height: JAR_H, borderWidth: BORDER, borderTopWidth: BORDER_TOP, borderColor: ART.jarLine, borderTopLeftRadius: 26, borderTopRightRadius: 26, borderBottomLeftRadius: 40, borderBottomRightRadius: 40, backgroundColor: ART.jarGlass, flexDirection: 'row', flexWrap: 'wrap-reverse', alignContent: 'flex-start', padding: PAD, gap: M_GAP, overflow: 'hidden' },
  // 50개가 다 들어가는 크기 (한 줄 7개 × 8줄)
  marble: { width: M, height: M, borderRadius: M / 2 },
  marbleOn: { transform: [{ scale: 1.5 }], borderWidth: 2, borderColor: C.ink }, // 유리병 바탕이 밝아 흰 테는 안 보임
  bubble: { position: 'absolute', zIndex: 5, backgroundColor: C.bg, borderRadius: R.card, paddingVertical: 11, paddingHorizontal: 15, shadowColor: C.shadow, shadowOpacity: 0.16, shadowRadius: 14, shadowOffset: { width: 0, height: 4 }, elevation: 6 },
  bMeta: { fontSize: 11, color: C.muted, marginBottom: 3 },
  bText: { fontSize: 14, fontWeight: '800', color: C.ink, lineHeight: 19 },
  bLink: { fontSize: 12, color: C.accentInk, fontWeight: '700', marginTop: 4 },
  hint: { fontSize: 13, color: C.muted, marginTop: 8 },
  listLink: { marginTop: 8, paddingHorizontal: 8, paddingVertical: 2 },
  listLinkText: { fontSize: 13, color: C.accentInk, fontWeight: '700', textDecorationLine: 'underline' },
});
