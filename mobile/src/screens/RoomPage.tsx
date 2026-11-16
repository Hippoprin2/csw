import { router } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { BlurView } from 'expo-blur';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Image } from 'expo-image';
import { ActivityIndicator, AppState, Keyboard, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, useWindowDimensions, View } from 'react-native';
import { GestureDetector, useCompetingGestures, usePanGesture, useTapGesture } from 'react-native-gesture-handler';
import Animated, { useAnimatedStyle, useSharedValue } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { CANVAS, ICONS, ROOM } from '@/data/world';
import { PET_ASPECT } from '@/data/petClips';
import { api, friendlyError } from '@/lib/api';
import { track } from '@/lib/analytics';
import { CATEGORY_ORDER, CATS, CHIPS, HARM_LINE, SAFETY_LINE, classifyByKeyword, eatVariant, pickLine, type Category } from '@/lib/categories';
import { formatTime, kstToday, kstYesterday } from '@/lib/dates';
import { jarMarbles } from '@/lib/jars';
import { askPermission } from '@/lib/notifications';
import { safetyKeywordHit } from '@/lib/safety';
import { useApp } from '@/state/app';
import { Icon } from '@/ui/Icon';
import { Btn } from '@/ui/kit';
import { Pet, type PetAction } from '@/ui/Pet';
import { Sheet, st as sheetSt } from '@/ui/Sheet';
import type { Pager } from '@/ui/pager';
import { SpaceImage } from '@/ui/SpaceImage';
import { useSpaceSize } from '@/ui/layout';
import { SpaceChips, SpaceSwitch, type SpaceNav } from '@/ui/SpaceChrome';
import { ART, C, H, R, TAB_SPACE } from '@/ui/theme';
import { useWinSheet } from '@/ui/WinSheet';

const DAILY_REWARD_CAP = 10;
const NOTIF_ASKED_KEY = 'csw.notifAsked';
const VASE_KEY = 'csw.sillVase'; // 창턱 꽃병 자리: 튤립/해바라기 둘 다 있으면 탭해서 바꿈 (기기에만 저장)
const DOT = 7; // 유리장 병 속 구슬 한 칸 (캔버스 px)
const SWITCH_H = 44; // 텃밭/방/마당 전환 높이 (36 + 위아래 4)
const PEEK_H = 44; // 오늘의 쪽지 접힌 한 줄
const ROOM_BAR = 64; // 방 보기 아래 버튼 줄(바구니·꾸미기) 자리
const REC_MAX_MS = 12000; // 기록 카드: 동작이 끝나지 않는 경우(로딩 실패)에도 이 뒤엔 걷음
const nowKey = () => Date.now(); // 동작·씨앗 표시 키 (이벤트 핸들러에서만 부름)
// 웹 전용: 키보드에 안 줄어드는 레이아웃 높이 (창 크기·회전·사파리 툴바 변화만 따라감)
function useLayoutViewportHeight() {
  const read = () => (Platform.OS === 'web' && typeof document !== 'undefined' ? document.documentElement.clientHeight : 0);
  const [h, setH] = useState(read);
  useEffect(() => {
    if (Platform.OS !== 'web' || typeof window === 'undefined') return;
    const on = () => setH(document.documentElement.clientHeight);
    window.addEventListener('resize', on);
    window.addEventListener('orientationchange', on);
    return () => { window.removeEventListener('resize', on); window.removeEventListener('orientationchange', on); };
  }, []);
  return h;
}

let keptCamX: number = ROOM.view.start_x; // 둘러본 위치 유지 (앱을 켜 둔 동안). 처음엔 단짝 가운데(= 예전 방)

const store = {
  get: (k: string) => { try { return globalThis.localStorage?.getItem(k) ?? null; } catch { return null; } },
  set: (k: string, v: string) => { try { globalThis.localStorage?.setItem(k, v); } catch {} },
};

