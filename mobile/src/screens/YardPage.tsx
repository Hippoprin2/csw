import { Image } from 'expo-image';
import { useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ICONS } from '@/data/world';
import { YARD, YARD_IMG } from '@/data/yard';
import { api, friendlyError, ZONE_PRICE, type MemoryCard } from '@/lib/api';
import { track } from '@/lib/analytics';
import { CATS } from '@/lib/categories';
import { formatDay } from '@/lib/dates';
import { safetyKeywordHit } from '@/lib/safety';
import { isNight, treeStage } from '@/lib/yardGeo';
import { useApp } from '@/state/app';
import { Icon } from '@/ui/Icon';
import { Btn } from '@/ui/kit';
import { RoomHandle, SpaceChips, type SpaceNav } from '@/ui/SpaceChrome';
import { Sheet, st as sheetSt } from '@/ui/Sheet';
import { C, H, R, TAB_SPACE } from '@/ui/theme';
import { YardScene, type YardSceneHandle, type YardTap } from '@/ui/YardScene';
import type { Pager } from '@/ui/pager';

// 마당 = 첫 업데이트 (WORLD 7장 Y1~Y8, FEATURES 7장)
// - 열림: 기록한 날 누적 7일(서버 yard_state.open, 한 번 열리면 영구). 남은 날 카운트다운은 넣지 않음
// - 구역 2·3 구매(60·120), 소품 10개(상점), 추억 나무(기록한 날 10/30/60) 열매 = 지난 기록 카드(S11)
// - 손님 30%, 낮·밤 = 기기 시간 19~06시, 피크닉 매트에서 먹이기
// - 마당 화면(A 포근한 창, 2026-11-13): 그림이 화면 전체, 판·공간 전환 없음. 위쪽 칩 2개 + '‹ 방' 손잡이 + 매트 버튼만
// - 테스트 스위치(설정 아이콘): 테스터 계정(서버 testers) 또는 개발 빌드에서만 보임. 실제 동작은 서버가 테스터만 허용

const GUEST_CHANCE = 0.3;

