import { router } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { useRef, useState } from 'react';
import { Keyboard, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';

import { SLOT_POS } from '@/data/itemSlots';
import { api, friendlyError } from '@/lib/api';
import { track } from '@/lib/analytics';
import { CATEGORY_ORDER, CATS, CHIPS, SAFETY_LINE, classifyByKeyword, pickLine, type Category } from '@/lib/categories';
import { kstToday, kstYesterday } from '@/lib/dates';
import { askPermission } from '@/lib/notifications';
import { safetyKeywordHit } from '@/lib/safety';
import { useApp } from '@/state/app';
import { Btn, HelpLines } from '@/ui/kit';
import { Pet, type PetAction } from '@/ui/Pet';
import { Sheet, st as sheetSt } from '@/ui/Sheet';
import { C, R } from '@/ui/theme';

const DAILY_REWARD_CAP = 10;
const PET_W = 210;
const NOTIF_ASKED_KEY = 'csw.notifAsked';
const SAFETY_DAY_KEY = 'csw.safetyShownDay';

const store = {
  get: (k: string) => { try { return globalThis.localStorage?.getItem(k) ?? null; } catch { return null; } },
  set: (k: string, v: string) => { try { globalThis.localStorage?.setItem(k, v); } catch {} },
};

// 방 = 홈. 기록 입력창·축하 8종·곁에 앉기·먹이기/선물하기는 방에서만 (STATUS 2026-11-09 결정)
export function RoomPage() {
  const { profile, wins, setWins, setBalance, owned, items, updateProfile, session, celebration, celebrate, crops, bag, unlocks, reloadGarden } = useApp();
  const [basket, setBasket] = useState(false);
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

  const today = kstToday();
  const todayCount = wins.filter((w) => w.win_date === today).length;
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
    Keyboard.dismiss();
    setBusy(true); setErr('');
    say('듣고 있어…', 8000);
    const kwSafety = safetyKeywordHit(t);
    // 카테고리를 직접 고르지 않았으면 서버 LLM으로 보정 (실패하면 키워드 결과)
    const llm = await api.classify(t);
    const userPicked = !!chosen && !raw;
    const category: Category = userPicked ? chosen! : (llm?.category ?? classifyByKeyword(t));
    const source = userPicked ? 'user' : llm ? 'llm' : 'auto';
    const unsafe = kwSafety || !!llm?.self_harm; // 둘 중 하나라도 걸리면 안내 (안전한 쪽으로)
    try {
      const winDate = day === 'today' ? today : kstYesterday();
      const r = await api.recordWin(t, category, source, winDate);
      setWins((ws) => [r.win, ...ws]);
      setBalance(r.balance);
      setText(''); setChosen(null); setPicking(false); setDay('today');
      track('win_recorded', { category, source, first: r.first, yesterday: day === 'yesterday', earned: r.earned });
      if (Platform.OS !== 'web') Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});

      if (unsafe) {
        setAction({ kind: 'sit', key: Date.now() });
        say(SAFETY_LINE, 9000);
        const shownToday = store.get(SAFETY_DAY_KEY) === today;
        setSafety(shownToday ? 'banner' : 'card');
        store.set(SAFETY_DAY_KEY, today);
        if (session) api.logSafety(session.user.id, kwSafety ? 'keyword' : 'llm').catch(() => {});
        track('safety_shown', { repeat: shownToday });
      } else {
        setAction({ kind: category, key: Date.now() });
        say(r.first ? '첫 구슬이 유리병에 들어갔어!' : pickLine(category));
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

  // 같은 자리 소품 중 놓인 것만 그린다. 층: 뒤·가운데 → 단짝 → 앞
  const placedIds = new Set(owned.filter((o) => o.placed).map((o) => o.item_id));
  const placed = items.filter((i) => i.space === 'room' && placedIds.has(i.id));
  const drawItem = (it: (typeof items)[number]) => {
    const { size, ...pos } = SLOT_POS[it.slot] ?? { left: '50%', top: '10%', size: 30 };
    return (
      <Animated.Text key={it.id} entering={newItemId === it.id ? FadeIn.duration(600) : undefined}
        style={[st.item, pos, { fontSize: size }]} accessibilityLabel={it.name}>
        {it.emoji}
      </Animated.Text>
    );
  };
  const shelf = crops.filter((c) => unlocks.includes(c.id)).slice(0, 3); // 창턱 수확 선반 3칸
  const bagItems = crops.filter((c) => (bag[c.id] ?? 0) > 0);
  const bagCount = bagItems.reduce((n, c) => n + bag[c.id], 0);

  async function feedOrGift(cropId: string) {
    const c = crops.find((x) => x.id === cropId);
    if (!c) return;
    try {
      await api.useHarvest(cropId);
      setBasket(false);
      await reloadGarden();
      // 채소·열매 = 먹이기(냠냠), 꽃 = 선물하기(냄새 맡고 반짝 → 기지개+회전 재사용)
      if (c.kind === 'edible') celebrate({ kind: 'eat', line: `${c.name} 냠냠, 고마워!` });
      else celebrate({ kind: 'care', line: `${c.name} 향기 좋다! 고마워` });
      track('harvest_used', { crop: cropId, kind: c.kind });
    } catch (e) {
      setErr(friendlyError(e));
    }
  }

  return (
    <View style={st.wrap}>
      <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ paddingBottom: 32 }}>
        <View style={st.room}>
          <View style={st.floor} />
          <View style={st.window}><View style={st.windowBar} /></View>
          <View style={st.shelf} accessibilityLabel="창턱 수확 선반">
            {shelf.map((c) => <Text key={c.id} style={st.shelfItem} accessibilityLabel={c.deco_name}>{c.deco_emoji}</Text>)}
          </View>
          {placed.filter((i) => i.layer !== 'front').map(drawItem)}
          {shownBubble ? (
            <View style={st.bubble}>
              <Text style={st.bubbleText}>{shownBubble}</Text>
            </View>
          ) : null}
          <View style={st.stage}><Pet action={petAction} size={PET_W} /></View>
          {placed.filter((i) => i.layer === 'front').map(drawItem)}

          {float && (
            <Text key={float.key} style={st.float}>+{float.n} 씨앗</Text>
          )}
        </View>

        {bagCount > 0 && (
          <Pressable style={st.basketBtn} onPress={() => setBasket(true)} accessibilityRole="button">
            <Text style={st.basketText}>🧺 수확 바구니 {bagCount}개 · 먹이기/선물하기</Text>
          </Pressable>
        )}
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
            <Text style={st.bannerText}>힘들 땐 109 (24시간) · 도움받을 수 있는 곳 보기 ›</Text>
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
              placeholder="예) 침대 정리했다" maxLength={100} returnKeyType="done"
              onSubmitEditing={() => submit()} accessibilityLabel="오늘 해낸 일" editable={!busy}
            />
            <Btn title="기록" onPress={() => submit()} disabled={!text.trim()} loading={busy} />
          </View>
          {text.trim() ? (
            <View style={st.catLine}>
              <Text style={st.catText}><Text style={{ color: C.ink, fontWeight: '700' }}>{CATS[k].prop} {CATS[k].name}</Text> 동작을 할 거예요 · </Text>
              <Pressable onPress={() => setPicking((p) => !p)} accessibilityRole="button"><Text style={st.change}>바꾸기</Text></Pressable>
            </View>
          ) : null}
          {picking && (
            <View style={st.chips}>
              {CATEGORY_ORDER.map((c) => (
                <Pressable key={c} onPress={() => { setChosen(c); setPicking(false); }} style={[st.chip, k === c && { borderColor: C.accent }]}>
                  <Text style={st.chipText}>{CATS[c].prop} {CATS[c].name}</Text>
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
        <Text style={st.cap}>
          {todayCount > 0 ? `오늘 ${todayCount}가지를 해냈어. ` : ''}
          기록 1개 = 씨앗 3개{todayCount >= DAILY_REWARD_CAP ? ' · 오늘 씨앗은 다 받았어. 기록은 얼마든지 남겨도 돼!' : ` (하루 ${DAILY_REWARD_CAP}개 기록까지)`}
        </Text>
      </ScrollView>

      <Sheet visible={notifAsk} onClose={() => allowNotif(false)}>
        <Text style={sheetSt.title}>내일 이 시간쯤 한 번만 물어봐도 될까?</Text>
        <Text style={sheetSt.body}>하루 한 번, 오늘 해낸 걸 물어볼게. 이미 적은 날엔 안 보내.</Text>
        <View style={[st.chips, { marginBottom: 14 }]}>
          {['20:00', '21:00', '22:00', '23:00'].map((t) => (
            <Pressable key={t} onPress={() => setNotifTime(t)} style={[st.chip, notifTime === t && { borderColor: C.accent, backgroundColor: '#fff' }]}>
              <Text style={st.chipText}>{t}</Text>
            </Pressable>
          ))}
        </View>
        <View style={sheetSt.row}>
          <Btn title="괜찮아" kind="ghost" onPress={() => allowNotif(false)} style={{ flex: 1 }} />
          <Btn title="좋아" onPress={() => allowNotif(true)} style={{ flex: 1 }} />
        </View>
      </Sheet>
      <Sheet visible={basket} onClose={() => setBasket(false)}>
        <Text style={sheetSt.title}>수확 바구니</Text>
        <Text style={sheetSt.body}>먹이거나 선물해도 창턱 장식은 그대로 남아.</Text>
        {bagItems.map((c) => (
          <View key={c.id} style={st.bagRow}>
            <Text style={{ fontSize: 28 }}>{c.emoji}</Text>
            <Text style={st.bagName}>{c.name} {bag[c.id]}개</Text>
            <Btn title={c.kind === 'edible' ? '먹이기' : '선물하기'} onPress={() => feedOrGift(c.id)} />
          </View>
        ))}
      </Sheet>
    </View>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg },
  room: { marginHorizontal: 16, height: 360, borderRadius: 28, overflow: 'hidden', backgroundColor: C.wall },
  floor: { position: 'absolute', left: 0, right: 0, bottom: 0, height: '38%', backgroundColor: C.floor },
  window: { position: 'absolute', left: 24, top: 28, width: 84, height: 70, borderRadius: 14, backgroundColor: '#cfe6f2', borderWidth: 6, borderColor: '#fff' },
  windowBar: { position: 'absolute', left: '50%', marginLeft: -2.5, top: 0, bottom: 0, width: 5, backgroundColor: '#fff' },
  shelf: { position: 'absolute', left: 18, top: 98, width: 96, height: 24, borderBottomWidth: 5, borderBottomColor: '#e8d5b9', flexDirection: 'row', justifyContent: 'space-around', alignItems: 'flex-end' },
  shelfItem: { fontSize: 17 },
  basketBtn: { marginHorizontal: 16, marginTop: 10, backgroundColor: '#fff', borderRadius: 14, paddingVertical: 10, paddingHorizontal: 14, borderWidth: 1, borderColor: C.line },
  basketText: { fontSize: 14, fontWeight: '700', color: C.ink },
  bagRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 10 },
  bagName: { flex: 1, fontSize: 15, color: C.ink, fontWeight: '600' },
  item: { position: 'absolute', fontSize: 34 },
  stage: { position: 'absolute', left: '50%', marginLeft: -PET_W / 2, bottom: -6 }, // 프레임 아래 12%가 빈 공간 → 발이 바닥 위에 오게
  bubble: { position: 'absolute', alignSelf: 'center', top: 12, maxWidth: '80%', backgroundColor: '#fff', borderRadius: 18, paddingVertical: 10, paddingHorizontal: 14, zIndex: 5 },
  bubbleText: { fontSize: 14, fontWeight: '600', color: C.ink, textAlign: 'center', lineHeight: 20 },
  float: { position: 'absolute', right: 28, top: 80, fontSize: 16, fontWeight: '800', color: C.seed },
  composer: { marginHorizontal: 16, marginTop: 14, backgroundColor: '#fff', borderRadius: R.card, padding: 16, borderWidth: 1, borderColor: C.line },
  label: { fontSize: 17, fontWeight: '800', color: C.ink, marginBottom: 10 },
  dayRow: { flexDirection: 'row', gap: 6, marginBottom: 10 },
  dayBtn: { paddingVertical: 5, paddingHorizontal: 12, borderRadius: R.pill, borderWidth: 1, borderColor: C.line },
  dayOn: { backgroundColor: C.ink, borderColor: C.ink },
  dayText: { fontSize: 13, color: C.muted, fontWeight: '600' },
  dayTextOn: { color: '#fff' },
  row: { flexDirection: 'row', gap: 8 },
  input: { flex: 1, minWidth: 0, fontSize: 16, paddingVertical: 12, paddingHorizontal: 14, borderRadius: R.input, borderWidth: 1.5, borderColor: C.line, backgroundColor: C.room, color: C.ink },
  catLine: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', marginTop: 12 },
  catText: { fontSize: 13, color: C.muted },
  change: { fontSize: 13, color: C.accent, textDecorationLine: 'underline' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 12 },
  chip: { paddingVertical: 7, paddingHorizontal: 11, borderRadius: R.pill, borderWidth: 1, borderColor: C.line, backgroundColor: C.room },
  chipText: { fontSize: 13, color: C.ink },
  err: { marginTop: 10, color: '#c0392b', fontSize: 13 },
  cap: { fontSize: 12, color: C.muted, marginHorizontal: 20, marginTop: 10 },
  safetyCard: { marginHorizontal: 16, marginTop: 14, backgroundColor: '#fff', borderRadius: R.card, padding: 16, borderWidth: 1, borderColor: C.line },
  safetyTitle: { fontSize: 16, fontWeight: '800', color: C.ink, marginBottom: 4 },
  safetyBody: { fontSize: 13, color: C.muted, marginBottom: 12, lineHeight: 19 },
  banner: { marginHorizontal: 16, marginTop: 12, backgroundColor: '#fff', borderRadius: 14, padding: 12, borderWidth: 1, borderColor: C.line },
  bannerText: { fontSize: 13, color: C.ink, fontWeight: '600' },
});
