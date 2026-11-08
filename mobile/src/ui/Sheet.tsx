import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import { Btn } from './kit';
import { C } from './theme';

// 웹에서도 동작하는 확인 창 (Alert.alert는 웹에서 버튼이 안 나옴)
export function Sheet({ visible, onClose, children }: { visible: boolean; onClose: () => void; children: React.ReactNode }) {
  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <Pressable style={st.backdrop} onPress={onClose} accessibilityLabel="닫기">
        <Pressable style={st.sheet} onPress={() => {}}>{children}</Pressable>
      </Pressable>
    </Modal>
  );
}

export function Confirm({ visible, title, body, confirm, danger, onConfirm, onCancel }: {
  visible: boolean; title: string; body?: string; confirm: string; danger?: boolean; onConfirm: () => void; onCancel: () => void;
}) {
  return (
    <Sheet visible={visible} onClose={onCancel}>
      <Text style={st.title}>{title}</Text>
      {body ? <Text style={st.body}>{body}</Text> : null}
      <View style={st.row}>
        <Btn title="취소" kind="ghost" onPress={onCancel} style={{ flex: 1 }} />
        <Btn title={confirm} kind={danger ? 'danger' : 'primary'} onPress={onConfirm} style={{ flex: 1 }} />
      </View>
    </Sheet>
  );
}

export const st = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: '#0006', justifyContent: 'center', padding: 24 },
  sheet: { backgroundColor: C.bg, borderRadius: 24, padding: 20, maxWidth: 420, width: '100%', alignSelf: 'center' },
  title: { fontSize: 18, fontWeight: '800', color: C.ink, marginBottom: 8 },
  body: { fontSize: 14, color: C.muted, lineHeight: 20, marginBottom: 16 },
  row: { flexDirection: 'row', gap: 8, marginTop: 4 },
});
