import { Tabs } from 'expo-router';
import { Text } from 'react-native';

import { C } from '@/ui/theme';

function TabIcon({ e, focused }: { e: string; focused: boolean }) {
  return <Text style={{ fontSize: 20, opacity: focused ? 1 : 0.45 }}>{e}</Text>;
}
const icon = (e: string) => function Icon({ focused }: { focused: boolean }) {
  return <TabIcon e={e} focused={focused} />;
};

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: C.ink,
        tabBarInactiveTintColor: C.muted,
        tabBarStyle: { backgroundColor: '#fffaf3', borderTopColor: C.line },
        tabBarLabelStyle: { fontSize: 12, fontWeight: '600' },
        sceneStyle: { backgroundColor: C.bg },
      }}>
      <Tabs.Screen name="index" options={{ title: '방', tabBarIcon: icon('🏠') }} />
      <Tabs.Screen name="jar" options={{ title: '유리병', tabBarIcon: icon('🫙') }} />
      <Tabs.Screen name="shop" options={{ title: '꾸미기', tabBarIcon: icon('🪴') }} />
      <Tabs.Screen name="settings" options={{ title: '설정', tabBarIcon: icon('⚙️') }} />
    </Tabs>
  );
}
