import { useLocalSearchParams } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Platform, Pressable, StyleSheet, Text, useWindowDimensions, View, type LayoutChangeEvent, type NativeScrollEvent, type NativeSyntheticEvent } from 'react-native';
import Animated, { Easing, scrollTo, useAnimatedReaction, useAnimatedRef, useSharedValue, withTiming } from 'react-native-reanimated';
import { SafeAreaView } from 'react-native-safe-area-context';
import { scheduleOnRN } from 'react-native-worklets';

import { track } from '@/lib/analytics';
import { todayLabel } from '@/lib/dates';
import { GardenPage } from '@/screens/GardenPage';
import { RoomPage } from '@/screens/RoomPage';
import { YardPage } from '@/screens/YardPage';
import { useApp } from '@/state/app';
import { Seeds } from '@/ui/kit';
import type { Pager } from '@/ui/pager';
import { C } from '@/ui/theme';

// 한 화면에서 좌우로 넘기기: 텃밭 ← 방(홈) → 마당 (WORLD W1). 앱을 열면 방.
const PAGES = ['garden', 'room', 'yard'] as const;
const LABEL = { garden: '텃밭', room: '방', yard: '마당' } as const;
const HOME = 1;

export default function Spaces() {
  const { profile, balance, yard } = useApp();
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
  const pet = profile?.pet_name ?? '단짝';

  useEffect(() => { wSV.value = w; }, [w, wSV]);

  // 손가락으로 페이지 끌기 (방 여백·방 끝·마당 끝): 바깥 스크롤을 UI 스레드에서 손가락에 붙여 움직이고, 놓으면 부드럽게 맞춤.
  // (예전: JS에서 scrollTo → 끊기고, 손 떼기 전에 툭 넘어감. 2026-11-11 대표 피드백)
  const drv = useSharedValue(-1); // 끌거나 맞추는 중인 스크롤 위치, -1 = 안 함
  useAnimatedReaction(() => drv.value, (x) => { if (x >= 0) scrollTo(ref, x, 0, false); });
  const settleRef = useRef((n: number) => {
    drv.value = -1;
    if (n !== pageRef.current) {
      pageRef.current = n; setPageState(n);
      track('space_viewed', { space: PAGES[n] });
    }
  });
  const pager = useMemo<Pager>(() => {
    const settle = (n: number) => settleRef.current(n);
    return {
      drag: (dx) => {
        'worklet';
        const W = wSV.value;
        drv.value = Math.min(W * 2, Math.max(0, W * pageSV.value - dx));
      },
      end: (dx, vx, canceled) => {
        'worklet';
        const W = wSV.value, p = pageSV.value;
        const from = drv.value >= 0 ? drv.value : W * p;
        let n = canceled ? Math.round(from / W)
          : dx > W * 0.25 || vx > 500 ? p - 1 : dx < -W * 0.25 || vx < -500 ? p + 1 : p;
        n = Math.min(2, Math.max(0, n));
        pageSV.value = n;
        drv.value = from;
        const dur = 160 + 200 * Math.min(1, Math.abs(n * W - from) / Math.max(1, W));
        drv.value = withTiming(n * W, { duration: dur, easing: Easing.out(Easing.cubic) }, (fin) => { if (fin) scheduleOnRN(settle, n); });
      },
    };
  }, [drv, pageSV, wSV]);

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
    if (p !== page) {
      setPage(p);
      track('space_viewed', { space: PAGES[p] });
    }
  }

  const title = PAGES[page] === 'room' ? `${pet}의 방` : `${pet}의 ${LABEL[PAGES[page]]}`;

  return (
    <SafeAreaView style={st.wrap} edges={['top']}>
      <View style={st.header}>
        <View>
          <Text style={st.title}>{title}</Text>
          <Text style={st.date}>{todayLabel()}</Text>
        </View>
        <Seeds n={balance} />
      </View>
      <View style={st.tabs} accessibilityRole="tablist">
        {PAGES.map((p, i) => (
          <Pressable key={p} onPress={() => go(i)} style={[st.tab, page === i && st.tabOn]} accessibilityRole="tab" accessibilityState={{ selected: page === i }}>
            <Text style={[st.tabText, page === i && st.tabTextOn]}>{i === 0 ? '‹ ' : ''}{LABEL[p]}{i === 2 ? ' ›' : ''}</Text>
          </Pressable>
        ))}
      </View>
      <View style={{ flex: 1 }} onLayout={onLayout}>
        {w > 0 && (
          <Animated.ScrollView
            ref={ref} horizontal showsHorizontalScrollIndicator={false}
            // 웹 스냅(scroll-snap)은 손가락 따라 끌기(pager)를 바로 되돌려 버려서, 웹에선 바깥 스크롤을 쓸 때만 켬
            pagingEnabled={Platform.OS !== 'web' || page === 0 || (page === 2 && !yard.open)}
            // 방·열린 마당에서는 끌기 = 그 공간 둘러보기. 옆 공간으로는 위 탭, 방 여백, 방/마당 끝에서 더 끌어서 (pager, 2026-11-11)
            scrollEnabled={page === 0 || (page === 2 && !yard.open)}
            onMomentumScrollEnd={onScrollEnd} onScrollEndDrag={onScrollEnd} scrollEventThrottle={16}
            contentOffset={{ x: w * HOME, y: 0 }} keyboardShouldPersistTaps="handled">
            <View style={{ width: w }}><GardenPage /></View>
            <View style={{ width: w }}><RoomPage pager={pager} /></View>
            <View style={{ width: w, height: pageH || undefined }}><YardPage active={page === 2} pager={pager} /></View>
          </Animated.ScrollView>
        )}
      </View>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, maxWidth: 520, width: '100%', alignSelf: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 20, paddingTop: 8, paddingBottom: 6 },
  title: { fontSize: 22, fontWeight: '800', color: C.ink },
  date: { fontSize: 12, color: C.muted, marginTop: 2 },
  tabs: { flexDirection: 'row', justifyContent: 'center', gap: 6, paddingBottom: 8 },
  tab: { paddingVertical: 4, paddingHorizontal: 12, borderRadius: 999 },
  tabOn: { backgroundColor: '#fff' },
  tabText: { fontSize: 13, color: C.muted, fontWeight: '600' },
  tabTextOn: { color: C.ink },
});
