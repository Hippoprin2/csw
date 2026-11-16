import { useLocalSearchParams } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Platform, StyleSheet, useWindowDimensions, View, type LayoutChangeEvent, type NativeScrollEvent, type NativeSyntheticEvent } from 'react-native';
import Animated, { Easing, scrollTo, useAnimatedReaction, useAnimatedRef, useSharedValue, withTiming } from 'react-native-reanimated';
import { scheduleOnRN, scheduleOnUI } from 'react-native-worklets';

import { track } from '@/lib/analytics';
import { GardenPage } from '@/screens/GardenPage';
import { RoomPage } from '@/screens/RoomPage';
import { YardPage } from '@/screens/YardPage';
import { useApp } from '@/state/app';
import type { Pager } from '@/ui/pager';
import { C } from '@/ui/theme';

// 한 화면에서 좌우로 넘기기: 텃밭 ← 방(홈) → 마당 (WORLD W1). 앱을 열면 방.
const PAGES = ['garden', 'room', 'yard'] as const;
const HOME = 1;

export default function Spaces() {
  const { yard } = useApp();
  const { space } = useLocalSearchParams<{ space?: string }>();
  const win = useWindowDimensions();
  const [measured, setMeasured] = useState(0);
  const [pageH, setPageH] = useState(0); // 마당 카드는 페이지 높이를 꽉 채움
  // onLayout이 안 오는 경우(웹에서 간헐적)를 대비해 화면 너비(최대 520)를 기본값으로 쓴다
  const w = measured || Math.min(win.width, 520);
  const [page, setPageState] = useState(HOME);
  const pageRef = useRef(HOME);
  const pageSV = useSharedValue(HOME), wSV = useSharedValue(w);
  const setPage = (p: number) => { pageRef.current = p; pageSV.value = p; setPageState(p); };
  const ref = useAnimatedRef<Animated.ScrollView>();

  useEffect(() => { wSV.value = w; }, [w, wSV]);

  // 손가락으로 페이지 끌기 (방 여백·방 끝·마당 끝): 바깥 스크롤을 UI 스레드에서 손가락에 붙여 움직이고, 놓으면 부드럽게 맞춤.
  // (예전: JS에서 scrollTo → 끊기고, 손 떼기 전에 툭 넘어감. 2026-11-11 대표 피드백)
  const drv = useSharedValue(-1); // 끌거나 맞추는 중인 스크롤 위치, -1 = 안 함
  // 한 번 끌기 = 한 페이지만: 끌기 시작한 페이지를 기억하고, 손 뗀 뒤 늦게 오는 끌기·두 번째 '놓기'는 무시
  // (마당 → 방으로 넘기면 방에 잠깐 섰다가 텃밭까지 넘어가던 문제, 2026-11-11)
  const from0 = useSharedValue(-1), settling = useSharedValue(false);
  useAnimatedReaction(() => drv.value, (x) => { if (Number.isFinite(x) && x >= 0) scrollTo(ref, x, 0, false); });
  const settleRef = useRef((n: number) => {
    drv.value = -1; settling.value = false;
    if (n !== pageRef.current) {
      pageRef.current = n; setPageState(n);
      track('space_viewed', { space: PAGES[n] });
    }
  });
  const pager = useMemo<Pager>(() => {
    const settle = (n: number) => settleRef.current(n);
    const dragUI = (dx: number) => {
        'worklet';
        if (settling.value || !Number.isFinite(dx)) return;
        if (from0.value < 0) from0.value = pageSV.value;
        const W = wSV.value, p = from0.value;
        // 바로 옆 페이지까지만 보임 (마당에서 미세하게 끌 때 텃밭이 한 프레임 튀던 문제, 2026-11-11 대표 영상)
        drv.value = Math.min(W * Math.min(2, p + 1), Math.max(W * Math.max(0, p - 1), W * p - dx));
    };
    const endUI = (dx: number, vx: number, canceled?: boolean) => {
        'worklet';
        if (from0.value < 0 || settling.value) return;
        if (!Number.isFinite(dx)) dx = 0;
        if (!Number.isFinite(vx)) vx = 0;
        const W = wSV.value, p = from0.value;
        from0.value = -1; settling.value = true;
        const from = drv.value >= 0 ? drv.value : W * p;
        let n = canceled ? Math.round(from / W)
          : dx > W * 0.25 || vx > 500 ? p - 1 : dx < -W * 0.25 || vx < -500 ? p + 1 : p;
        n = Math.min(2, Math.max(0, n));
        pageSV.value = n;
        drv.value = from;
        const dur = 160 + 200 * Math.min(1, Math.abs(n * W - from) / Math.max(1, W));
        drv.value = withTiming(n * W, { duration: dur, easing: Easing.out(Easing.cubic) }, (fin) => { if (fin) scheduleOnRN(settle, n); else settling.value = false; });
    };
    // 공유값은 UI 스레드에서만 읽고 써야 함: JS 스레드(방 그림·마당 끌기, runOnJS)에서 부르면 방금 쓴 값이 아직 안 보여서
    // 시작 페이지를 -1로 읽고 텃밭(0)으로 튀었음 (2026-11-11 대표 슬로모션 영상, 방 여백 끌기는 UI 스레드라 멀쩡했음)
    const onUI = () => { 'worklet'; return !!(globalThis as { _WORKLET?: boolean })._WORKLET; };
    return {
      drag: (dx) => { 'worklet'; if (onUI()) dragUI(dx); else scheduleOnUI(dragUI, dx); },
      end: (dx, vx, canceled) => { 'worklet'; if (onUI()) endUI(dx, vx, canceled); else scheduleOnUI(endUI, dx, vx, canceled); },
    };
  }, [drv, pageSV, wSV, from0, settling]);

  // 너비가 정해지거나 바뀌면 보고 있던 공간(처음엔 방)으로 맞춘다
  useEffect(() => {
    const t = setTimeout(() => ref.current?.scrollTo({ x: w * pageRef.current, animated: false }), 0);
    return () => clearTimeout(t);
  }, [w, ref]);

  // 마당 소품을 사면 상점에서 마당으로 보내 준다
  useEffect(() => {
    if (space !== 'yard') return;
    const t = setTimeout(() => go(2), 50);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 파라미터가 바뀔 때만
  }, [space]);

  function onLayout(e: LayoutChangeEvent) {
    const nw = Math.round(e.nativeEvent.layout.width);
    if (nw && nw !== measured) {
      setMeasured(nw);
    }
    const nh = Math.round(e.nativeEvent.layout.height);
    if (nh && nh !== pageH) setPageH(nh);
  }
  function onScrollEnd(e: NativeSyntheticEvent<NativeScrollEvent>) {
    if (!w) return;
    const p = Math.round(e.nativeEvent.contentOffset.x / w);
    if (p !== page) {
      setPage(p);
      track('space_viewed', { space: PAGES[p] });
    }
  }
  function go(p: number) {
    ref.current?.scrollTo({ x: w * p, animated: Platform.OS !== 'web' }); // 웹 부드러운 스크롤은 스냅과 겹쳐 중간에 멈출 때가 있음
    // 웹: 텃밭→마당처럼 두 칸 건너뛰면 스냅 설정이 바뀌는 렌더 뒤에 처음 위치로 돌아감 → 렌더 뒤 한 번 더 맞춘다
    if (Platform.OS === 'web') setTimeout(() => ref.current?.scrollTo({ x: w * p, animated: false }), 0);
    if (p !== page) {
      setPage(p);
      track('space_viewed', { space: PAGES[p] });
    }
  }

  const nav = { page, go };

  // 상단 머리글·공간 탭 없음: 그림이 화면 위를 꽉 채우고 칩·전환은 각 공간이 그림 위/판 안에 띄운다 (A 포근한 창, 2026-11-13)
  return (
    <View style={st.wrap}>
      <View style={{ flex: 1 }} onLayout={onLayout}>
        {w > 0 && (
          <Animated.ScrollView
            ref={ref} horizontal showsHorizontalScrollIndicator={false}
            // 웹 스냅(scroll-snap)은 손가락 따라 끌기(pager)를 바로 되돌려 버려서, 웹에선 바깥 스크롤을 쓸 때만 켬
            pagingEnabled={Platform.OS !== 'web' || page === 0 || (page === 2 && !yard.open)}
            // 방·열린 마당에서는 끌기 = 그 공간 둘러보기. 옆 공간으로는 판 안 전환·마당 '‹ 방' 손잡이, 방 여백, 방/마당 끝에서 더 끌어서 (pager, 2026-11-11)
            scrollEnabled={page === 0 || (page === 2 && !yard.open)}
            onMomentumScrollEnd={onScrollEnd} onScrollEndDrag={onScrollEnd} scrollEventThrottle={16}
            contentOffset={{ x: w * HOME, y: 0 }} keyboardShouldPersistTaps="handled">
            <View style={{ width: w }}><GardenPage nav={nav} /></View>
            <View style={{ width: w, height: pageH || undefined }}><RoomPage pager={pager} nav={nav} pageH={pageH} /></View>
            <View style={{ width: w, height: pageH || undefined }}><YardPage active={page === 2} pager={pager} nav={nav} /></View>
          </Animated.ScrollView>
        )}
      </View>
    </View>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, maxWidth: 520, width: '100%', alignSelf: 'center' },
});
