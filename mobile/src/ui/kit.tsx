import { ActivityIndicator, Linking, Pressable, StyleSheet, Text, View, type StyleProp, type TextStyle, type ViewStyle } from 'react-native';

import { HELP_LINES } from '@/lib/safety';
import { Icon, type IconName } from './Icon';
import { C, H as HT, R } from './theme';

// primary = 민트 알약 / soft = 옅은 면 알약 / ghost = 글자 버튼 / danger = 위험색 글자 버튼
export function Btn({ title, onPress, disabled, kind = 'primary', loading, style, icon }: {
  title: string; onPress: () => void; disabled?: boolean; kind?: 'primary' | 'soft' | 'ghost' | 'danger'; loading?: boolean; style?: StyleProp<ViewStyle>;
  icon?: IconName; // 글자 앞 선 아이콘 (예: 씨앗 잎)
}) {
  const bg = { primary: C.accent, soft: C.soft, ghost: 'transparent', danger: C.soft }[kind];
  const fg = { primary: C.white, soft: C.ink, ghost: C.muted, danger: C.danger }[kind];
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      disabled={disabled || loading}
      style={({ pressed }) => [
        s.btn, { backgroundColor: bg, opacity: disabled ? 0.4 : 1, transform: [{ scale: pressed ? 0.97 : 1 }] }, style,
      ]}>
      {loading ? <ActivityIndicator color={fg} /> : (
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          {icon && <Icon name={icon} size={16} color={fg} fill={icon === 'leaf' ? fg : undefined} />}
          <Text style={[s.btnText, { color: fg }]}>{title}</Text>
        </View>
      )}
    </Pressable>
  );
}

// 씨앗 = 초록 잎 아이콘 + 숫자 (크림 칩)
export function Seeds({ n, style }: { n: number; style?: StyleProp<ViewStyle> }) {
  return (
    <View style={[s.seeds, style]} accessibilityLabel={`씨앗 ${n}개`}>
      <Icon name="leaf" size={16} color={C.seed} fill={C.seed} />
      <Text style={s.seedText}>{n}</Text>
    </View>
  );
}

// 가격 표시: 잎 + 숫자 (글자 안에 넣는 작은 것)
export function Price({ n, color = C.ink }: { n: number; color?: string }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 3 }} accessibilityLabel={`씨앗 ${n}개`}>
      <Icon name="leaf" size={13} color={color === C.white ? C.white : C.seed} fill={color === C.white ? C.white : C.seed} />
      <Text style={{ fontSize: 13, fontWeight: '700', color }}>{n}</Text>
    </View>
  );
}

// 그림 위에 뜨는 크림 칩
export function FloatChip({ children, style }: { children: React.ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[s.floatChip, style]}>{children}</View>;
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

// ‹ 뒤로 (글자 버튼)
export function Back({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={label} hitSlop={8} style={s.back}>
      <Icon name="chevronLeft" size={20} color={C.muted} />
      <Text style={s.backText}>{label}</Text>
    </Pressable>
  );
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
  btn: { minHeight: HT.btn, borderRadius: R.pill, paddingHorizontal: 22, alignItems: 'center', justifyContent: 'center' },
  btnText: { fontWeight: '700', fontSize: 15 },
  seeds: { flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: C.chip, borderRadius: R.pill, height: HT.chip, paddingHorizontal: 14 },
  seedText: { fontWeight: '700', fontSize: 14, color: C.ink },
  floatChip: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: C.chip, borderRadius: R.pill, height: HT.chip, paddingHorizontal: 14 },
  h: { fontSize: 22, fontWeight: '800', color: C.ink, marginTop: 10, marginBottom: 4 },
  sub: { color: C.muted, fontSize: 14, marginBottom: 14, lineHeight: 20 },
  card: { backgroundColor: C.card, borderRadius: R.card, padding: 18 },
  back: { flexDirection: 'row', alignItems: 'center', alignSelf: 'flex-start', paddingVertical: 8, marginLeft: -4 },
  backText: { fontSize: 15, color: C.muted, fontWeight: '600' },
  helpRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: C.soft, borderRadius: R.card, paddingVertical: 14, paddingHorizontal: 18 },
  helpName: { fontSize: 14, fontWeight: '700', color: C.ink },
  helpNote: { fontSize: 12, color: C.muted, marginTop: 2 },
  helpNum: { fontSize: 18, fontWeight: '800', color: C.accentInk },
});
