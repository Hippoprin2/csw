import { Image } from 'expo-image';
import { useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { ICONS } from '@/data/world';
import { YARD } from '@/data/yard';
import { api, friendlyError, ZONE_PRICE, type MemoryCard } from '@/lib/api';
import { track } from '@/lib/analytics';
import { CATS } from '@/lib/categories';
import { formatDay } from '@/lib/dates';
import { safetyKeywordHit } from '@/lib/safety';
import { isNight, treeStage } from '@/lib/yardGeo';
import { useApp } from '@/state/app';
import { Btn } from '@/ui/kit';
import { useSpaceSize } from '@/ui/layout';
import { Sheet, st as sheetSt } from '@/ui/Sheet';
import { C } from '@/ui/theme';
import { YardScene, type YardSceneHandle, type YardTap } from '@/ui/YardScene';

// 마당 = 첫 업데이트 (WORLD 7장 Y1~Y8, FEATURES 7장)
// - 열림: 기록한 날 누적 7일(서버 yard_state.open, 한 번 열리면 영구). 남은 날 카운트다운은 넣지 않음
// - 구역 2·3 구매(60·120), 소품 10개(상점), 추억 나무(기록한 날 10/30/60) 열매 = 지난 기록 카드(S11)
// - 손님 30%, 낮·밤 = 기기 시간 19~06시, 피크닉 매트에서 먹이기
// - 테스트 스위치(⚙︎): 테스터 계정(서버 testers) 또는 개발 빌드에서만 보임. 실제 동작은 서버가 테스터만 허용

const GUEST_CHANCE = 0.3;

export function YardPage({ active = true, onLeave }: { active?: boolean; onLeave?: () => void }) {
  const { yard, reloadYard, owned, items, balance, setBalance, crops, bag, reloadGarden, profile } = useApp();
  const pet = profile?.pet_name ?? '단짝';
  const showDev = yard.tester || __DEV__;
  const [devOpen, setDevOpen] = useState(false);
  const [nightOverride, setNightOverride] = useState<boolean | null>(null);
  const [clockNight, setClockNight] = useState(isNight());
  const [guests] = useState(() => Math.random() < GUEST_CHANCE);
  const [zoneAsk, setZoneAsk] = useState<number | null>(null);
  const [toast, setToast] = useState('');
  const [card, setCard] = useState<{ c: (MemoryCard & { skipped: string[] }) | null } | null>(null);
  const [picked, setPicked] = useState<number[]>([]);
  const [seen, setSeen] = useState<string[]>([]);
  const [feedOpen, setFeedOpen] = useState(false);
  const [bubble, setBubble] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const sceneRef = useRef<YardSceneHandle | null>(null);

  // 낮·밤: 1분마다 기기 시간 확인
  useEffect(() => {
    const t = setInterval(() => setClockNight(isNight()), 60000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(''), 2600);
    return () => clearTimeout(t);
  }, [toast]);
  useEffect(() => {
    if (!bubble) return;
    const t = setTimeout(() => setBubble(null), 3500);
    return () => clearTimeout(t);
  }, [bubble]);

  const yardIds = new Set(items.filter((i) => i.space === 'yard').map((i) => i.id));
  const ownedYard = owned.filter((o) => yardIds.has(o.item_id)).map((o) => o.item_id);
  const night = nightOverride ?? clockNight;
  const stage = treeStage(yard.record_days);
  const edibles = crops.filter((c) => c.kind === 'edible' && (bag[c.id] ?? 0) > 0);

  function onTap(t: YardTap) {
    if (t.kind === 'zone') { setErr(''); setZoneAsk(t.zone); return; }
    if (t.kind === 'forest') { setToast('숲은 구경만 할 수 있어'); return; }
    if (t.kind === 'item' && t.id === 'picnic_mat') { setErr(''); setFeedOpen(true); return; }
    if (t.kind === 'fruit') {
      // 단짝이 나무로 가서 열매를 보여주면 카드가 열림
      setPicked((p) => [...p, t.index]);
      const load = pickMemory(seen);
      sceneRef.current?.walkTo('tree', () => {
        load.then((c) => {
          if (c) setSeen((s) => [...s, ...c.skipped, c.id]);
          setTimeout(() => setCard({ c }), 700);
          track('memory_fruit', { found: !!c });
        });
      });
    }
  }

  async function buyZone(z: number) {
    setBusy(true); setErr('');
    try {
      const b = await api.buyZone(z);
      setBalance(b);
      await reloadYard();
      setZoneAsk(null);
      setBubble('새 길이다! 같이 가 보자');
      track('yard_zone_bought', { zone: z });
    } catch (e) {
      setErr(friendlyError(e));
    } finally {
      setBusy(false);
    }
  }

  function feed(cropId: string) {
    const c = crops.find((x) => x.id === cropId);
    if (!c) return;
    setFeedOpen(false);
    sceneRef.current?.walkTo('picnic_mat', async () => {
      try {
        await api.useHarvest(cropId);
        await reloadGarden();
        setBubble(`${c.name} 냠냠, 고마워!`);
        track('harvest_used', { crop: cropId, kind: c.kind, where: 'yard' });
      } catch (e) {
        setToast(friendlyError(e));
      }
    });
  }

  async function dev(fn: () => Promise<unknown>) {
    try {
      const r = await fn();
      if (typeof r === 'number') setBalance(r);
      await reloadYard();
    } catch (e) {
      setToast(friendlyError(e));
    }
  }

  const devPanel = showDev && (
    <>
      <Pressable style={st.gear} onPress={() => setDevOpen((v) => !v)} accessibilityLabel="테스트 스위치">
        <Text style={{ fontSize: 18 }}>⚙︎</Text>
      </Pressable>
      {devOpen && (
        <View style={st.panel}>
          <Text style={st.panelTitle}>테스트 스위치 (테스트 계정만)</Text>
          <DevBtn title={yard.dev_open ? '마당 바로 열기 끄기' : '마당 바로 열기'} onPress={() => dev(() => api.devYard(!yard.dev_open))} />
          <DevBtn title="구역 모두 열기" onPress={() => dev(api.devAllZones)} />
          <DevBtn title="씨앗 +500" onPress={() => dev(api.devSeeds)} />
          <DevBtn title={`밤/낮: ${nightOverride === null ? '기기 시간' : nightOverride ? '밤' : '낮'}`}
            onPress={() => setNightOverride((v) => (v === null ? !clockNight : v === clockNight ? null : !v))} />
          <Text style={st.panelNote}>기록한 날 {yard.record_days}일 · 나무 {stage}단계</Text>
        </View>
      )}
    </>
  );

  if (!yard.open) return <LockedYard devPanel={devPanel} />;

  const zoneInfo = zoneAsk ? YARD.walk.zones[String(zoneAsk)] : null;
  const price = zoneAsk ? ZONE_PRICE[zoneAsk] : 0;

  return (
    <View style={st.wrap}>
      <YardScene
        zones={yard.zones} items={ownedYard} stage={stage} fruitsHidden={picked} night={night} guests={guests}
        active={active} onTap={onTap} onLeave={onLeave} bubble={bubble} sceneRef={sceneRef}
      />
      {ownedYard.includes('picnic_mat') && edibles.length > 0 && (
        <Pressable style={st.feedBtn} onPress={() => { setErr(''); setFeedOpen(true); }} accessibilityRole="button">
          <Text style={st.feedText}>🧺 피크닉 매트에서 먹이기</Text>
        </Pressable>
      )}
      {toast ? <View style={st.toast} pointerEvents="none"><Text style={st.toastText}>{toast}</Text></View> : null}
      {devPanel}

      <Sheet visible={!!zoneAsk} onClose={() => setZoneAsk(null)}>
        <Text style={sheetSt.title}>{zoneInfo?.name_ko} 구역</Text>
        <Text style={sheetSt.body}>한 번 사면 계속 {pet}의 마당이야. 새 길로 같이 놀러 갈 수 있어.</Text>
        {err ? <Text style={st.err}>{err}</Text> : null}
        <View style={sheetSt.row}>
          <Btn title="다음에" kind="ghost" onPress={() => setZoneAsk(null)} style={{ flex: 1 }} />
          <Btn title={balance >= price ? `🌱 ${price}로 열기` : `씨앗 ${price}개 필요`} disabled={balance < price || busy}
            loading={busy} onPress={() => zoneAsk && buyZone(zoneAsk)} style={{ flex: 1 }} />
        </View>
      </Sheet>

      <Sheet visible={feedOpen} onClose={() => setFeedOpen(false)}>
        <Text style={sheetSt.title}>피크닉 매트에서 먹이기</Text>
        {edibles.length === 0 ? (
          <Text style={sheetSt.body}>텃밭에서 수확한 채소·열매가 있으면 여기서 같이 먹을 수 있어.</Text>
        ) : (
          <>
            <Text style={sheetSt.body}>매트로 가서 같이 먹어. 창턱 장식은 그대로 남아.</Text>
            {edibles.map((c) => (
              <View key={c.id} style={st.bagRow}>
                <Image source={ICONS[`produce_${c.id}`]} style={{ width: 40, height: 40 }} contentFit="contain" />
                <Text style={st.bagName}>{c.name} {bag[c.id]}개</Text>
                <Btn title="먹이기" onPress={() => feed(c.id)} />
              </View>
            ))}
          </>
        )}
      </Sheet>

      <Sheet visible={!!card} onClose={() => setCard(null)}>
        {card?.c ? (
          <>
            <Text style={st.cardKicker}>🍑 추억 열매</Text>
            <Text style={sheetSt.title}>
              {card.c.kind === 'month' ? '한 달 전 오늘, 너는 이걸 해냈어' : `${formatDay(card.c.win_date)}, 너는 이걸 해냈어`}
            </Text>
            <View style={[st.memo, { borderLeftColor: CATS[card.c.category].color }]}>
              <Text style={st.memoText}>{card.c.text}</Text>
              <Text style={st.memoMeta}>{formatDay(card.c.win_date)} · {CATS[card.c.category].name}</Text>
            </View>
          </>
        ) : (
          <>
            <Text style={st.cardKicker}>🍑 추억 열매</Text>
            <Text style={sheetSt.title}>아직 열매가 익는 중이야</Text>
            <Text style={sheetSt.body}>기록이 일주일쯤 지나면 열매에 담겨. 그때 꺼내 줄게.</Text>
          </>
        )}
        <Btn title="고마워" onPress={() => setCard(null)} />
      </Sheet>
    </View>
  );
}

// 추억 열매 기록: 서버가 '버틴 하루'를 빼고 고름. 힘든 마음(자해 표현)이 담긴 기록은 앱에서 한 번 더 걸러 다시 고른다
async function pickMemory(seen: string[]) {
  const skipped: string[] = [];
  for (let k = 0; k < 4; k++) {
    const c = await api.memoryCard([...seen, ...skipped]).catch(() => null);
    if (!c) return null;
    if (!safetyKeywordHit(c.text)) return { ...c, skipped };
    skipped.push(c.id);
  }
  return null;
}

function DevBtn({ title, onPress }: { title: string; onPress: () => void }) {
  return (
    <Pressable style={st.devBtn} onPress={onPress} accessibilityRole="button">
      <Text style={st.devBtnText}>{title}</Text>
    </Pressable>
  );
}

function LockedYard({ devPanel }: { devPanel: React.ReactNode }) {
  const { gardenSize } = useSpaceSize();
  return (
    <View style={st.wrap}>
      <View style={[st.yard, { width: gardenSize, height: gardenSize }]}>
        <View style={st.hedge} />
        <Text style={st.tree}>🌳</Text>
        <Text style={st.pond}>💧</Text>
        <View style={st.gate}>
          <Text style={st.gateIcon}>🚪</Text>
          <Text style={st.gateTitle}>기록한 날이 7일이 되면 열려</Text>
          <Text style={st.gateSub}>띄엄띄엄이어도 괜찮아. 문 너머로 연못이 살짝 보여</Text>
        </View>
      </View>
      {devPanel}
    </View>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg },
  yard: { alignSelf: 'center', borderRadius: 28, overflow: 'hidden', backgroundColor: '#d7ecd0' },
  hedge: { position: 'absolute', left: 0, right: 0, top: 0, height: '26%', backgroundColor: '#a9d29b' },
  tree: { position: 'absolute', right: 24, top: '12%', fontSize: 64, opacity: 0.6 },
  pond: { position: 'absolute', left: 40, bottom: 40, fontSize: 48, opacity: 0.5 },
  gate: { position: 'absolute', left: 30, right: 30, top: '34%', backgroundColor: '#fffaf2ee', borderRadius: 22, padding: 18, alignItems: 'center' },
  gateIcon: { fontSize: 40, marginBottom: 6 },
  gateTitle: { fontSize: 18, fontWeight: '800', color: C.ink },
  gateSub: { fontSize: 13, color: C.muted, marginTop: 4, textAlign: 'center' },
  gear: { position: 'absolute', right: 26, top: 10, width: 34, height: 34, borderRadius: 17, backgroundColor: '#ffffffcc', alignItems: 'center', justifyContent: 'center' },
  panel: { position: 'absolute', right: 26, top: 50, width: 210, backgroundColor: '#fff', borderRadius: 16, padding: 12, gap: 6, borderWidth: 1, borderColor: C.line },
  panelTitle: { fontSize: 12, fontWeight: '700', color: C.muted, marginBottom: 2 },
  panelNote: { fontSize: 11, color: C.muted, marginTop: 2 },
  devBtn: { backgroundColor: C.bg, borderRadius: 10, paddingVertical: 8, paddingHorizontal: 10 },
  devBtnText: { fontSize: 13, fontWeight: '600', color: C.ink },
  feedBtn: { position: 'absolute', left: 30, bottom: 26, backgroundColor: '#fffffff0', borderRadius: 14, paddingVertical: 9, paddingHorizontal: 13 },
  feedText: { fontSize: 14, fontWeight: '700', color: C.ink },
  toast: { position: 'absolute', left: 40, right: 40, bottom: 80, backgroundColor: '#3a3530e6', borderRadius: 14, padding: 12, alignItems: 'center' },
  toastText: { color: '#fff', fontSize: 14, fontWeight: '600' },
  bagRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 10 },
  bagName: { flex: 1, fontSize: 15, color: C.ink, fontWeight: '600' },
  err: { color: '#c0392b', fontSize: 13, marginBottom: 10 },
  cardKicker: { fontSize: 13, color: C.muted, fontWeight: '700', marginBottom: 4 },
  memo: { backgroundColor: '#fff', borderRadius: 16, borderLeftWidth: 5, padding: 16, marginBottom: 16 },
  memoText: { fontSize: 18, color: C.ink, fontWeight: '600', lineHeight: 26 },
  memoMeta: { fontSize: 12, color: C.muted, marginTop: 8 },
});
