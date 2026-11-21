import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { type JarInfo, type Win } from '@/lib/api';
import { track } from '@/lib/analytics';
import { CATEGORY_ORDER, CATS } from '@/lib/categories';
import { addDays, formatDay, kstToday, weekStart } from '@/lib/dates';
import { jarMarbles, shelfByYear } from '@/lib/jars';
import { useApp } from '@/state/app';
import { CatChips } from '@/ui/CatChips';
import { Icon } from '@/ui/Icon';
import { MarbleJar } from '@/ui/MarbleJar';
import { H, Sub } from '@/ui/kit';
import { WinList } from '@/ui/WinList';
import { useWinSheet } from '@/ui/WinSheet';
import { ART, C, H as HT, R, TAB_SPACE } from '@/ui/theme';

// 유리병 탭 = 시간 순서 하나 (2026-11-16 대표 결정 G1-A·G2-A·G3-A·F-B, 시안 design/jar_page/sheet5)
// 병(쓸어 보기) → 분류 칩 → '이 순간 기억나?' 한 장 → 이번 주(머리말 + 날짜별) → 지난 주 → 더 지난 기록(선반)
// 3주 전부터는 선반의 병·분류 칩·찾기로 본다 (하나도 없어지지 않음)

// 선반 위 닫힌 병 (뚜껑 + 구슬 색)
function ShelfJar({ jar }: { jar: JarInfo }) {
  return (
    <Pressable
      onPress={() => { track('jar_viewed', { no: jar.no }); router.push(`/jar/${jar.no}`); }}
      style={st.shelfItem} accessibilityRole="button" accessibilityLabel={`${jar.no}번째 병, 구슬 ${jar.count}개, 눌러서 열기`}
    >
      <View style={st.lid} />
      <View style={st.miniJar}>
        {jarMarbles(jar).map((c, i) => <View key={i} style={[st.miniMarble, { backgroundColor: CATS[c].color }]} />)}
      </View>
      <Text style={st.shelfLabel}>{jar.no}번째 병</Text>
    </Pressable>
  );
}

// '이 순간 기억나?' 한 장: 이번 주(없으면 지난 주)에서 반복이 적은 기록 하나, 주 단위로 고정
// '버틴 하루'(힘든 마음 기록)는 다시 꺼내 보여주지 않는다 (2026-11-10 대표 결정)
function pickMemory(ws: Win[], seed: string): Win | null {
  const pool = ws.filter((w) => w.category !== 'endure');
  if (!pool.length) return null;
  const freq = new Map<string, number>();
  pool.forEach((w) => freq.set(w.text, (freq.get(w.text) ?? 0) + 1));
  const rare = pool.filter((w) => freq.get(w.text) === Math.min(...freq.values()));
  return rare[seed.split('-').reduce((a, b) => a + Number(b), 0) % rare.length];
}

function Memory({ win }: { win: Win }) {
  const { openWin } = useWinSheet();
  return (
    <Pressable style={st.memory} onPress={() => openWin(win)} accessibilityRole="button" accessibilityHint="눌러서 크게 보기">
      <Text style={st.memoryQ}>이 순간 기억나?</Text>
      <Text style={st.memoryT}>“{win.text}” · {formatDay(win.win_date)}</Text>
    </Pressable>
  );
}

// 한 주 묶음: 작은 제목 + "N가지 해냈어" + 분류 점(많은 순) + 날짜별 기록
function WeekSection({ label, ws }: { label: string; ws: Win[] }) {
  const byCat = CATEGORY_ORDER.map((c) => [c, ws.filter((w) => w.category === c).length] as const)
    .filter(([, n]) => n > 0).sort((a, b) => b[1] - a[1]);
  return (
    <View style={st.week}>
      <Text style={st.weekLabel}>{label}</Text>
      {ws.length === 0 ? (
        <Text style={st.weekBody}>이번 주에 한 가장 작은 일 하나만 떠올려볼래?</Text>
      ) : (
        <>
          <Text style={st.weekBig}>{ws.length}가지 해냈어</Text>
          <View style={st.dots} accessibilityLabel={byCat.map(([c, n]) => `${CATS[c].name} ${n}`).join(', ')}>
            {byCat.map(([c, n]) => (
              <View key={c} style={st.dotItem}>
                <View style={[st.catDot, { backgroundColor: CATS[c].color }]} />
                <Text style={st.dotNum}>{n}</Text>
              </View>
            ))}
          </View>
          <WinList wins={ws} />
        </>
      )}
    </View>
  );
}

