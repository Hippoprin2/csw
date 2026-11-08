import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api, friendlyError } from '@/lib/api';
import { track } from '@/lib/analytics';
import { useApp } from '@/state/app';
import { H, Seeds, Sub } from '@/ui/kit';
import { C } from '@/ui/theme';

export default function Shop() {
  const { items, owned, setOwned, balance, setBalance, profile, celebrate } = useApp();
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState('');

  async function buy(id: string) {
    setBusy(id); setErr('');
    try {
      const b = await api.buy(id);
      setBalance(b);
      setOwned((o) => [...o, id]);
      track('item_bought', { item: id });
      const it = items.find((i) => i.id === id);
      celebrate({ itemId: id, line: `${it?.name ?? '선물'} 고마워! 방이 더 좋아졌어` });
      router.navigate('/');
    } catch (e) {
      setErr(friendlyError(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <SafeAreaView style={st.wrap} edges={['top']}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <H>방 꾸미기</H>
          <Seeds n={balance} />
        </View>
        <Sub>기록할 때마다 씨앗 3개. 산 물건은 {profile?.pet_name ?? '꼬마하마'} 방에 놓여요.</Sub>
        {err ? <Text style={st.err}>{err}</Text> : null}
        <View style={st.grid}>
          {items.map((it) => {
            const own = owned.includes(it.id);
            const can = !own && balance >= it.price;
            return (
              <Pressable key={it.id} disabled={!can || !!busy} onPress={() => buy(it.id)}
                style={({ pressed }) => [st.item, own && { opacity: 0.5 }, pressed && { transform: [{ scale: 0.97 }] }]}
                accessibilityRole="button" accessibilityLabel={`${it.name} 씨앗 ${it.price}`} accessibilityState={{ disabled: !can }}>
                <Text style={st.emoji}>{it.emoji}</Text>
                <Text style={st.name}>{it.name}</Text>
                <Text style={[st.price, !own && !can && { color: C.muted }]}>{own ? '방에 있음' : `씨앗 ${it.price}`}</Text>
              </Pressable>
            );
          })}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, maxWidth: 520, width: '100%', alignSelf: 'center' },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  item: { width: '31%', flexGrow: 1, backgroundColor: '#fff', borderWidth: 1, borderColor: C.line, borderRadius: 18, paddingVertical: 14, paddingHorizontal: 8, alignItems: 'center' },
  emoji: { fontSize: 34, marginBottom: 6 },
  name: { fontSize: 13, fontWeight: '600', color: C.ink },
  price: { fontSize: 12, color: C.seed, fontWeight: '700', marginTop: 3 },
  err: { color: '#c0392b', fontSize: 13, marginBottom: 10 },
});
