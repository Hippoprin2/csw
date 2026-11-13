import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import type { JarInfo, Win } from '@/lib/api';
import { track } from '@/lib/analytics';
import { CATEGORY_ORDER, CATS } from '@/lib/categories';
import { addDays, formatDay, kstToday, weekStart } from '@/lib/dates';
import { jarMarbles, shelfByYear } from '@/lib/jars';
import { useApp } from '@/state/app';
import { Icon } from '@/ui/Icon';
import { Card, H, Sub } from '@/ui/kit';
import { WinList } from '@/ui/WinList';
import { ART, C, H as HT, R, TAB_SPACE } from '@/ui/theme';

const RECENT_LIST_DAYS = 14; // 유리병 화면 목록은 최근 2주만. 그 전은 선반의 병을 열거나 찾기 (FEATURES C6 J1-A)

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

function WeekCard({ start, wins, title }: { start: string; wins: Win[]; title: string }) {
  const end = addDays(start, 6);
  const ws = wins.filter((w) => w.win_date >= start && w.win_date <= end);
  const byCat = CATEGORY_ORDER.map((c) => [c, ws.filter((w) => w.category === c).length] as const).filter(([, n]) => n > 0);
  // 반복 적은 기록 우선으로 "이 순간 기억나?" 하나 고르기 (주 단위로 고정)
  // '버틴 하루'(힘든 마음 기록)는 다시 꺼내 보여주지 않는다 (2026-11-10 대표 결정)
  let memory: Win | null = null;
  const pool = ws.filter((w) => w.category !== 'endure');
  if (pool.length) {
    const freq = new Map<string, number>();
    pool.forEach((w) => freq.set(w.text, (freq.get(w.text) ?? 0) + 1));
    const rare = pool.filter((w) => freq.get(w.text) === Math.min(...freq.values()));
    memory = rare[start.split('-').reduce((a, b) => a + Number(b), 0) % rare.length];
  }

  return (
    <Card style={{ marginBottom: 14 }}>
      <Text style={st.weekTitle}>{title}</Text>
      {ws.length === 0 ? (
        <Text style={st.weekBody}>이번 주에 한 가장 작은 일 하나만 떠올려볼래?</Text>
      ) : (
        <>
          <Text style={st.weekBig}>너는 {ws.length}가지를 해냈어</Text>
          <View style={st.marbles}>
            {ws.slice(0, 40).map((w) => <View key={w.id} style={[st.marble, { backgroundColor: CATS[w.category].color }]} />)}
            {ws.length > 40 ? <Text style={st.more}>+{ws.length - 40}</Text> : null}
          </View>
          <View style={st.catRow}>
            {byCat.map(([c, n]) => (
              <View key={c} style={st.catPill}>
                <View style={[st.catDot, { backgroundColor: CATS[c].color }]} />
                <Text style={st.catPillText}>{CATS[c].name} {n}</Text>
              </View>
            ))}
          </View>
          {memory ? (
            <View style={st.memory}>
              <Text style={st.memoryQ}>이 순간 기억나?</Text>
              <Text style={st.memoryT}>“{memory.text}” · {formatDay(memory.win_date)}</Text>
            </View>
          ) : null}
        </>
      )}
    </Card>
  );
}