export default function Jar() {
  const { wins, jars } = useApp();
  const [openYears, setOpenYears] = useState<Record<string, boolean>>({});
  const [locked, setLocked] = useState(false); // 구슬 쓸어 보는 동안 화면 스크롤 멈춤

  const today = kstToday();
  const thisWeek = weekStart(today);
  const lastWeek = addDays(thisWeek, -7);
  const current = wins.filter((w) => w.jar_no === jars.current_jar).sort((a, b) => (a.created_at < b.created_at ? -1 : 1));
  const thisWs = wins.filter((w) => w.win_date >= thisWeek && w.win_date <= today);
  const lastWs = wins.filter((w) => w.win_date >= lastWeek && w.win_date < thisWeek);
  const memory = pickMemory(thisWs, thisWeek) ?? pickMemory(lastWs, lastWeek);
  const shelf = shelfByYear(jars);
  const shelfCount = shelf.reduce((n, y) => n + y.jars.length, 0);
  const hasOlder = jars.total > thisWs.length + lastWs.length;

  return (
    <SafeAreaView style={st.wrap} edges={['top']}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: TAB_SPACE + 16 }} scrollEnabled={!locked}>
        <View style={st.headRow}>
          <H>나의 작은 승리 유리병</H>
          {jars.total > 0 && (
            <Pressable onPress={() => router.push('/jar/search')} style={st.searchBtn} accessibilityRole="button" accessibilityLabel="기록 찾기">
              <Icon name="search" size={18} color={C.ink} />
              <Text style={st.searchTxt}>찾기</Text>
            </Pressable>
          )}
        </View>
        <Sub>지금까지 구슬 {jars.total}개. 구슬은 줄어들지 않아.</Sub>

        <MarbleJar
          wins={current} label={`${jars.current_jar}번째 병, 구슬 ${current.length}개`}
          listHref={`/jar/${jars.current_jar}`} onScrollLock={setLocked}
        />
        {jars.current_jar > 1 && (
          <Text style={st.jarCaption}>
            {current.length === 0 ? '새 병이야. 다음 구슬은 여기에 들어가.' : `${jars.current_jar}번째 병`}
          </Text>
        )}

        {jars.total > 0 && <CatChips style={{ marginBottom: 14 }} />}
        {memory && <Memory win={memory} />}

        {jars.total === 0 ? (
          <Text style={st.empty}>아직 구슬이 없어. 방에서 오늘 해낸 걸 하나 적어볼래?</Text>
        ) : (
          <>
            <WeekSection label="이번 주" ws={thisWs} />
            {lastWs.length > 0 && <><View style={st.divider} /><WeekSection label="지난 주" ws={lastWs} /></>}
          </>
        )}

        {(hasOlder || shelfCount > 0) && (
          <>
            <View style={st.divider} />
            <Text style={st.weekLabel}>더 지난 기록</Text>
            <Text style={st.olderBig}>하나도 없어지지 않아</Text>
            {shelfCount > 0 && (
              <View style={{ marginBottom: 6 }}>
                <Text style={st.shelfTitle}>선반 · 꽉 찬 병 {shelfCount}개</Text>
                {shelf.map((y, idx) => {
                  const opened = idx === 0 || openYears[y.year];
                  return (
                    <View key={y.year} style={{ marginBottom: 10 }}>
                      {shelf.length > 1 && (
                        <Pressable onPress={() => setOpenYears((o) => ({ ...o, [y.year]: !opened }))} disabled={idx === 0} style={st.yearRow}>
                          <Text style={st.yearH}>{y.year}년 · 병 {y.jars.length}개</Text>
                          {idx === 0 ? null : <Icon name={opened ? 'chevronDown' : 'chevronRight'} size={16} color={C.muted} />}
                        </Pressable>
                      )}
                      {opened && (
                        <>
                          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={st.shelf}>
                            {y.jars.map((j) => <ShelfJar key={j.no} jar={j} />)}
                          </ScrollView>
                          <View style={st.shelfBoard} />
                        </>
                      )}
                    </View>
                  );
                })}
              </View>
            )}
            <Text style={st.older}>분류 칩이나 위 찾기로도 볼 수 있어</Text>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, maxWidth: 520, width: '100%', alignSelf: 'center' },
  headRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  searchBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, height: HT.chip, paddingHorizontal: 14, borderRadius: R.pill, backgroundColor: C.soft },
  searchTxt: { fontSize: 13, color: C.ink, fontWeight: '700' },
  jarCaption: { textAlign: 'center', fontSize: 13, color: C.muted, marginBottom: 18 },
  memory: { backgroundColor: C.soft, borderRadius: R.card, padding: 16, marginBottom: 22 },
  memoryQ: { fontSize: 12, color: C.muted, marginBottom: 4 },
  memoryT: { fontSize: 14, color: C.ink, fontWeight: '600' },
  week: { marginBottom: 4 },
  weekLabel: { fontSize: 13, color: C.muted, fontWeight: '700', marginLeft: 4, marginBottom: 2 },
  weekBig: { fontSize: 21, fontWeight: '800', color: C.ink, marginLeft: 4, marginBottom: 8 },
  weekBody: { fontSize: 15, color: C.ink, lineHeight: 22, marginLeft: 4, marginTop: 4, marginBottom: 16 },
  dots: { flexDirection: 'row', flexWrap: 'wrap', columnGap: 10, rowGap: 4, marginLeft: 4, marginBottom: 14 },
  dotItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  catDot: { width: 8, height: 8, borderRadius: R.pill },
  dotNum: { fontSize: 12, color: C.muted },
  divider: { height: 8, borderRadius: R.pill, backgroundColor: C.soft, marginHorizontal: -20, marginTop: 4, marginBottom: 22 },
  olderBig: { fontSize: 21, fontWeight: '800', color: C.ink, marginLeft: 4, marginBottom: 14 },
  shelfTitle: { fontSize: 13, color: C.muted, fontWeight: '700', marginBottom: 8, marginLeft: 4 },
  yearRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginBottom: 6 },
  yearH: { fontSize: 13, color: C.ink, fontWeight: '700' },
  shelf: { gap: 12, paddingHorizontal: 6, alignItems: 'flex-end' },
  shelfBoard: { height: 8, borderRadius: 4, backgroundColor: ART.jarLine, marginTop: -2 },
  shelfItem: { alignItems: 'center', width: 64 },
  lid: { width: 40, height: 9, borderRadius: 3, backgroundColor: ART.jarLid, marginBottom: -1 },
  miniJar: { width: 54, height: 62, borderWidth: 3, borderColor: ART.jarLine, borderTopLeftRadius: 10, borderTopRightRadius: 10, borderBottomLeftRadius: 16, borderBottomRightRadius: 16, backgroundColor: ART.jarGlass, flexDirection: 'row', flexWrap: 'wrap-reverse', alignContent: 'flex-start', padding: 3, gap: 1, overflow: 'hidden' },
  miniMarble: { width: 6, height: 6, borderRadius: 3 },
  shelfLabel: { fontSize: 11, color: C.muted, marginTop: 4, marginBottom: 6 },
  empty: { textAlign: 'center', color: C.muted, paddingVertical: 30, fontSize: 14 },
  older: { textAlign: 'center', color: C.muted, fontSize: 13, lineHeight: 19, paddingVertical: 12 },
});