export function YardPage({ active = true, pager, nav }: { active?: boolean; pager?: Pager; nav?: SpaceNav }) {
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
  const insets = useSafeAreaInsets();
  const belowChips = insets.top + 8 + H.chip + 12;

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
    if (t.kind === 'item' && t.id === 'picnic_mat') {
      if (edibles.length) { setErr(''); setFeedOpen(true); } else sceneRef.current?.walkTo('picnic_mat'); // 먹을 게 없으면 매트에 앉아 쉼
      return;
    }
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
    // 매트에 앉아서 먹는 클립 (딸기 / 그 밖 = 고구마). 먹기 시작할 때 수확물을 씀
    const eat = cropId === 'strawberry' ? 'sit_eat_strawberry' : 'sit_eat_sweetpotato';
    sceneRef.current?.walkTo('picnic_mat', async () => {
      try {
        await api.useHarvest(cropId);
        await reloadGarden();
        setBubble(`${c.name} 냠냠, 고마워!`);
        track('harvest_used', { crop: cropId, kind: c.kind, where: 'yard' });
      } catch (e) {
        setToast(friendlyError(e));
      }
    }, { eat });
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
      <Pressable style={[st.gear, { top: belowChips }]} onPress={() => setDevOpen((v) => !v)} accessibilityLabel="테스트 스위치">
        <Icon name="sliders" size={18} color={C.ink} />
      </Pressable>
      {devOpen && (
        <View style={[st.panel, { top: belowChips + 44 }]}>
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

  const chrome = (
    <>
      <SpaceChips space="yard" />
      {nav && <RoomHandle onPress={() => nav.go(1)} />}
    </>
  );

  if (!yard.open) return <LockedYard devPanel={devPanel} chrome={chrome} />;

  const zoneInfo = zoneAsk ? YARD.walk.zones[String(zoneAsk)] : null;
  const price = zoneAsk ? ZONE_PRICE[zoneAsk] : 0;

  return (
    <View style={st.wrap}>
      <YardScene
        zones={yard.zones} items={ownedYard} stage={stage} fruitsHidden={picked} night={night} guests={guests}
        active={active} onTap={onTap} pager={pager} bubble={bubble} sceneRef={sceneRef}
      />
      {ownedYard.includes('picnic_mat') && edibles.length > 0 && (
        <Pressable style={st.feedBtn} onPress={() => { setErr(''); setFeedOpen(true); }} accessibilityRole="button">
          <Icon name="basket" size={18} color={C.ink} />
          <Text style={st.feedText}>매트에서 같이 먹기</Text>
        </Pressable>
      )}
      {toast ? <View style={st.toast} pointerEvents="none"><Text style={st.toastText}>{toast}</Text></View> : null}
      {chrome}
      {devPanel}

      <Sheet visible={!!zoneAsk} onClose={() => setZoneAsk(null)}>
        <Text style={sheetSt.title}>{zoneInfo?.name_ko} 구역</Text>
        <Text style={sheetSt.body}>한 번 사면 계속 {pet}의 마당이야. 새 길로 같이 놀러 갈 수 있어.</Text>
        {err ? <Text style={st.err}>{err}</Text> : null}
        <View style={sheetSt.col}>
          <Btn title={balance >= price ? `${price}로 열기` : `씨앗 ${price}개 필요`} icon={balance >= price ? 'leaf' : undefined} disabled={balance < price || busy}
            loading={busy} onPress={() => zoneAsk && buyZone(zoneAsk)} />
          <Btn title="다음에" kind="ghost" onPress={() => setZoneAsk(null)} />
        </View>
      </Sheet>

      <Sheet visible={feedOpen} onClose={() => setFeedOpen(false)}>
        <Text style={sheetSt.title}>피크닉 매트에서 먹이기</Text>
        {edibles.length === 0 ? (
          <Text style={sheetSt.body}>텃밭에서 수확한 채소·열매가 있으면 여기서 같이 먹을 수 있어.</Text>
        ) : (
          <>
            <Text style={sheetSt.body}>매트로 가서 같이 먹어. 바구니에서 하나 줄어.</Text>
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
            <Kicker />
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
            <Kicker />
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

function Kicker() {
  return (
    <View style={st.kicker}>
      <Icon name="fruit" size={16} color={C.muted} />
      <Text style={st.cardKicker}>추억 열매</Text>
    </View>
  );
}

// 열리기 전: 마당 그림을 흐리게 깔고 안내 카드 1장 (남은 날 수는 보여주지 않음)
function LockedYard({ devPanel, chrome }: { devPanel: React.ReactNode; chrome: React.ReactNode }) {
  return (
    <View style={st.wrap}>
      <Image source={YARD_IMG['yard/bg_1_0.webp']} style={StyleSheet.absoluteFill} contentFit="cover" blurRadius={14} />
      <View style={[StyleSheet.absoluteFill, { backgroundColor: C.veil }]} />
      <View style={st.gate}>
        <View style={st.gateIcon}><Icon name="lock" size={26} color={C.accentInk} /></View>
        <Text style={st.gateTitle}>기록한 날이 7일이 되면 열려</Text>
        <Text style={st.gateSub}>띄엄띄엄이어도 괜찮아. 문 너머로 연못이 살짝 보여</Text>
      </View>
      {chrome}
      {devPanel}
    </View>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg },
  gate: { position: 'absolute', left: 24, right: 24, top: '36%', backgroundColor: C.card, borderRadius: R.cardLg, paddingVertical: 26, paddingHorizontal: 22, alignItems: 'center' },
  gateIcon: { width: 56, height: 56, borderRadius: R.pill, backgroundColor: C.accentBg, alignItems: 'center', justifyContent: 'center', marginBottom: 12 },
  gateTitle: { fontSize: 19, fontWeight: '800', color: C.ink },
  gateSub: { fontSize: 14, color: C.muted, marginTop: 6, textAlign: 'center', lineHeight: 20 },
  gear: { position: 'absolute', right: 16, width: 36, height: 36, borderRadius: R.pill, backgroundColor: C.chip, alignItems: 'center', justifyContent: 'center', zIndex: 21 },
  panel: { position: 'absolute', right: 16, width: 220, backgroundColor: C.card, borderRadius: R.card, padding: 14, gap: 6, zIndex: 21 },
  panelTitle: { fontSize: 12, fontWeight: '700', color: C.muted, marginBottom: 2 },
  panelNote: { fontSize: 11, color: C.muted, marginTop: 2 },
  devBtn: { backgroundColor: C.soft, borderRadius: R.pill, height: 36, justifyContent: 'center', paddingHorizontal: 14 },
  devBtnText: { fontSize: 13, fontWeight: '600', color: C.ink },
  feedBtn: { position: 'absolute', left: 16, bottom: TAB_SPACE, flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: C.chip, borderRadius: R.pill, height: H.btn - 8, paddingHorizontal: 18 },
  feedText: { fontSize: 14, fontWeight: '700', color: C.ink },
  toast: { position: 'absolute', left: 40, right: 40, bottom: TAB_SPACE + 56, backgroundColor: C.toast, borderRadius: R.pill, paddingVertical: 12, paddingHorizontal: 18, alignItems: 'center' },
  toastText: { color: C.white, fontSize: 14, fontWeight: '600' },
  bagRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 10, backgroundColor: C.card, borderRadius: R.card, padding: 10, paddingLeft: 12 },
  bagName: { flex: 1, fontSize: 15, color: C.ink, fontWeight: '600' },
  err: { color: C.danger, fontSize: 13, marginBottom: 10 },
  kicker: { flexDirection: 'row', alignItems: 'center', gap: 5, marginBottom: 4 },
  cardKicker: { fontSize: 13, color: C.muted, fontWeight: '700' },
  memo: { backgroundColor: C.card, borderRadius: R.card, borderLeftWidth: 5, padding: 18, marginBottom: 16 },
  memoText: { fontSize: 18, color: C.ink, fontWeight: '600', lineHeight: 26 },
  memoMeta: { fontSize: 12, color: C.muted, marginTop: 8 },
});
