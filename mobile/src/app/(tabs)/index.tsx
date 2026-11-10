import { useEffect, useRef, useState } from 'react';
import { Platform, Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View, type LayoutChangeEvent, type NativeScrollEvent, type NativeSyntheticEvent } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { track } from '@/lib/analytics';
import { todayLabel } from '@/lib/dates';
import { GardenPage } from '@/screens/GardenPage';
import { RoomPage } from '@/screens/RoomPage';
import { YardPage } from '@/screens/YardPage';
import { useApp } from '@/state/app';
import { Seeds } from '@/ui/kit';
import { C } from '@/ui/theme';

// 한 화면에서 좌우로 넘기기: 텃밭 ← 방(홈) → 마당 (WORLD W1). 앱을 열면 방.
const PAGES = ['garden', 'room', 'yard'] as const;
const LABEL = { garden: '텃밭', room: '방', yard: '마당' } as const;
const HOME = 1;

export default function Spaces() {
  const { profile, balance } = useApp();
  const win = useWindowDimensions();
  const [measured, setMeasured] = useState(0);
  // onLayout이 안 오는 경우(웹에서 간헐적)를 대비해 화면 너비(최대 520)를 기본값으로 쓴다
  const w = measured || Math.min(win.width, 520);
  const [page, setPageState] = useState(HOME);
  const pageRef = useRef(HOME);
  const setPage = (p: number) => { pageRef.current = p; setPageState(p); };
  const ref = useRef<React.ComponentRef<typeof ScrollView>>(null);
  const pet = profile?.pet_name ?? '단짝';

  // 너비가 정해지거나 바뀌면 보고 있던 공간(처음엔 방)으로 맞춘다
  useEffect(() => {
    const t = setTimeout(() => ref.current?.scrollTo({ x: w * pageRef.current, animated: false }), 0);
    return () => clearTimeout(t);
  }, [w]);

  function onLayout(e: LayoutChangeEvent) {
    const nw = Math.round(e.nativeEvent.layout.width);
    if (nw && nw !== measured) {
      setMeasured(nw);
    }
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
          <ScrollView
            ref={ref} horizontal pagingEnabled showsHorizontalScrollIndicator={false}
            onMomentumScrollEnd={onScrollEnd} onScrollEndDrag={onScrollEnd} scrollEventThrottle={16}
            contentOffset={{ x: w * HOME, y: 0 }} keyboardShouldPersistTaps="handled">
            <View style={{ width: w }}><GardenPage /></View>
            <View style={{ width: w }}><RoomPage /></View>
            <View style={{ width: w }}><YardPage /></View>
          </ScrollView>
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
