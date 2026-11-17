import { useEffect, useMemo, useState } from 'react';
import { KeyboardAvoidingView, Modal, Platform, Pressable, StyleSheet, Text, View, useWindowDimensions } from 'react-native';
import { GestureDetector, GestureHandlerRootView, usePanGesture } from 'react-native-gesture-handler';
import Animated, { Easing, useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { scheduleOnRN } from 'react-native-worklets';

import { Btn } from './kit';
import { C, R } from './theme';

const IN_MS = 260;
const OUT_MS = 200;
const CLOSE_DRAG = 90; // 이만큼(px) 아래로 끌거나
const CLOSE_VELOCITY = 700; // 이 속도(px/s)로 휙 내리면 닫힘

// 아래에서 올라오는 시트 (위 모서리 32 + 손잡이 막대, A 포근한 창 2026-11-13). 웹에서도 동작 (Alert.alert는 웹에서 버튼이 안 나옴)
// 2026-11-16 대표 피드백: 뒤 그림자는 제자리에서 한 번에 옅게 깔리고(페이드) 시트만 올라옴 + 아래로 끌어내리면 닫힘.
// (예전: Modal animationType="slide"라 그림자가 시트와 같이 밀려 올라오고, 끌어도 안 닫힘)
// locked: 끌기·바깥 누르기로 안 닫힘, 손잡이 없음 (⑥ 가입 시트처럼 꼭 골라야 하는 시트)
export function Sheet({ visible, onClose, children, locked }: { visible: boolean; onClose: () => void; children: React.ReactNode; locked?: boolean }) {
  const insets = useSafeAreaInsets();
  const { height: winH } = useWindowDimensions();
  const [mounted, setMounted] = useState(visible);
  if (visible && !mounted) setMounted(true); // 렌더 중 파생 (이펙트 안 setState 금지 규칙)
  const shown = useSharedValue(0); // 그림자 투명도 0~1
  const y = useSharedValue(winH); // 시트가 아래로 밀린 px
  const drag = useSharedValue(0); // 손가락으로 끌어내린 px

  useEffect(() => {
    if (!mounted) return;
    if (visible) {
      drag.set(0);
      shown.set(withTiming(1, { duration: IN_MS }));
      y.set(withTiming(0, { duration: IN_MS, easing: Easing.out(Easing.cubic) }));
    } else {
      shown.set(withTiming(0, { duration: OUT_MS }));
      y.set(withTiming(winH, { duration: OUT_MS, easing: Easing.in(Easing.cubic) }, (done) => { if (done) scheduleOnRN(setMounted, false); }));
    }
  }, [visible, mounted, winH, shown, y, drag]);

  const pan = usePanGesture(useMemo(() => ({
    enabled: !locked,
    activeOffsetY: [-10, 10] as [number, number], failOffsetX: [-20, 20] as [number, number], runOnJS: true,
    onUpdate: (e: { translationY: number }) => { if (Number.isFinite(e.translationY)) drag.set(Math.max(0, e.translationY)); },
    onDeactivate: (e: { translationY: number; velocityY: number }) => {
      if (e.translationY > CLOSE_DRAG || e.velocityY > CLOSE_VELOCITY) onClose();
      else drag.set(withTiming(0, { duration: 180 }));
    },
  }), [drag, onClose, locked]));

  const scrimStyle = useAnimatedStyle(() => ({ opacity: shown.value }));
  const sheetStyle = useAnimatedStyle(() => ({ transform: [{ translateY: y.value + drag.value }] }));

  if (!mounted) return null;
  return (
    <Modal visible transparent animationType="none" onRequestClose={locked ? () => {} : onClose} statusBarTranslucent>
      <GestureHandlerRootView style={{ flex: 1 }}>
        <Animated.View style={[StyleSheet.absoluteFill, st.scrim, scrimStyle]}>
          {!locked && <Pressable style={StyleSheet.absoluteFill} onPress={onClose} accessibilityLabel="닫기" />}
        </Animated.View>
        {/* iOS: 시트 안 입력칸(메모 한 줄·기록 고치기)이 키보드에 가리지 않게 시트를 키보드 위로 올림 */}
        <KeyboardAvoidingView style={st.root} behavior={Platform.OS === 'ios' ? 'padding' : undefined} pointerEvents="box-none">
          <GestureDetector gesture={pan}>
            <Animated.View style={[st.sheet, { paddingBottom: 20 + insets.bottom }, sheetStyle]}>
              {!locked && <View style={st.handle} />}
              {children}
            </Animated.View>
          </GestureDetector>
        </KeyboardAvoidingView>
      </GestureHandlerRootView>
    </Modal>
  );
}

// 확인 시트: 주 버튼(민트 알약, 위험 동작이면 위험색 글자) 위, 취소(글자 버튼) 아래
export function Confirm({ visible, title, body, confirm, danger, onConfirm, onCancel, link }: {
  visible: boolean; title: string; body?: string; confirm: string; danger?: boolean; onConfirm: () => void; onCancel: () => void;
  link?: { title: string; onPress: () => void }; // 본문 아래 보조 버튼 (예: 계정 삭제 전 구독 관리)
}) {
  return (
    <Sheet visible={visible} onClose={onCancel}>
      <Text style={st.title}>{title}</Text>
      {body ? <Text style={st.body}>{body}</Text> : null}
      <View style={st.col}>
        {link ? <Btn title={link.title} kind="ghost" onPress={link.onPress} /> : null}
        <Btn title={confirm} kind={danger ? 'danger' : 'primary'} onPress={onConfirm} />
        <Btn title="취소" kind="ghost" onPress={onCancel} />
      </View>
    </Sheet>
  );
}

export const st = StyleSheet.create({
  root: { flex: 1, justifyContent: 'flex-end' },
  scrim: { backgroundColor: C.scrim },
  sheet: { backgroundColor: C.bg, borderTopLeftRadius: R.sheet, borderTopRightRadius: R.sheet, paddingHorizontal: 22, paddingTop: 10, maxWidth: 520, width: '100%', alignSelf: 'center' },
  handle: { alignSelf: 'center', width: 40, height: 5, borderRadius: R.pill, backgroundColor: C.track, marginBottom: 18 },
  title: { fontSize: 19, fontWeight: '800', color: C.ink, marginBottom: 8 },
  body: { fontSize: 14, color: C.muted, lineHeight: 21, marginBottom: 18 },
  row: { flexDirection: 'row', gap: 8, marginTop: 4 },
  col: { gap: 4, marginTop: 4 },
});
