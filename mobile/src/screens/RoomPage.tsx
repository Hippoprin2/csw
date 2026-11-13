import { router } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { useEffect, useRef, useState } from 'react';
import { Image } from 'expo-image';
import { ActivityIndicator, AppState, Keyboard, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { GestureDetector, useCompetingGestures, usePanGesture, useTapGesture } from 'react-native-gesture-handler';
import Animated, { useAnimatedStyle, useSharedValue } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { CANVAS, ICONS, ROOM } from '@/data/world';
import { api, friendlyError } from '@/lib/api';
import { track } from '@/lib/analytics';
import { CATEGORY_ORDER, CATS, CHIPS, SAFETY_LINE, classifyByKeyword, pickLine, type Category } from '@/lib/categories';
import { formatTime, kstToday, kstYesterday } from '@/lib/dates';
import { jarMarbles } from '@/lib/jars';
import { askPermission } from '@/lib/notifications';
import { safetyKeywordHit } from '@/lib/safety';
import { useApp } from '@/state/app';
import { Icon } from '@/ui/Icon';
import { Btn, HelpLines } from '@/ui/kit';
import { Pet, type PetAction } from '@/ui/Pet';
import { Sheet, st as sheetSt } from '@/ui/Sheet';
import type { Pager } from '@/ui/pager';
import { SpaceImage } from '@/ui/SpaceImage';
import { useSpaceSize } from '@/ui/layout';
import { PANEL_OVERLAP, SpaceChips, SpaceSwitch, useSceneLayout, type SpaceNav } from '@/ui/SpaceChrome';
import { ART, C, H, R, TAB_SPACE } from '@/ui/theme';
import { useWinSheet } from '@/ui/WinSheet';

const DAILY_REWARD_CAP = 10;
const NOTIF_ASKED_KEY = 'csw.notifAsked';
const SAFETY_DAY_KEY = 'csw.safetyShownDay';
const VASE_KEY = 'csw.sillVase'; // 창턱 꽃병 자리: 튤립/해바라기 둘 다 있으면 탭해서 바꿈 (기기에만 저장)
const NOTES_SHOWN = 5; // 오늘의 쪽지는 최근 5개까지, 나머지는 하루 한 장에서
const DOT = 7; // 유리장 병 속 구슬 한 칸 (캔버스 px)
let keptCamX: number = ROOM.view.start_x; // 둘러본 위치 유지 (앱을 켜 둔 동안). 처음엔 단짝 가운데(= 예전 방)

const store = {
  get: (k: string) => { try { return globalThis.localStorage?.getItem(k) ?? null; } catch { return null; } },
  set: (k: string, v: string) => { try { globalThis.localStorage?.setItem(k, v); } catch {} },
};

// 방 = 홈. 기록 입력창·축하 8종·곁에 앉기·먹이기/선물하기는 방에서만 (STATUS 2026-11-09 결정)
export function RoomPage({ pager, nav }: { pager?: Pager; nav?: SpaceNav } = {}) {
  const { jars, profile, wins, setWins, reloadJars, setBalance, owned, items, updateProfile, celebration, celebrate, crops, bag, reloadGarden } = useApp();
  const [basket, setBasket] = useState(false);
  // 그림: 화면 위쪽 가로 꽉(약 420). 1080 창을 높이에 맞추고 남는 쪽은 가운데 기준으로 잘라 보여준다
  const { fullWidth } = useSpaceSize();
  const { canvasH, sceneH } = useSceneLayout();
  const insets = useSafeAreaInsets();
  const belowChips = insets.top + 8 + H.chip + 10; // 위쪽 칩 아래
  // 1080 창의 세로 전체를 canvasH에 맞춘다 (단짝 발까지 보이게). 가로는 가운데 기준으로 자르거나 넓게 보여줌
  const sc = canvasH / CANVAS;
  const offX = (CANVAS - fullWidth / sc) / 2; // 창(1080) 중 화면 밖으로 잘리는 왼쪽 폭 (캔버스 px, 넓은 화면이면 음수)
  const maxWorldX = Math.max(0, ROOM.width - fullWidth / sc);
  const offY = 0;
  const [vase, setVase] = useState(() => store.get(VASE_KEY));
  const [text, setText] = useState('');
  const [chosen, setChosen] = useState<Category | null>(null);
  const [picking, setPicking] = useState(false);
  const [day, setDay] = useState<'today' | 'yesterday'>('today');
  const [busy, setBusy] = useState(false);
  const [action, setAction] = useState<PetAction>(null);
  const [bubble, setBubble] = useState('');
  const [float, setFloat] = useState<{ key: number; n: number } | null>(null);
  const [safety, setSafety] = useState<'card' | 'banner' | null>(null);
  const [notifAsk, setNotifAsk] = useState(false);
  const [notifTime, setNotifTime] = useState('21:00');
  const [err, setErr] = useState('');
  const bubbleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 키보드가 입력창을 가리지 않게: 키보드가 스크롤 영역 아래를 얼마나 덮는지 재서 그만큼 아래 여백을 늘리고 맨 아래로 스크롤.
  // (iOS는 화면이 줄지 않음. 안드로이드는 화면이 줄어드는 경우가 많아 덮는 양이 0이면 그대로)
  const scrollRef = useRef<React.ComponentRef<typeof ScrollView>>(null);
  const [kbPad, setKbPad] = useState(0);
  useEffect(() => {
    const showEv = Platform.OS === 'ios' ? 'keyboardWillShow' : 'keyboardDidShow';
    const hideEv = Platform.OS === 'ios' ? 'keyboardWillHide' : 'keyboardDidHide';
    const show = Keyboard.addListener(showEv, (e) => {
      scrollRef.current?.measureInWindow((_x, y, _w, h) => {
        const overlap = Math.max(0, y + h - e.endCoordinates.screenY);
        setKbPad(overlap);
        setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 50);
      });
    });
    // 키보드가 내려가면 맨 위로 되돌림: 안 그러면 내려간 채로 남아 방 위쪽과 단짝 말풍선(멘트)이 잘림 (대표 피드백 2026-11-11)
    const hide = Keyboard.addListener(hideEv, () => {
      setKbPad(0);
      scrollRef.current?.scrollTo({ y: 0, animated: true });
    });
    return () => { show.remove(); hide.remove(); };
  }, []);

  const today = kstToday();
  const todayWins = wins.filter((w) => w.win_date === today).sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
  const todayCount = todayWins.length;
  const { openWin } = useWinSheet();
  const auto = classifyByKeyword(text.trim());
  const k = chosen ?? auto;

  const say = (line: string, ms = 3200) => {
    setBubble(line);
    if (bubbleTimer.current) clearTimeout(bubbleTimer.current);
    bubbleTimer.current = setTimeout(() => setBubble(''), ms);
  };

  // 구매·먹이기·선물 직후: 최근 이벤트(기록 vs 그 밖) 중 더 나중 것을 보여준다
  const extFresh = !!celebration && (!action || celebration.key > action.key);
  const petAction: PetAction = extFresh ? { kind: celebration!.kind, key: celebration!.key } : action;
  const shownBubble = extFresh ? celebration!.line : bubble;
  const newItemId = celebration?.itemId;

  // 단짝이 동작을 시작하면(기록·먹이기·선물·상점 구매 등 무엇이든) 아래로 내려가 있던 화면을 맨 위로 올려 동작·말풍선이 보이게 (대표 피드백 2026-11-13).
  // 바구니처럼 시트에서 시작한 동작은 시트가 내려가는 동안 스크롤이 끊길 수 있어 한 번 더
  const petKey = petAction?.key;
  const shownKey = useRef(petKey);
  useEffect(() => {
    if (petKey === undefined || petKey === shownKey.current) return;
    shownKey.current = petKey;
    const top = () => scrollRef.current?.scrollTo({ y: 0, animated: true });
    top();
    const t = setTimeout(top, 400);
    return () => clearTimeout(t);
  }, [petKey]);

  async function submit(raw?: string) {
    const t = (raw ?? text).trim();
    if (!t || busy) return;
    // 기록하면 맨 위로: 예시 버튼처럼 키보드 없이 기록할 땐 키보드 내려감 이벤트가 없어서 직접 올림 (대표 피드백 2026-11-11)
    scrollRef.current?.scrollTo({ y: 0, animated: true });
    Keyboard.dismiss();
    setBusy(true); setErr('');
    say('듣고 있어…', 8000);
    const kwSafety = safetyKeywordHit(t);
    // 카테고리를 직접 고르지 않았으면 서버 LLM으로 보정 (실패하면 키워드 결과)
    const llm = await api.classify(t);
    const userPicked = !!chosen && !raw;
    const unsafe = kwSafety || !!llm?.self_harm; // 둘 중 하나라도 걸리면 안내 (안전한 쪽으로)
    // 자해 표현이 감지되면 '나 돌보기' 같은 분류로 남지 않게 항상 '버틴 하루'로 저장 (사용자가 고른 분류보다 우선)
    const category: Category = unsafe ? 'endure' : userPicked ? chosen! : (llm?.category ?? classifyByKeyword(t));
    const source = unsafe ? 'auto' : userPicked ? 'user' : llm ? 'llm' : 'auto';
    try {
      const winDate = day === 'today' ? today : kstYesterday();
      const r = await api.recordWin(t, category, source, winDate);
      setWins((ws) => [r.win, ...ws]);
      reloadJars().catch(() => {});
      setBalance(r.balance);
      setText(''); setChosen(null); setPicking(false); setDay('today');
      setTimeout(() => scrollRef.current?.scrollTo({ y: 0, animated: true }), 50); // 말풍선이 보이게 (위 스크롤이 중간에 끊겨도 다시)
      track('win_recorded', { category, source, first: r.first, yesterday: day === 'yesterday', earned: r.earned });
      if (Platform.OS !== 'web') Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});

      if (unsafe) {
        setAction({ kind: 'sit', key: Date.now() });
        say(SAFETY_LINE, 9000);
        const shownToday = store.get(SAFETY_DAY_KEY) === today;
        setSafety(shownToday ? 'banner' : 'card');
        store.set(SAFETY_DAY_KEY, today);
        api.logSafety(kwSafety ? 'keyword' : 'llm').catch(() => {});
        track('safety_shown', { repeat: shownToday });
      } else {
        setAction({ kind: category, key: Date.now() });
        if (r.sealed) {
          say('유리병이 꽉 찼어! 뚜껑 닫아서 선반에 올려둘게. 새 병 시작이야', 6000);
          track('jar_sealed', { no: r.win.jar_no });
        } else say(r.first ? '첫 구슬이 유리병에 들어갔어!' : pickLine(category));
      }
      if (r.earned) {
        const fk = Date.now();
        setFloat({ key: fk, n: r.earned });
        setTimeout(() => setFloat((f) => (f?.key === fk ? null : f)), 1600);
      }

      // D5: 알림 권한은 첫 기록 직후에 한 번만 물어본다
      if (!unsafe && !profile?.notify_enabled && !store.get(NOTIF_ASKED_KEY) && Platform.OS !== 'web') {
        setTimeout(() => setNotifAsk(true), 2600);
      }
    } catch (e) {
      setErr(friendlyError(e));
      say('');
    } finally {
      setBusy(false);
    }
  }

  async function allowNotif(yes: boolean) {
    store.set(NOTIF_ASKED_KEY, '1');
    setNotifAsk(false);
    track('notif_prompt', { accepted: yes });
    if (!yes) return;
    const granted = await askPermission();
    track('notif_prompt', { granted });
    if (granted) await updateProfile({ notify_enabled: true, notify_time: `${notifTime}:00` });
  }

  // 공간 스레드 export(design/world/export/v1) 그대로: 배경 → (놓인 소품 + 창턱 수확 장식 + 단짝)을 z 순서로
  const placedIds = new Set(owned.filter((o) => o.placed).map((o) => o.item_id));
  // 창턱 수확 장식은 바구니에 남아 있는 동안만 (대표 결정 2026-11-13: 먹거나 선물해서 다 쓰면 사라짐 — 예전 '처음 수확하면 영구' 규칙 폐기)
  const unlocked = (c: string) => (bag[c] ?? 0) > 0;
  const vaseCrop = unlocked('tulip') && unlocked('sunflower') ? (vase === 'sunflower' ? 'sunflower' : 'tulip')
    : unlocked('tulip') ? 'tulip' : unlocked('sunflower') ? 'sunflower' : null;
  const shown = ROOM.items.filter((it) => {
    if (it.id.startsWith('harvest_')) {
      const crop = it.id.slice('harvest_'.length);
      return it.slot === 'sill_vase' ? crop === vaseCrop : unlocked(crop);
    }
    return placedIds.has(it.id);
  });
  const nameOf = (id: string) => items.find((i) => i.id === id)?.name ?? crops.find((c) => `harvest_${c.id}` === id)?.deco_name;
  const back = shown.filter((it) => it.z < ROOM.pet.z);
  const front = shown.filter((it) => it.z > ROOM.pet.z);
  const draw = (it: (typeof ROOM.items)[number]) => (
    <SpaceImage key={it.id} source={it.source} rect={it} s={sc} fadeIn={newItemId === it.id} label={nameOf(it.id)} />
  );
  const vaseItem = vaseCrop && unlocked('tulip') && unlocked('sunflower') ? ROOM.items.find((i) => i.id === `harvest_${vaseCrop}`) : null;
  const swapVase = () => {
    const next = vaseCrop === 'tulip' ? 'sunflower' : 'tulip';
    setVase(next); store.set(VASE_KEY, next);
  };
  const bagItems = crops.filter((c) => (bag[c.id] ?? 0) > 0);
  const bagCount = bagItems.reduce((n, c) => n + bag[c.id], 0);

  async function feedOrGift(cropId: string) {
    const c = crops.find((x) => x.id === cropId);
    if (!c) return;
    try {
      await api.useHarvest(cropId);
      setBasket(false);
      // 채소·열매 = 먹이기(냠냠), 꽃 = 선물하기(냄새 맡고 반짝 → 기지개+회전 재사용). 바구니 새로 받기를 기다리지 않고 바로 시작
      if (c.kind === 'edible') celebrate({ kind: c.id === 'strawberry' ? 'eat_strawberry' : 'eat', line: `${c.name} 냠냠, 고마워!` });
      else celebrate({ kind: 'care', line: `${c.name} 향기 좋다! 고마워` });
      await reloadGarden();
      track('harvest_used', { crop: cropId, kind: c.kind });
    } catch (e) {
      setErr(friendlyError(e));
    }
  }

  // 유리장: 닫힌 병 중 최근 12개 (슬롯 0 = 그중 가장 오래된 병). 모든 병은 유리병 탭 선반에 그대로 (R3)
  const JC = ROOM.jarCabinet;
  const cab = jars.jars.filter((j) => j.no < jars.current_jar && j.count > 0).sort((a, b) => a.no - b.no).slice(-JC.slots.length);
  // 넓은 방(2160) 끌어서 둘러보기 (manifest spaces.room.view): 카드는 1080 창, 끝에서 더 끌면 옆 공간으로. 자동 복귀 없음
  const V = ROOM.view;
  const camX = useSharedValue(keptCamX);
  const drag = useRef({ start: keptCamX, over: 0, on: false });
  // 앱을 켤 때마다 방 가운데부터 (대표 요청 2026-11-11): 처음 켤 때는 start_x(= 넓은 방 가운데),
  // 앱을 내렸다 다시 열 때도 가운데로. 내려갈 때 바꿔 둬서 다시 열면 화면이 움직이는 게 안 보임
  useEffect(() => {
    const sub = AppState.addEventListener('change', (st) => {
      if (st === 'background') { keptCamX = V.start_x; camX.set(V.start_x); }
    });
    return () => sub.remove();
  }, [camX, V.start_x]);
  const pan = usePanGesture({
    activeOffsetX: [-10, 10], failOffsetY: [-12, 12], maxPointers: 1, runOnJS: true,
    onActivate: () => { drag.current = { start: camX.value, over: 0, on: true }; },
    onUpdate: (e) => {
      if (!drag.current.on || !Number.isFinite(e.translationX)) return;
      const want = drag.current.start - e.translationX / sc;
      const x = Math.min(V.max_x, Math.max(V.min_x, want));
      camX.set(x); keptCamX = x;
      // 방 끝을 넘겨 끈 만큼 페이지가 손가락을 따라 옴 (텃밭/마당)
      const over = (x - want) * sc;
      if (pager && (over !== 0 || drag.current.over !== 0)) { drag.current.over = over; pager.drag(over); }
    },
    onDeactivate: (e) => {
      if (!drag.current.on) return;
      if (pager && drag.current.over !== 0) pager.end(drag.current.over, e.velocityX, e.canceled);
      drag.current.over = 0; drag.current.on = false;
    },
  });
  // 탭: 유리장 병 → 그 병 보기, 꽃병 → 튤립/해바라기 바꾸기
  const tap = useTapGesture({
    maxDistance: 8, runOnJS: true,
    onDeactivate: (e) => {
      if (e.canceled) return;
      const x = Math.min(maxWorldX, Math.max(0, camX.value + offX)) + e.x / sc, y = offY + e.y / sc;
      const hit = (r: number[]) => x >= r[0] && x <= r[0] + r[2] && y >= r[1] && y <= r[1] + r[3];
      const si = cab.findIndex((_, i) => hit(JC.slots[i].tap));
      if (si >= 0) { track('jar_viewed', { no: cab[si].no, from: 'cabinet' }); router.push(`/jar/${cab[si].no}`); return; }
      if (vaseItem && hit([vaseItem.x, vaseItem.y, vaseItem.w, vaseItem.h])) swapVase();
    },
  });
  const roomGesture = useCompetingGestures(pan, tap);
  // 방 그림 밖(여백·기록 칸)에서 좌우로 끌면 페이지 넘기기 → 텃밭/마당. 방 그림 안의 끌기가 먼저
  const pagePan = usePanGesture({
    activeOffsetX: [-12, 12], failOffsetY: [-12, 12], maxPointers: 1, requireToFail: pan,
    onUpdate: (e) => { 'worklet'; pager?.drag(e.translationX); },
    onDeactivate: (e) => { 'worklet'; pager?.end(e.translationX, e.velocityX, e.canceled); },
  });
  const worldStyle = useAnimatedStyle(() => ({ transform: [{ translateX: -Math.min(maxWorldX, Math.max(0, camX.value + offX)) * sc }, { translateY: -offY * sc }] }));

  const jarDots = (j: (typeof cab)[number], slot: (typeof JC.slots)[number]) => {
    const [mx, my, mw, mh] = slot.marbles;
    const cols = Math.floor(mw / DOT), rows = Math.floor(mh / DOT), all = jarMarbles(j);
    const n = Math.max(1, Math.round((Math.min(j.count, 50) / 50) * cols * rows));
    return Array.from({ length: n }, (_, i) => {
      const c = all[Math.floor((i * all.length) / n)] ?? 'cheer';
      const col = i % cols, row = Math.floor(i / cols); // 아래 줄부터 채움
      return <View key={i} style={{ position: 'absolute', left: (mx + col * DOT) * sc, top: (my + mh - (row + 1) * DOT) * sc, width: DOT * sc, height: DOT * sc, borderRadius: DOT * sc, backgroundColor: CATS[c].color }} />;
    });
  };

  return (
    <GestureDetector gesture={pagePan}>
    <View style={st.wrap}>
      <ScrollView ref={scrollRef} keyboardShouldPersistTaps="handled" keyboardDismissMode="interactive"
        contentContainerStyle={{ paddingBottom: TAB_SPACE + 12 + kbPad }}>
        <GestureDetector gesture={roomGesture}>
        <View style={[st.room, { width: fullWidth, height: sceneH }]} accessibilityHint="좌우로 끌면 방을 둘러볼 수 있어요">
          <Animated.View style={[{ position: 'absolute', left: 0, top: 0, width: ROOM.width * sc, height: ROOM.height * sc }, worldStyle]}>
            <Image source={ROOM.background} style={StyleSheet.absoluteFill} contentFit="cover" loading="eager" />
            {cab.map((j, i) => {
              const sl = JC.slots[i];
              return (
                <View key={j.no} style={StyleSheet.absoluteFill} pointerEvents="none" accessible accessibilityLabel={`${j.no}번째 유리병`}>
                  <Image source={JC.jarBack.source} style={{ position: 'absolute', left: sl.back[0] * sc, top: sl.back[1] * sc, width: JC.jarBack.w * sc, height: JC.jarBack.h * sc }} />
                  {jarDots(j, sl)}
                  <Image source={JC.jarFront.source} style={{ position: 'absolute', left: sl.front[0] * sc, top: sl.front[1] * sc, width: JC.jarFront.w * sc, height: JC.jarFront.h * sc }} />
                </View>
              );
            })}
            <Image source={JC.glass.source} style={{ position: 'absolute', left: JC.glass.x * sc, top: JC.glass.y * sc, width: JC.glass.w * sc, height: JC.glass.h * sc }} />
            {back.map(draw)}
            <View style={{ position: 'absolute', left: ROOM.pet.x * sc, top: ROOM.pet.y * sc }}>
              <Pet action={petAction} size={ROOM.pet.w * sc} />
            </View>
            {front.map(draw)}
          </Animated.View>
          {shownBubble ? (
            <View style={[st.bubble, { top: belowChips }]}>
              <Text style={st.bubbleText}>{shownBubble}</Text>
            </View>
          ) : null}
          {float && (
            <Text key={float.key} style={[st.float, { top: belowChips + 8 }]}>+{float.n} 씨앗</Text>
          )}
          <SpaceChips space="room" />
        </View>
        </GestureDetector>

        <View style={st.panel}>
        {nav && <SpaceSwitch nav={nav} />}
        {/* 안전 안내는 기록 직후 맨 위로 올라갔을 때 바로 보이게 전환 바로 아래 */}
        {safety === 'card' && (
          <View style={st.safetyCard}>
            <Text style={st.safetyTitle}>혼자 견디고 있다면, 이야기할 곳이 있어요</Text>
            <Text style={st.safetyBody}>모두 24시간 연결돼요. 번호를 누르면 바로 전화가 걸려요.</Text>
            <HelpLines />
            <Btn title="닫기" kind="ghost" onPress={() => setSafety(null)} style={{ marginTop: 10 }} />
          </View>
        )}
        {safety === 'banner' && (
          <Pressable style={st.banner} onPress={() => router.push('/help')} accessibilityRole="button">
            <Text style={st.bannerText}>힘들 땐 109 (24시간) · 도움받을 수 있는 곳 보기</Text>
            <Icon name="chevronRight" size={18} color={C.muted} />
          </Pressable>
        )}

        <View style={st.composer}>
          <Text style={st.label}>오늘 해낸 거, 아무리 작아도 좋아</Text>
          <View style={st.dayRow}>
            {(['today', 'yesterday'] as const).map((d) => (
              <Pressable key={d} onPress={() => setDay(d)} style={[st.dayBtn, day === d && st.dayOn]} accessibilityRole="radio" accessibilityState={{ selected: day === d }}>
                <Text style={[st.dayText, day === d && st.dayTextOn]}>{d === 'today' ? '오늘' : '어제'}</Text>
              </Pressable>
            ))}
          </View>
          <View style={st.row}>
            <TextInput
              style={st.input} value={text} onChangeText={(v) => { setText(v); setErr(''); }}
              placeholder="예) 침대 정리했다" placeholderTextColor={C.placeholder} maxLength={100} returnKeyType="done"
              onSubmitEditing={() => submit()} accessibilityLabel="오늘 해낸 일" editable={!busy}
            />
            <Pressable onPress={() => submit()} disabled={!text.trim() || busy} accessibilityRole="button" accessibilityLabel="기록"
              style={({ pressed }) => [st.send, (!text.trim() || busy) && { opacity: 0.4 }, pressed && { transform: [{ scale: 0.95 }] }]}>
              {busy ? <ActivityIndicator color={C.white} /> : <Icon name="send" size={24} color={C.white} stroke={2.2} />}
            </Pressable>
          </View>
          {text.trim() ? (
            <View style={st.catLine}>
              <Text style={st.catText}><Text style={{ color: C.ink, fontWeight: '700' }}>{CATS[k].name}</Text> 동작을 할 거예요 · </Text>
              <Pressable onPress={() => setPicking((p) => !p)} accessibilityRole="button"><Text style={st.change}>바꾸기</Text></Pressable>
            </View>
          ) : null}
          {picking && (
            <View style={st.chips}>
              {CATEGORY_ORDER.map((c) => (
                <Pressable key={c} onPress={() => { setChosen(c); setPicking(false); }} style={[st.chip, k === c && st.chipOn]}>
                  <Text style={[st.chipText, k === c && st.chipTextOn]}>{CATS[c].name}</Text>
                </Pressable>
              ))}
            </View>
          )}
          {!text.trim() && (
            <View style={st.chips}>
              {CHIPS.map((c) => (
                <Pressable key={c} onPress={() => submit(c)} style={st.chip} accessibilityRole="button" disabled={busy}>
                  <Text style={st.chipText}>{c}</Text>
                </Pressable>
              ))}
            </View>
          )}
          {err ? <Text style={st.err}>{err}</Text> : null}
        </View>
        {/* 오늘의 쪽지 (C9 M1): 오늘 적은 기록이 쪽지로 쌓임 (최근 것 위). 누르면 크게 보기, 다 보기 → 하루 한 장 */}
        {todayWins.length > 0 && (
          <View style={st.notes}>
            <View style={st.notesHead}>
              <Text style={st.notesTitle}>오늘의 쪽지 · {todayWins.length}가지</Text>
              <Pressable onPress={() => router.push(`/jar/day/${today}`)} hitSlop={8} accessibilityRole="button" accessibilityLabel="오늘 기록 다 보기">
                <Text style={st.notesMore}>다 보기 ›</Text>
              </Pressable>
            </View>
            {todayWins.slice(0, NOTES_SHOWN).map((w) => (
              <Pressable key={w.id} onPress={() => openWin(w)} style={st.note} accessibilityRole="button" accessibilityHint="눌러서 크게 보기">
                <View style={[st.noteDot, { backgroundColor: CATS[w.category].color }]} />
                <Text style={st.noteText} numberOfLines={1}>{w.text}</Text>
                {w.starred ? <Icon name="star" size={13} color={C.accentInk} fill={C.accentInk} /> : null}
                <Text style={st.noteTime}>{formatTime(w.created_at)}</Text>
              </Pressable>
            ))}
            {todayWins.length > NOTES_SHOWN && (
              <Pressable onPress={() => router.push(`/jar/day/${today}`)} accessibilityRole="button">
                <Text style={st.notesRest}>+ {todayWins.length - NOTES_SHOWN}가지 더</Text>
              </Pressable>
            )}
          </View>
        )}
        <Text style={st.cap}>
          {todayCount > 0 ? `오늘 ${todayCount}가지를 해냈어. ` : ''}
          기록 1개 = 씨앗 3개{todayCount >= DAILY_REWARD_CAP ? ' · 오늘 씨앗은 다 받았어. 기록은 얼마든지 남겨도 돼!' : ` (하루 ${DAILY_REWARD_CAP}개 기록까지)`}
        </Text>
        {bagCount > 0 && (
          <Pressable style={st.basketBtn} onPress={() => setBasket(true)} accessibilityRole="button">
            <Icon name="basket" size={20} color={C.accentInk} />
            <Text style={st.basketText}>수확 바구니 {bagCount}개 · 먹이기/선물하기</Text>
          </Pressable>
        )}

        </View>
      </ScrollView>

      <Sheet visible={notifAsk} onClose={() => allowNotif(false)}>
        <Text style={sheetSt.title}>내일 이 시간쯤 한 번만 물어봐도 될까?</Text>
        <Text style={sheetSt.body}>하루 한 번, 오늘 해낸 걸 물어볼게. 이미 적은 날엔 안 보내.</Text>
        <View style={[st.chips, { marginBottom: 14 }]}>
          {['20:00', '21:00', '22:00', '23:00'].map((t) => (
            <Pressable key={t} onPress={() => setNotifTime(t)} style={[st.chip, notifTime === t && st.chipOn]}>
              <Text style={[st.chipText, notifTime === t && st.chipTextOn]}>{t}</Text>
            </Pressable>
          ))}
        </View>
        <View style={sheetSt.col}>
          <Btn title="좋아" onPress={() => allowNotif(true)} />
          <Btn title="괜찮아" kind="ghost" onPress={() => allowNotif(false)} />
        </View>
      </Sheet>
      <Sheet visible={basket} onClose={() => setBasket(false)}>
        <Text style={sheetSt.title}>수확 바구니</Text>
        <Text style={sheetSt.body}>먹이거나 선물하면 하나씩 줄고, 다 쓰면 창턱 장식도 사라져. 텃밭에서 또 수확하면 다시 생겨.</Text>
        {bagItems.map((c) => (
          <View key={c.id} style={st.bagRow}>
            <Image source={ICONS[`produce_${c.id}`]} style={{ width: 40, height: 40 }} contentFit="contain" />
            <Text style={st.bagName}>{c.name} {bag[c.id]}개</Text>
            <Btn title={c.kind === 'edible' ? '먹이기' : '선물하기'} onPress={() => feedOrGift(c.id)} />
          </View>
        ))}
      </Sheet>
    </View>
    </GestureDetector>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg },
  room: { overflow: 'hidden', backgroundColor: ART.roomFill },
  // 크림 판: 위 모서리 32, 그림 아래를 살짝 덮으며 올라옴
  panel: { marginTop: -PANEL_OVERLAP, backgroundColor: C.bg, borderTopLeftRadius: R.sheet, borderTopRightRadius: R.sheet, paddingHorizontal: 20, paddingTop: 18 },
  basketBtn: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 14, backgroundColor: C.accentBg, borderRadius: R.pill, height: H.btn, paddingHorizontal: 18 },
  basketText: { fontSize: 14, fontWeight: '700', color: C.accentInk },
  bagRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 10, backgroundColor: C.card, borderRadius: R.card, padding: 10, paddingLeft: 12 },
  bagName: { flex: 1, fontSize: 15, color: C.ink, fontWeight: '600' },
  bubble: { position: 'absolute', alignSelf: 'center', top: 96, maxWidth: '80%', backgroundColor: C.card, borderRadius: R.card, paddingVertical: 10, paddingHorizontal: 16, zIndex: 5 },
  bubbleText: { fontSize: 14, fontWeight: '600', color: C.ink, textAlign: 'center', lineHeight: 20 },
  float: { position: 'absolute', right: 28, top: 104, fontSize: 16, fontWeight: '800', color: C.seed },
  composer: { marginTop: 20 },
  label: { fontSize: 21, fontWeight: '800', color: C.ink, marginBottom: 10, lineHeight: 28 },
  dayRow: { flexDirection: 'row', gap: 6, marginBottom: 12 },
  dayBtn: { height: 32, justifyContent: 'center', paddingHorizontal: 14, borderRadius: R.pill, backgroundColor: C.soft },
  dayOn: { backgroundColor: C.accentBg },
  dayText: { fontSize: 13, color: C.muted, fontWeight: '600' },
  dayTextOn: { color: C.accentInk, fontWeight: '800' },
  row: { flexDirection: 'row', gap: 8, alignItems: 'center' },
  input: { flex: 1, minWidth: 0, height: H.input, fontSize: 16, paddingHorizontal: 22, borderRadius: R.pill, backgroundColor: C.card, color: C.ink },
  send: { width: H.input, height: H.input, borderRadius: R.pill, backgroundColor: C.accent, alignItems: 'center', justifyContent: 'center' },
  catLine: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', marginTop: 12, paddingHorizontal: 6 },
  catText: { fontSize: 13, color: C.muted },
  change: { fontSize: 13, color: C.accentInk, fontWeight: '700', textDecorationLine: 'underline' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 14 },
  chip: { height: H.chip, justifyContent: 'center', paddingHorizontal: 14, borderRadius: R.pill, backgroundColor: C.soft },
  chipOn: { backgroundColor: C.accentBg },
  chipText: { fontSize: 14, color: C.ink },
  chipTextOn: { color: C.accentInk, fontWeight: '700' },
  err: { marginTop: 10, color: C.danger, fontSize: 13 },
  notes: { marginTop: 16, backgroundColor: C.card, borderRadius: R.card, padding: 12, paddingTop: 14 },
  notesHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 6, marginBottom: 8 },
  notesTitle: { fontSize: 13, fontWeight: '800', color: C.ink },
  notesMore: { fontSize: 13, color: C.accentInk, fontWeight: '700' },
  note: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: C.bg, borderRadius: R.pill, paddingVertical: 11, paddingHorizontal: 16, marginBottom: 6 },
  noteDot: { width: 9, height: 9, borderRadius: R.pill },
  noteText: { flex: 1, fontSize: 14, color: C.ink },
  noteTime: { fontSize: 11, color: C.muted },
  notesRest: { fontSize: 13, color: C.muted, textAlign: 'center', paddingVertical: 6 },
  cap: { fontSize: 12, color: C.muted, marginHorizontal: 6, marginTop: 12, lineHeight: 18 },
  safetyCard: { marginTop: 14, backgroundColor: C.card, borderRadius: R.card, padding: 18 },
  safetyTitle: { fontSize: 16, fontWeight: '800', color: C.ink, marginBottom: 4 },
  safetyBody: { fontSize: 13, color: C.muted, marginBottom: 12, lineHeight: 19 },
  banner: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 12, backgroundColor: C.card, borderRadius: R.card, paddingVertical: 14, paddingHorizontal: 18 },
  bannerText: { flex: 1, fontSize: 13, color: C.ink, fontWeight: '600' },
});
