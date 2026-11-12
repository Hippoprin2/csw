import { Tabs } from 'expo-router';
import type { BottomTabBarProps } from 'expo-router/tabs';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Icon, type IconName } from '@/ui/Icon';
import { C, H, R } from '@/ui/theme';

// 화면 아래에 떠 있는 흰 알약 탭 바 (좌우 16, 아래 24, 높이 68). 활성 탭만 민트 알약 배경 (A 포근한 창, 2026-11-13)
const ICON: Record<string, IconName> = { index: 'home', jar: 'jar', shop: 'plant', settings: 'gear' };

function FloatingTabBar({ state, descriptors, emitter, navigateToTab }: BottomTabBarProps) {
  const insets = useSafeAreaInsets();
  return (
    <View style={[st.bar, { bottom: Math.max(24, insets.bottom + 4) }]} accessibilityRole="tablist">
      {state.routes.map((route, i) => {
        const focused = state.index === i;
        const label = descriptors[route.key].options.title ?? route.name;
        const color = focused ? C.accentInk : C.muted;
        const onPress = () => {
          const ev = emitter.emit({ type: 'tabPress', target: route.key, canPreventDefault: true });
          if (!focused && !ev.defaultPrevented) navigateToTab(route.key);
        };
        return (
          <Pressable key={route.key} onPress={onPress} style={[st.item, focused && st.itemOn]}
            accessibilityRole="tab" accessibilityState={{ selected: focused }} accessibilityLabel={label}>
            <Icon name={ICON[route.name] ?? 'home'} size={22} color={color} stroke={focused ? 2 : 1.8} />
            <Text style={[st.label, { color }, focused && { fontWeight: '800' }]}>{label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export default function TabLayout() {
  return (
    <Tabs
      tabBar={(props) => <FloatingTabBar {...props} />}
      screenOptions={{ headerShown: false, sceneStyle: { backgroundColor: C.bg } }}>
      <Tabs.Screen name="index" options={{ title: '방' }} />
      <Tabs.Screen name="jar" options={{ title: '유리병' }} />
      <Tabs.Screen name="shop" options={{ title: '꾸미기' }} />
      <Tabs.Screen name="settings" options={{ title: '설정' }} />
    </Tabs>
  );
}

const st = StyleSheet.create({
  bar: {
    position: 'absolute', left: 16, right: 16, height: H.tab, maxWidth: 488, alignSelf: 'center',
    flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 8,
    backgroundColor: C.card, borderRadius: R.pill,
    shadowColor: '#4A3226', shadowOpacity: 0.12, shadowRadius: 18, shadowOffset: { width: 0, height: 6 }, elevation: 8,
  },
  item: { flex: 1, height: 52, borderRadius: R.pill, alignItems: 'center', justifyContent: 'center', gap: 2 },
  itemOn: { backgroundColor: C.accentBg },
  label: { fontSize: 11, fontWeight: '600' },
});