// 방 = 홈. 기록 입력창·축하 8종·곁에 앉기·먹이기/선물하기는 방에서만 (STATUS 2026-11-09 결정)
// 2026-11-16 홈 '하마 무대' (대표 결정 H1~H4, design/home_stage/README.md):
// - 'stage'(기본): 뿌옇게 흐린 방 위에 단짝을 크게. 입력은 알약 한 줄(누르면 펼침), 오늘의 쪽지는 아래 한 줄(누르거나 끌어올리면 시트)
// - 'room'(씨앗 칩 옆 '방' 버튼): 흐림이 걷히고 예전 방 그대로 — 끌어 둘러보기·유리장·꽃병·수확 바구니·꾸미기
export function RoomPage({ pager, nav, pageH = 0 }: { pager?: Pager; nav?: SpaceNav; pageH?: number } = {}) {
  const { jars, profile, wins, setWins, reloadJars, setBalance, owned, items, updateProfile, celebration, celebrate, crops, bag, reloadGarden } = useApp();
  const [basket, setBasket] = useState(false);
  const [mode, setMode] = useState<'stage' | 'room'>('stage');
  const { fullWidth } = useSpaceSize();
  const insets = useSafeAreaInsets();
  // 페이지 높이는 index가 잰 값(pageH)을 받음. 여기서 onLayout으로 재면 웹에서 한 번도 안 불려(GestureDetector 아래) 기본 760으로
  // 그려져 실제 화면(예: 사파리 665)보다 커지고, 사파리가 넘친 만큼 위로 밀어 날짜·씨앗 칩이 잘렸음 (대표 폰 2026-11-16)
  const { height: winH } = useWindowDimensions();
  // 웹: 창 높이를 바로 씀. 단 useWindowDimensions(=visualViewport)는 키보드가 뜨면 줄어들어 방 그림이 위쪽 띠만 남고
  // 아래가 흰 바탕이 됐음(대표 폰 2026-11-16) → 키보드와 무관한 레이아웃 높이(documentElement.clientHeight)를 씀
  const webH = useLayoutViewportHeight();
  const H0 = Platform.OS === 'web' ? webH || winH : pageH || winH;
  const switchTop = insets.top + 8 + H.chip + 8;
  const belowSwitch = switchTop + SWITCH_H + 10;
  // 그림 배율: 무대 = 페이지 전체를 덮게(흐린 배경), 방 보기 = 1080 창 세로가 아래 버튼 줄·탭 바 위에서 끝나게 (단짝 발이 안 가려지게)
  const roomH = Math.max(300, H0 - TAB_SPACE - ROOM_BAR);
  const sc = (mode === 'stage' ? H0 : roomH) / CANVAS;
  const offX = (CANVAS - fullWidth / sc) / 2; // 창(1080) 중 화면 밖으로 잘리는 왼쪽 폭 (캔버스 px, 넓은 화면이면 음수)
  const maxWorldX = Math.max(0, ROOM.width - fullWidth / sc);
  // 무대 단짝: 전환 아래 ~ 쪽지 위 사이를 꽉 채우는 크기 (가로는 화면의 92%까지)
  const composerBottom = TAB_SPACE + 12;
  const peekBottom = composerBottom + H.input + 10;
  const stageTop = belowSwitch;
  const stageBottom = H0 - (peekBottom + PEEK_H + 8);
  const petW = Math.round(Math.max(160, Math.min(fullWidth * 0.92, (stageBottom - stageTop) / PET_ASPECT)));
  const petH = Math.round(petW * PET_ASPECT);
  const petTop = stageTop + Math.max(0, (stageBottom - stageTop - petH) / 2);
  const [vase, setVase] = useState(() => store.get(VASE_KEY));
  const [text, setText] = useState('');
  const [chosen, setChosen] = useState<Category | null>(null);
  const [picking, setPicking] = useState(false);
  const [day, setDay] = useState<'today' | 'yesterday'>('today');
  const [busy, setBusy] = useState(false);
  const [action, setAction] = useState<PetAction>(null);
  const [composing, setComposing] = useState(false); // 입력 펼침 (H1)
  const [notesOpen, setNotesOpen] = useState(false); // 오늘의 쪽지 시트 (H2)
  const [rec, setRec] = useState<{ key: number; text: string; category: Category } | null>(null); // 기록 카드 (H4)
  const onPetDone = useCallback((key: number) => { setRec((r) => (r?.key === key ? null : r)); }, []);
  useEffect(() => {
    if (!rec) return;
    const t = setTimeout(() => setRec((r) => (r?.key === rec.key ? null : r)), REC_MAX_MS);
    return () => clearTimeout(t);
  }, [rec]);
  const [bubble, setBubble] = useState('');
  const [float, setFloat] = useState<{ key: number; n: number } | null>(null);
  const [notifAsk, setNotifAsk] = useState(false);
  const [notifTime, setNotifTime] = useState('21:00');
  const [err, setErr] = useState('');
  const bubbleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 펼친 입력은 키보드 바로 위에: 키보드가 이 페이지 아래를 얼마나 덮는지 잰다 (iOS는 화면이 안 줄고, 안드로이드는 줄면 0)
  const wrapRef = useRef<React.ComponentRef<typeof View>>(null);
  const [kb, setKb] = useState(0);
  useEffect(() => {
    const showEv = Platform.OS === 'ios' ? 'keyboardWillShow' : 'keyboardDidShow';
    const hideEv = Platform.OS === 'ios' ? 'keyboardWillHide' : 'keyboardDidHide';
    const show = Keyboard.addListener(showEv, (e) => {
      wrapRef.current?.measureInWindow((_x, y, _w, h) => setKb(Math.max(0, y + h - e.endCoordinates.screenY)));
    });
    const hide = Keyboard.addListener(hideEv, () => setKb(0));
    return () => { show.remove(); hide.remove(); };
  }, []);

  // 웹(폰 사파리 = 웹 테스트판): 입력칸을 누르면 사파리가 키보드 위로 보이게 문서 전체를 위로 밀고, 키보드가 내려가도
  // 안 되돌려서 위 날짜·씨앗 칩이 주소창 밑으로 잘린 채 남음(대표 폰 2026-11-16). 키보드가 내려가면(화면 높이 복귀) 맨 위로 되돌림.
  // 네이티브 앱은 문서 스크롤이 없어 해당 없음
  useEffect(() => {
    if (Platform.OS !== 'web' || typeof window === 'undefined') return;
    const vv = window.visualViewport;
    const reset = () => { if (!vv || vv.height >= window.innerHeight - 40) window.scrollTo(0, 0); };
    vv?.addEventListener('resize', reset);
    window.addEventListener('focusout', reset);
    return () => { vv?.removeEventListener('resize', reset); window.removeEventListener('focusout', reset); };
  }, []);

  // 상점에서 소품을 사거나 바꾸면 그 소품이 보이게 '방 보기'로 (렌더 중 파생: 이펙트 안 setState 금지 규칙)
  const [seenCel, setSeenCel] = useState(celebration?.key);
  if (celebration?.key !== seenCel) {
    setSeenCel(celebration?.key);
    if (celebration?.itemId) setMode('room');
  }

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

  async function submit(raw?: string) {
    const t = (raw ?? text).trim();
    if (!t || busy) return;
    Keyboard.dismiss(); // 보내면 키보드가 내려가며 입력은 다시 한 줄로 (H1)
    setBusy(true); setErr('');
    say('듣고 있어…', 8000);
    const kwSafety = safetyKeywordHit(t);
    // 카테고리를 직접 고르지 않았으면 서버 LLM으로 보정 (실패하면 키워드 결과)
    const llm = await api.classify(t);
    const userPicked = !!chosen && !raw;
    const unsafe = kwSafety || !!llm?.self_harm; // 둘 중 하나라도 걸리면 안내 (안전한 쪽으로)
    // L2: 남을 해치는 표현 → 축하 대신 단짝이 조용히 곁에. 상담 번호 안 띄움, 판정은 어디에도 저장 안 함, 씨앗은 그대로
    const harm = !unsafe && !!llm?.harm_others;
    // 자해·남 해치는 표현이면 '나 돌보기' 같은 분류로 남지 않게 항상 '버틴 하루'로 저장 (사용자가 고른 분류보다 우선)
    const category: Category = unsafe || harm ? 'endure' : userPicked ? chosen! : (llm?.category ?? classifyByKeyword(t));
    const source = unsafe ? 'auto' : userPicked ? 'user' : llm ? 'llm' : 'auto';
    try {
      const winDate = day === 'today' ? today : kstYesterday();
      const r = await api.recordWin(t, category, source, winDate);
      setWins((ws) => [r.win, ...ws]);
      reloadJars().catch(() => {});
      setBalance(r.balance);
      setText(''); setChosen(null); setPicking(false); setDay('today');
      track('win_recorded', { category, source, first: r.first, yesterday: day === 'yesterday', earned: r.earned });
      if (Platform.OS !== 'web') Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});

      if (unsafe) {
        setAction({ kind: 'sit', key: nowKey() });
        say(SAFETY_LINE, 9000);
        // 상담 번호 안내 카드·배너는 지움 (대표 결정 2026-11-16, 홈 무대 개편). 곁에 앉기 + 말풍선은 그대로, 상담 번호는 설정 > 도움받을 곳
        api.logSafety(kwSafety ? 'keyword' : 'llm').catch(() => {}); // 익명 날짜별 개수만 (계정과 연결 안 함, J2)
      } else if (harm) {
        setAction({ kind: 'sit', key: nowKey() });
        say(HARM_LINE, 7000);
      } else {
        const k = nowKey();
        setAction({ kind: eatVariant(category, t) ?? category, key: k });
        // H4: 줌·어둡게 대신 적은 문장이 카드로 떠서 '지금 이걸 축하하는 중'이 보임. 동작 끝(Pet onDone)·화면 탭이면 걷힘
        setRec({ key: k, text: t, category });
        if (r.sealed) {
          say('유리병이 꽉 찼어! 뚜껑 닫아서 선반에 올려둘게. 새 병 시작이야', 6000);
          track('jar_sealed', { no: r.win.jar_no });
        } else say(r.first ? '첫 구슬이 유리병에 들어갔어!' : pickLine(category));
      }
      if (r.earned) {
        const fk = nowKey();
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
      if (st === 'background') { keptCamX = V.start_x; camX.set(V.start_x); setMode('stage'); setComposing(false); } // 다시 열면 하마 무대부터
    });
    return () => sub.remove();
  }, [camX, V.start_x]);
  // 방 끌어 둘러보기는 '방 보기'에서만. 하마 무대에서 좌우로 끌면 페이지 넘기기(pagePan)
  const pan = usePanGesture({
    enabled: mode === 'room',
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
      if (mode === 'stage') { setRec(null); return; } // 무대: 탭하면 기록 카드만 걷음 (단짝 동작은 계속)
      const x = Math.min(maxWorldX, Math.max(0, camX.value + offX)) + e.x / sc, y = e.y / sc;
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
  // 무대: 단짝 가운데 고정(start_x). 방 보기: 둘러본 위치(camX)
  const worldStyle = useAnimatedStyle(() => {
    const x = mode === 'stage' ? V.start_x : camX.value;
    return { transform: [{ translateX: -Math.min(maxWorldX, Math.max(0, x + offX)) * sc }] };
  }, [mode, sc, offX, maxWorldX]);

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

  // 오늘의 쪽지 한 줄을 위로 끌면 시트 (누르기도 됨)
  const peekPan = usePanGesture(useMemo(() => ({
    activeOffsetY: [-10, 10] as [number, number], failOffsetX: [-14, 14] as [number, number], runOnJS: true,
    onActivate: () => setNotesOpen(true),
  }), []));
  // 시트(Modal) 위에 다른 시트를 바로 띄우면 iOS에서 겹쳐 안 뜸 → 닫고 나서
  const afterNotes = (fn: () => void) => { setNotesOpen(false); setTimeout(fn, 350); };

  const stage = mode === 'stage';
  const latest = todayWins[0];
  const roomBtn = (
    <Pressable onPress={() => { setMode(stage ? 'room' : 'stage'); setRec(null); setComposing(false); track('space_viewed', { space: stage ? 'room_view' : 'room' }); }}
      style={st.modeBtn} hitSlop={6} accessibilityRole="button" accessibilityLabel={stage ? '방 보기' : '단짝 보기'}>
      <Icon name={stage ? 'expand' : 'shrink'} size={16} color={C.ink} />
      <Text style={st.modeText}>{stage ? '방' : '단짝'}</Text>
    </Pressable>
  );

  return (
    <GestureDetector gesture={pagePan}>
    <View ref={wrapRef} style={st.wrap}>
      <GestureDetector gesture={roomGesture}>
      <View style={[st.room, { width: fullWidth, height: H0 }, !stage && { backgroundColor: ART.roomFloor }]} accessibilityHint={stage ? undefined : '좌우로 끌면 방을 둘러볼 수 있어요'}>
        <Animated.View style={[{ position: 'absolute', left: 0, top: 0, width: ROOM.width * sc, height: ROOM.height * sc }, worldStyle]}>
          <Image source={ROOM.background} style={StyleSheet.absoluteFill} contentFit="cover" loading="eager" />
          {cab.map((j, i) => {
            const sl = JC.slots[i];
            return (
              <View key={j.no} style={StyleSheet.absoluteFill} pointerEvents="none" accessible={!stage} accessibilityLabel={`${j.no}번째 유리병`}>
                <Image source={JC.jarBack.source} style={{ position: 'absolute', left: sl.back[0] * sc, top: sl.back[1] * sc, width: JC.jarBack.w * sc, height: JC.jarBack.h * sc }} />
                {jarDots(j, sl)}
                <Image source={JC.jarFront.source} style={{ position: 'absolute', left: sl.front[0] * sc, top: sl.front[1] * sc, width: JC.jarFront.w * sc, height: JC.jarFront.h * sc }} />
              </View>
            );
          })}
          <Image source={JC.glass.source} style={{ position: 'absolute', left: JC.glass.x * sc, top: JC.glass.y * sc, width: JC.glass.w * sc, height: JC.glass.h * sc }} />
          {back.map(draw)}
          {!stage && (
            <View style={{ position: 'absolute', left: ROOM.pet.x * sc, top: ROOM.pet.y * sc }}>
              <Pet action={petAction} size={ROOM.pet.w * sc} />
            </View>
          )}
          {front.map(draw)}
        </Animated.View>
        {/* H1 무대: 방을 뿌옇게 (산 소품은 색감으로만). 안드로이드는 실험적 흐림 방식 */}
        {stage && (
          <>
            <BlurView intensity={36} tint="light" experimentalBlurMethod="dimezisBlurView" style={StyleSheet.absoluteFill} pointerEvents="none" />
            <View style={[StyleSheet.absoluteFill, st.veil]} pointerEvents="none" />
          </>
        )}
      </View>
      </GestureDetector>

      {stage && (
        <View pointerEvents="none" style={{ position: 'absolute', left: (fullWidth - petW) / 2, top: petTop }}>
          <Pet action={petAction} size={petW} onDone={onPetDone} />
        </View>
      )}
      {stage && rec && (
        <View pointerEvents="none" style={[st.rec, { top: Math.min(petTop + petH * 0.9, stageBottom - 20) }]}>
          <View style={[st.noteDot, { backgroundColor: CATS[rec.category].color }]} />
          <Text style={st.recText} numberOfLines={2}>{rec.text}</Text>
        </View>
      )}
      {shownBubble ? (
        <View pointerEvents="none" style={[st.bubble, { top: belowSwitch }]}>
          <Text style={st.bubbleText}>{shownBubble}</Text>
        </View>
      ) : null}
      {float && (
        <Text key={float.key} pointerEvents="none" style={[st.float, { top: belowSwitch + 8 }]}>+{float.n} 씨앗</Text>
      )}
      <SpaceChips space="room" extra={roomBtn} />
      {nav && <View style={[st.switchWrap, { top: switchTop }]}><SpaceSwitch nav={nav} style={st.switch} /></View>}

      {/* 하마 무대 아래: 오늘의 쪽지 한 줄(H2). 기록 축하 중·입력 중엔 비켜 줌 */}
      {stage && !rec && !composing && latest && (
        <GestureDetector gesture={peekPan}>
          <Pressable onPress={() => setNotesOpen(true)} style={[st.peek, { bottom: peekBottom }]} accessibilityRole="button" accessibilityLabel={`오늘의 쪽지 ${todayCount}가지, 눌러서 펼치기`}>
            <Text style={st.peekTitle}>오늘의 쪽지 {todayCount}</Text>
            <Text style={st.peekText} numberOfLines={1}>{`· ${latest.text}`}</Text>
            <Icon name="chevronUp" size={18} color={C.muted} />
          </Pressable>
        </GestureDetector>
      )}

      {/* H1 입력: 알약 그 자리에서 바로 적음 (새 창 없음, 대표 피드백 2026-11-16). 적는 동안만 키보드 위로 올라가고
          바로 위에 오늘/어제·예시(빈칸일 때)·분류(적었을 때) 작은 칩이 뜸. 바깥 누르면 키보드만 내려감(적던 글은 남음) */}
      {stage && composing && (
        <Pressable style={[StyleSheet.absoluteFill, { zIndex: 29 }]} onPress={() => Keyboard.dismiss()} accessibilityLabel="입력 닫기" />
      )}
      {stage && !rec && (
        <View style={[st.inputDock, { bottom: composing && kb ? kb + 8 : composerBottom }]}>
          {composing && (
            <View style={st.assist}>
              {err ? <Text style={st.errPill}>{err}</Text> : null}
              {picking && (
                <View style={st.assistRow}>
                  {CATEGORY_ORDER.map((c) => (
                    <Pressable key={c} onPress={() => { setChosen(c); setPicking(false); }} style={[st.chip, st.chipFloat, k === c && st.chipOn]}>
                      <Text style={[st.chipText, k === c && st.chipTextOn]}>{CATS[c].name}</Text>
                    </Pressable>
                  ))}
                </View>
              )}
              <ScrollView horizontal showsHorizontalScrollIndicator={false} keyboardShouldPersistTaps="always" contentContainerStyle={st.assistLine}>
                {(['today', 'yesterday'] as const).map((d) => (
                  <Pressable key={d} onPress={() => setDay(d)} style={[st.chip, st.chipFloat, day === d && st.chipOn]} accessibilityRole="radio" accessibilityState={{ selected: day === d }}>
                    <Text style={[st.chipText, day === d && st.chipTextOn]}>{d === 'today' ? '오늘' : '어제'}</Text>
                  </Pressable>
                ))}
                <View style={st.assistSep} />
                {text.trim() ? (
                  <Pressable onPress={() => setPicking((v) => !v)} style={[st.chip, st.chipFloat]} accessibilityRole="button" accessibilityLabel={`${CATS[k].name} 동작, 눌러서 바꾸기`}>
                    <Text style={st.chipText}><Text style={{ fontWeight: '800' }}>{CATS[k].name}</Text> 동작 · <Text style={st.change}>바꾸기</Text></Text>
                  </Pressable>
                ) : (
                  CHIPS.map((c) => (
                    <Pressable key={c} onPress={() => submit(c)} style={[st.chip, st.chipFloat]} accessibilityRole="button" disabled={busy}>
                      <Text style={st.chipText}>{c}</Text>
                    </Pressable>
                  ))
                )}
              </ScrollView>
            </View>
          )}
          <View style={st.pill}>
            <TextInput
              style={st.pillInput} value={text} onChangeText={(v) => { setText(v); setErr(''); }}
              onFocus={() => setComposing(true)} onBlur={() => { setComposing(false); setPicking(false); }}
              placeholder="오늘 해낸 거, 아무리 작아도 좋아" placeholderTextColor={C.placeholder} maxLength={100} returnKeyType="done"
              onSubmitEditing={() => submit()} accessibilityLabel="오늘 해낸 일" editable={!busy}
            />
            <Pressable onPress={() => submit()} disabled={!text.trim() || busy} accessibilityRole="button" accessibilityLabel="기록"
              style={({ pressed }) => [st.sendSm, (!text.trim() || busy) && { opacity: 0.4 }, pressed && { transform: [{ scale: 0.95 }] }]}>
              {busy ? <ActivityIndicator color={C.white} /> : <Icon name="send" size={20} color={C.white} stroke={2.2} />}
            </Pressable>
          </View>
        </View>
      )}

      {/* H3 방 보기: 아래 버튼 줄 — 수확 바구니(있을 때) + 꾸미기 */}
      {!stage && (
        <View style={[st.roomBar, { top: roomH }]}>
          {bagCount > 0 && (
            <Pressable style={st.barBtn} onPress={() => setBasket(true)} accessibilityRole="button">
              <Icon name="basket" size={20} color={C.accentInk} />
              <Text style={st.barText}>수확 바구니 {bagCount}</Text>
            </Pressable>
          )}
          <Pressable style={[st.barBtn, st.barMain]} onPress={() => router.navigate('/shop')} accessibilityRole="button">
            <Icon name="plant" size={20} color={C.white} />
            <Text style={[st.barText, { color: C.white }]}>꾸미기</Text>
          </Pressable>
        </View>
      )}

      <Sheet visible={notesOpen} onClose={() => setNotesOpen(false)}>
        <View style={st.notesHead}>
          <Text style={sheetSt.title}>오늘의 쪽지 · {todayCount}가지</Text>
          <Pressable onPress={() => afterNotes(() => router.push(`/jar/day/${today}`))} hitSlop={8} accessibilityRole="button" accessibilityLabel="오늘 기록 다 보기">
            <Text style={st.notesMore}>다 보기 ›</Text>
          </Pressable>
        </View>
        <ScrollView style={{ maxHeight: H0 * 0.45 }}>
          {todayWins.map((w) => (
            <Pressable key={w.id} onPress={() => afterNotes(() => openWin(w))} style={st.note} accessibilityRole="button" accessibilityHint="눌러서 크게 보기">
              <View style={[st.noteDot, { backgroundColor: CATS[w.category].color }]} />
              <Text style={st.noteText} numberOfLines={1}>{w.text}</Text>
              {w.starred ? <Icon name="star" size={13} color={C.accentInk} fill={C.accentInk} /> : null}
              <Text style={st.noteTime}>{formatTime(w.created_at)}</Text>
            </Pressable>
          ))}
        </ScrollView>
        <Text style={st.cap}>
          기록 1개 = 씨앗 3개{todayCount >= DAILY_REWARD_CAP ? ' · 오늘 씨앗은 다 받았어. 기록은 얼마든지 남겨도 돼!' : ` (하루 ${DAILY_REWARD_CAP}개 기록까지)`}
        </Text>
      </Sheet>
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
  wrap: { flex: 1, backgroundColor: C.bg, overflow: 'hidden' },
  room: { position: 'absolute', left: 0, top: 0, overflow: 'hidden', backgroundColor: ART.roomFill },
  veil: { backgroundColor: C.stageVeil },
  switchWrap: { position: 'absolute', left: 0, right: 0, alignItems: 'center', zIndex: 15 },
  switch: { alignSelf: 'center', width: 228, backgroundColor: C.chip },
  modeBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, height: H.chip, paddingHorizontal: 12, borderRadius: R.pill, backgroundColor: C.chip },
  modeText: { fontSize: 13, fontWeight: '800', color: C.ink },
  bubble: { position: 'absolute', alignSelf: 'center', maxWidth: '80%', backgroundColor: C.card, borderRadius: R.card, paddingVertical: 10, paddingHorizontal: 16, zIndex: 12 },
  bubbleText: { fontSize: 15, fontWeight: '700', color: C.ink, textAlign: 'center', lineHeight: 21 },
  float: { position: 'absolute', right: 28, fontSize: 16, fontWeight: '800', color: C.seed, zIndex: 12 },
  rec: { position: 'absolute', alignSelf: 'center', maxWidth: '86%', flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: C.card, borderRadius: R.card, paddingVertical: 12, paddingHorizontal: 18, zIndex: 11 },
  recText: { flexShrink: 1, fontSize: 16, fontWeight: '700', color: C.ink },
  peek: { position: 'absolute', left: 16, right: 16, height: PEEK_H, flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, borderRadius: R.card, backgroundColor: C.card, zIndex: 10 },
  peekTitle: { fontSize: 13.5, fontWeight: '800', color: C.ink },
  peekText: { flex: 1, fontSize: 13.5, color: C.muted, marginLeft: 6, marginRight: 6 },
  inputDock: { position: 'absolute', left: 16, right: 16, zIndex: 31 },
  assist: { gap: 8, marginBottom: 8 },
  assistRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, alignItems: 'center' },
  assistLine: { flexDirection: 'row', gap: 6, alignItems: 'center' },
  assistSep: { width: 1, height: 20, backgroundColor: C.divider, marginHorizontal: 2 },
  chipFloat: { backgroundColor: C.card },
  errPill: { alignSelf: 'flex-start', backgroundColor: C.card, color: C.danger, fontSize: 13, borderRadius: R.pill, paddingVertical: 8, paddingHorizontal: 14, overflow: 'hidden' },
  pill: { height: H.input, flexDirection: 'row', alignItems: 'center', paddingLeft: 6, paddingRight: 7, borderRadius: R.pill, backgroundColor: C.card },
  pillInput: { flex: 1, minWidth: 0, height: H.input, fontSize: 15.5, paddingHorizontal: 16, color: C.ink, outlineWidth: 0, outlineStyle: 'none' }, // 웹 포커스 파란 테두리 없앰 (사파리는 outlineWidth만으론 남음)
  sendSm: { width: 42, height: 42, borderRadius: R.pill, backgroundColor: C.accent, alignItems: 'center', justifyContent: 'center' },
  roomBar: { position: 'absolute', left: 0, right: 0, height: ROOM_BAR, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 8, paddingHorizontal: 16 },
  barBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, height: 46, paddingHorizontal: 18, borderRadius: R.pill, backgroundColor: C.card },
  barMain: { backgroundColor: C.accent },
  barText: { fontSize: 14, fontWeight: '800', color: C.accentInk },
  bagRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 10, backgroundColor: C.card, borderRadius: R.card, padding: 10, paddingLeft: 12 },
  bagName: { flex: 1, fontSize: 15, color: C.ink, fontWeight: '600' },
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
  notesHead: { flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between' },
  notesMore: { fontSize: 13, color: C.accentInk, fontWeight: '700' },
  note: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: C.card, borderRadius: R.pill, paddingVertical: 12, paddingHorizontal: 16, marginBottom: 6 },
  noteDot: { width: 9, height: 9, borderRadius: R.pill },
  noteText: { flex: 1, fontSize: 14, color: C.ink },
  noteTime: { fontSize: 11, color: C.muted },
  cap: { fontSize: 12, color: C.muted, marginHorizontal: 6, marginTop: 10, marginBottom: 6, lineHeight: 18 },
});