export default function Jar() {
  const { wins, jars } = useApp();
  const [showPast, setShowPast] = useState(false);
  const [openYears, setOpenYears] = useState<Record<string, boolean>>({});

  const today = kstToday();
  const thisWeek = weekStart(today);
  const current = wins.filter((w) => w.jar_no === jars.current_jar);
  const shelf = shelfByYear(jars);
  const recentFrom = addDays(today, -(RECENT_LIST_DAYS - 1));
  const recent = wins.filter((w) => w.win_date >= recentFrom);
  const hasOlder = jars.total > recent.length;
  const pastWeeks = [...new Set(wins.map((w: Win) => weekStart(w.win_date)).filter((s) => s < thisWeek))].sort().reverse().slice(0, 12);

  return (
    <SafeAreaView style={st.wrap} edges={['top']}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: TAB_SPACE + 16 }}>
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

        <View style={st.jar} accessibilityLabel={`${jars.current_jar}번째 병, 구슬 ${current.length}개`}>
          {[...current].reverse().map((w) => <View key={w.id} style={[st.jarMarble, { backgroundColor: CATS[w.category].color }]} />)}
        </View>
        {jars.current_jar > 1 && (
          <Text style={st.jarCaption}>
            {current.length === 0 ? '새 병이야. 다음 구슬은 여기에 들어가.' : `${jars.current_jar}번째 병`}
          </Text>
        )}

        {shelf.length > 0 && (
          <View style={{ marginBottom: 18 }}>
            <Text style={st.weekTitle}>선반 · 꽉 찬 병 {shelf.reduce((n, y) => n + y.jars.length, 0)}개</Text>
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

        <WeekCard start={thisWeek} wins={wins} title="이번 주 유리병" />
        {pastWeeks.length > 0 && (
          <Pressable onPress={() => { setShowPast((v) => !v); if (!showPast) track('weekly_viewed', { weeks: pastWeeks.length }); }} style={{ marginBottom: 14 }}>
            <Text style={st.link}>{showPast ? '지난 주 접기' : `지난 주 돌아보기 (${pastWeeks.length})`}</Text>
          </Pressable>
        )}
        {showPast && pastWeeks.map((s) => (
          <WeekCard key={s} start={s} wins={wins} title={`${formatDay(s)} 주`} />
        ))}

        {jars.total === 0 && <Text style={st.empty}>아직 구슬이 없어. 방에서 오늘 해낸 걸 하나 적어볼래?</Text>}
        {recent.length > 0 && <Text style={st.weekTitle}>최근 2주</Text>}
        <WinList wins={recent} />
        {hasOlder && <Text style={st.older}>더 지난 기록은 선반의 병을 열거나 찾기로 볼 수 있어. 하나도 없어지지 않아.</Text>}
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, maxWidth: 520, width: '100%', alignSelf: 'center' },
  headRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  searchBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, height: HT.chip, paddingHorizontal: 14, borderRadius: R.pill, backgroundColor: C.soft },
  searchTxt: { fontSize: 13, color: C.ink, fontWeight: '700' },
  // 병 그림 (유리병 자체는 화면 속 소품이라 선을 유지)
  jar: { alignSelf: 'center', width: 150, height: 170, borderWidth: 4, borderTopWidth: 10, borderColor: ART.jarLine, borderTopLeftRadius: 26, borderTopRightRadius: 26, borderBottomLeftRadius: 40, borderBottomRightRadius: 40, backgroundColor: ART.jarGlass, flexDirection: 'row', flexWrap: 'wrap-reverse', alignContent: 'flex-start', padding: 9, gap: 3, overflow: 'hidden', marginBottom: 8 },
  // 50개가 다 들어가는 크기 (한 줄 7개 × 8줄)
  jarMarble: { width: 14, height: 14, borderRadius: 7 },
  jarCaption: { textAlign: 'center', fontSize: 13, color: C.muted, marginBottom: 18 },
  yearRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginBottom: 6 },
  yearH: { fontSize: 13, color: C.ink, fontWeight: '700' },
  shelf: { gap: 12, paddingHorizontal: 6, alignItems: 'flex-end' },
  shelfBoard: { height: 8, borderRadius: 4, backgroundColor: ART.jarLine, marginTop: -2 },
  shelfItem: { alignItems: 'center', width: 64 },
  lid: { width: 40, height: 9, borderRadius: 3, backgroundColor: ART.jarLid, marginBottom: -1 },
  miniJar: { width: 54, height: 62, borderWidth: 3, borderColor: ART.jarLine, borderTopLeftRadius: 10, borderTopRightRadius: 10, borderBottomLeftRadius: 16, borderBottomRightRadius: 16, backgroundColor: ART.jarGlass, flexDirection: 'row', flexWrap: 'wrap-reverse', alignContent: 'flex-start', padding: 3, gap: 1, overflow: 'hidden' },
  miniMarble: { width: 6, height: 6, borderRadius: 3 },
  shelfLabel: { fontSize: 11, color: C.muted, marginTop: 4, marginBottom: 6 },
  weekTitle: { fontSize: 13, color: C.muted, fontWeight: '700', marginBottom: 8, marginLeft: 4 },
  weekBig: { fontSize: 19, fontWeight: '800', color: C.ink, marginBottom: 12 },
  weekBody: { fontSize: 15, color: C.ink, lineHeight: 22 },
  marbles: { flexDirection: 'row', flexWrap: 'wrap', gap: 4, marginBottom: 12, alignItems: 'center' },
  marble: { width: 14, height: 14, borderRadius: 7 },
  more: { fontSize: 12, color: C.muted, marginLeft: 4 },
  catRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 12 },
  catPill: { flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: C.soft, borderRadius: R.pill, height: 28, paddingHorizontal: 11 },
  catDot: { width: 8, height: 8, borderRadius: R.pill },
  catPillText: { fontSize: 12, color: C.ink },
  memory: { backgroundColor: C.soft, borderRadius: R.card, padding: 16 },
  memoryQ: { fontSize: 12, color: C.muted, marginBottom: 4 },
  memoryT: { fontSize: 14, color: C.ink, fontWeight: '600' },
  link: { fontSize: 14, color: C.accentInk, fontWeight: '700', marginLeft: 4 },
  empty: { textAlign: 'center', color: C.muted, paddingVertical: 30, fontSize: 14 },
  older: { textAlign: 'center', color: C.muted, fontSize: 13, lineHeight: 19, paddingVertical: 12 },
});
