import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Image } from 'expo-image';

import { THUMBS } from '@/data/world';
import { api, friendlyError } from '@/lib/api';
import { track } from '@/lib/analytics';
import { useApp } from '@/state/app';
import { H, Seeds, Sub } from '@/ui/kit';
import { C } from '@/ui/theme';

// 소품 상점. 방: 소품마다 정해진 자리, 같은 자리 소품은 바꿔 끼우기(WORLD W3)
// 마당(WORLD 7장): 소품 10개, 자리 1개씩(바꿔 끼우기 없음), 마당이 열려야 살 수 있음. 산 소품만 마당에 보임
export default function Shop() {
  const { items, owned, balance, setBalance, profile, celebrate, reloadRoom, yard } = useApp();
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState('');

  const ownedMap = new Map(owned.map((o) => [o.item_id, o.placed]));
  const slotCount = (slot: string) => items.filter((i) => i.slot === slot && ownedMap.has(i.id)).length;
  const roomItems = items.filter((i) => i.space === 'room');
  const yardItems = items.filter((i) => i.space === 'yard');

  async function buy(id: string) {
    const it = items.find((i) => i.id === id);
    setBusy(id); setErr('');
    try {
      const b = await api.buy(id);
      setBalance(b);
      await reloadRoom();
      track('item_bought', { item: id });
      if (it?.space === 'yard') {
        router.navigate({ pathname: '/', params: { space: 'yard' } });
        return;
      }
      celebrate({ kind: 'cheer', itemId: id, line: `${it?.name ?? '선물'} 고마워! 방이 더 좋아졌어` });
      router.navigate('/');
    } catch (e) {
      setErr(friendlyError(e));
    } finally {
      setBusy(null);
    }
  }

  async function place(id: string) {
    setBusy(id); setErr('');
    try {
      await api.placeItem(id);
      await reloadRoom();
      track('item_placed', { item: id });
      const it = items.find((i) => i.id === id);
      celebrate({ kind: 'cheer', itemId: id, line: `${it?.name}(으)로 바꿨어!` });
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
        <Sub>
          기록할 때마다 씨앗 3개. 산 물건은 {profile?.pet_name ?? '단짝'} 방 제자리에 놓여요. 같은 자리 물건은 눌러서 바꿔 놓을 수 있어요.
        </Sub>
        {err ? <Text style={st.err}>{err}</Text> : null}
        <View style={st.grid}>
          {roomItems.map((it) => {
            const own = ownedMap.has(it.id);
            const placed = ownedMap.get(it.id) === true;
            const swappable = own && !placed;
            const can = (!own && balance >= it.price) || swappable;
            const label = placed ? (slotCount(it.slot) > 1 ? '놓여 있음' : '방에 있음') : swappable ? '바꿔 놓기' : `씨앗 ${it.price}`;
            return (
              <Pressable key={it.id} disabled={!can || !!busy} onPress={() => (swappable ? place(it.id) : buy(it.id))}
                style={({ pressed }) => [st.item, placed && { opacity: 0.55 }, pressed && { transform: [{ scale: 0.97 }] }]}
                accessibilityRole="button" accessibilityLabel={`${it.name} ${label}`} accessibilityState={{ disabled: !can }}>
                <Image source={THUMBS[it.id]} style={st.thumb} contentFit="contain" accessibilityIgnoresInvertColors />
                <Text style={st.name}>{it.name}</Text>
                <Text style={[st.price, !own && !can && { color: C.muted }, swappable && { color: C.accent }]}>{label}</Text>
              </Pressable>
            );
          })}
        </View>
        <View style={st.yardHead}>
          <H>마당 꾸미기</H>
        </View>
        <Sub>{yard.open ? '산 물건은 마당 제자리에 놓여요. 단짝이 가서 놀기도 해요.' : '마당이 열리면 살 수 있어요.'}</Sub>
        <View style={[st.grid, !yard.open && { opacity: 0.5 }]}>
          {yardItems.map((it) => {
            const own = ownedMap.has(it.id);
            const can = yard.open && !own && balance >= it.price;
            const label = own ? '마당에 있음' : `씨앗 ${it.price}`;
            return (
              <Pressable key={it.id} disabled={!can || !!busy} onPress={() => buy(it.id)}
                style={({ pressed }) => [st.item, own && { opacity: 0.55 }, pressed && { transform: [{ scale: 0.97 }] }]}
                accessibilityRole="button" accessibilityLabel={`${it.name} ${label}`} accessibilityState={{ disabled: !can }}>
                <Image source={THUMBS[it.id]} style={st.thumb} contentFit="contain" accessibilityIgnoresInvertColors />
                <Text style={st.name}>{it.name}</Text>
                <Text style={[st.price, !own && !can && { color: C.muted }]}>{label}</Text>
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
  thumb: { width: 72, height: 72, marginBottom: 4 },
  name: { fontSize: 13, fontWeight: '600', color: C.ink },
  price: { fontSize: 12, color: C.seed, fontWeight: '700', marginTop: 3 },
  yardHead: { marginTop: 28 },
  err: { color: '#c0392b', fontSize: 13, marginBottom: 10 },
});
