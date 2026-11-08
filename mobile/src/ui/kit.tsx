import { ActivityIndicator, Linking, Pressable, StyleSheet, Text, View, type StyleProp, type TextStyle, type ViewStyle } from 'react-native';

import { HELP_LINES } from '@/lib/safety';
import { C, R } from './theme';

export function Btn({ title, onPress, disabled, kind = 'primary', loading, style }: {
  title: string; onPress: () => void; disabled?: boolean; kind?: 'primary' | 'ghost' | 'danger' | 'dark'; loading?: boolean; style?: StyleProp<ViewStyle>;
}) {
  const bg = { primary: C.accent, ghost: 'transparent', danger: '#d9534f', dark: C.ink }[kind];
  const fg = kind === 'ghost' ? C.ink : '#fff';
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      disabled={disabled || loading}
      style={({ pressed }) => [
        s.btn, { backgroundColor: bg, opacity: disabled ? 0.4 : 1, transform: [{ scale: pressed ? 0.97 : 1 }] },
        kind === 'ghost' && { borderWidth: 1, borderColor: C.line }, style,
      ]}>
      {loading ? <ActivityIndicator color={fg} /> : <Text style={[s.btnText, { color: fg }]}>{title}</Text>}
    </Pressable>
  );
}

export function Seeds({ n }: { n: number }) {
  return (
    <View style={s.seeds} accessibilityLabel={`씨앗 ${n}개`}>
      <View style={s.seedDot} />
      <Text style={s.seedText}>{n}</Text>
    </View>
  );
}

export function H({ children, style }: { children: React.ReactNode; style?: StyleProp<TextStyle> }) {
  return <Text style={[s.h, style]}>{children}</Text>;
}
export function Sub({ children, style }: { children: React.ReactNode; style?: StyleProp<TextStyle> }) {
  return <Text style={[s.sub, style]}>{children}</Text>;
}

export function Card({ children, style }: { children: React.ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[s.card, style]}>{children}</View>;
}

// 자해 표현 감지 시 안내 카드 (S5). 번호 누르면 바로 전화.
export function HelpLines() {
  return (
    <View style={{ gap: 8 }}>
      {HELP_LINES.map((h) => (
        <Pressable key={h.number} accessibilityRole="button" onPress={() => Linking.openURL(`tel:${h.number}`)} style={s.helpRow}>
          <View style={{ flex: 1 }}>
            <Text style={s.helpName}>{h.name}</Text>
            <Text style={s.helpNote}>{h.note}</Text>
          </View>
          <Text style={s.helpNum}>{h.number}</Text>
        </Pressable>
      ))}
    </View>
  );
}

export const s = StyleSheet.create({
  btn: { minHeight: 48, borderRadius: R.input, paddingHorizontal: 18, alignItems: 'center', justifyContent: 'center' },
  btnText: { fontWeight: '700', fontSize: 15 },
  seeds: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#fff', borderWidth: 1, borderColor: C.line, borderRadius: R.pill, paddingVertical: 6, paddingHorizontal: 12 },
  seedDot: { width: 12, height: 14, backgroundColor: C.seed, borderRadius: 7 },
  seedText: { fontWeight: '700', fontSize: 14, color: C.ink },
  h: { fontSize: 20, fontWeight: '800', color: C.ink, marginTop: 10, marginBottom: 4 },
  sub: { color: C.muted, fontSize: 13, marginBottom: 14, lineHeight: 19 },
  card: { backgroundColor: '#fff', borderRadius: R.card, padding: 16, borderWidth: 1, borderColor: C.line },
  helpRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: C.room, borderRadius: 14, paddingVertical: 12, paddingHorizontal: 14 },
  helpName: { fontSize: 14, fontWeight: '700', color: C.ink },
  helpNote: { fontSize: 12, color: C.muted, marginTop: 2 },
  helpNum: { fontSize: 18, fontWeight: '800', color: C.accent },
});
