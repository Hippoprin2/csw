import { KeyboardAvoidingView, Modal, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Btn } from './kit';
import { C, R } from './theme';

// 아래에서 올라오는 시트 (위 모서리 32 + 손잡이 막대, A 포근한 창 2026-11-13). 웹에서도 동작 (Alert.alert는 웹에서 버튼이 안 나옴)
export function Sheet({ visible, onClose, children }: { visible: boolean; onClose: () => void; children: React.ReactNode }) {
  const insets = useSafeAreaInsets();
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      {/* iOS: 시트 안 입력칸(메모 한 줄·기록 고치기)이 키보드에 가리지 않게 시트를 키보드 위로 올림 */}
      <KeyboardAvoidingView style={st.root} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} accessibilityLabel="닫기" />
        <View style={[st.sheet, { paddingBottom: 20 + insets.bottom }]}>
          <View style={st.handle} />
          {children}
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

// 확인 시트: 주 버튼(민트 알약, 위험 동작이면 위험색 글자) 위, 취소(글자 버튼) 아래
export function Confirm({ visible, title, body, confirm, danger, onConfirm, onCancel }: {
  visible: boolean; title: string; body?: string; confirm: string; danger?: boolean; onConfirm: () => void; onCancel: () => void;
}) {
  return (
    <Sheet visible={visible} onClose={onCancel}>
      <Text style={st.title}>{title}</Text>
      {body ? <Text style={st.body}>{body}</Text> : null}
      <View style={st.col}>
        <Btn title={confirm} kind={danger ? 'danger' : 'primary'} onPress={onConfirm} />
        <Btn title="취소" kind="ghost" onPress={onCancel} />
      </View>
    </Sheet>
  );
}

export const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.scrim, justifyContent: 'flex-end' },
  sheet: { backgroundColor: C.bg, borderTopLeftRadius: R.sheet, borderTopRightRadius: R.sheet, paddingHorizontal: 22, paddingTop: 10, maxWidth: 520, width: '100%', alignSelf: 'center' },
  handle: { alignSelf: 'center', width: 40, height: 5, borderRadius: R.pill, backgroundColor: C.track, marginBottom: 18 },
  title: { fontSize: 19, fontWeight: '800', color: C.ink, marginBottom: 8 },
  body: { fontSize: 14, color: C.muted, lineHeight: 21, marginBottom: 18 },
  row: { flexDirection: 'row', gap: 8, marginTop: 4 },
  col: { gap: 4, marginTop: 4 },
});
