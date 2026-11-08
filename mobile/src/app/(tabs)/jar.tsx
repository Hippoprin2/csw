import { useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api, friendlyError, type Win } from '@/lib/api';
import { track } from '@/lib/analytics';
import { CATEGORY_ORDER, CATS, type Category } from '@/lib/categories';
import { addDays, formatDay, kstToday, weekStart } from '@/lib/dates';
import { useApp } from '@/state/app';
import { Btn, Card, H, Sub } from '@/ui/kit';
import { Confirm, Sheet, st as sheetSt } from '@/ui/Sheet';
import { C, R } from '@/ui/theme';

const COLLAPSE_OVER = 6; // 하루 기록이 많으면 접어서 표시

type Row = { key: string; text: string; category: Category; count: number; latest: Win };

// 같은 날 같은 내용은 한 줄로 묶기 ("물 마셨다 ×4")
function groupDay(ws: Win[]): Row[] {
  const m = new Map<string, Row>();
  for (const w of ws) {
    const key = w.text.trim();
    const r = m.get(key);
    if (r) r.count++;
    else m.set(key, { key: w.id, text: key, category: w.category, count: 1, latest: w });
  }
  return [...m.values()];
}

function WeekCard({ start, wins, title }: { start: string; wins: Win[]; title: string }) {
  const end = addDays(start, 6);
  const ws = wins.filter((w) => w.win_date >= start && w.win_date <= end);
  const byCat = CATEGORY_ORDER.map((c) => [c, ws.filter((w) => w.category === c).length] as const).filter(([, n]) => n > 0);
  // 반복 적은 기록 우선으로 "이 순간 기억나?" 하나 고르기 (주 단위로 고정)
  let memory: Win | null = null;
  if (ws.length) {
    const freq = new Map<string, number>();
    ws.forEach((w) => freq.set(w.text, (freq.get(w.text) ?? 0) + 1));
    const rare = ws.filter((w) => freq.get(w.text) === Math.min(...freq.values()));
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
            {byCat.map(([c, n]) => <Text key={c} style={st.catPill}>{CATS[c].prop} {CATS[c].name} {n}</Text>)}
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
  const { wins, setWins } = useApp();
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [showPast, setShowPast] = useState(false);
  const [edit, setEdit] = useState<Win | null>(null);
  const [editText, setEditText] = useState('');
  const [editCat, setEditCat] = useState<Category>('cheer');
  const [confirmDel, setConfirmDel] = useState(false);
  const [err, setErr] = useState('');

  const today = kstToday();
  const thisWeek = weekStart(today);
  const days = useMemo(() => {
    const m = new Map<string, Win[]>();
    wins.forEach((w) => m.set(w.win_date, [...(m.get(w.win_date) ?? []), w]));
    return [...m.entries()].sort((a, b) => (a[0] < b[0] ? 1 : -1));
  }, [wins]);
  const pastWeeks = useMemo(() => {
    const set = new Set(wins.map((w) => weekStart(w.win_date)).filter((s) => s < thisWeek));
    return [...set].sort().reverse().slice(0, 12);
  }, [wins, thisWeek]);

  function startEdit(w: Win) {
    setEdit(w); setEditText(w.text); setEditCat(w.category); setErr('');
  }
  async function saveEdit() {
    if (!edit) return;
    try {
      const w = await api.editWin(edit.id, editText.trim(), editCat);
      setWins((ws) => ws.map((x) => (x.id === w.id ? w : x)));
      track('win_edited');
      setEdit(null);
    } catch (e) { setErr(friendlyError(e)); }
  }
  async function del() {
    if (!edit) return;
    try {
      await api.deleteWin(edit.id);
      setWins((ws) => ws.filter((x) => x.id !== edit.id));
      track('win_deleted');
      setConfirmDel(false); setEdit(null);
    } catch (e) { setErr(friendlyError(e)); setConfirmDel(false); }
  }

  return (
    <SafeAreaView style={st.wrap} edges={['top']}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
        <H>나의 작은 승리 유리병</H>
        <Sub>지금까지 구슬 {wins.length}개. 구슬은 줄어들지 않아.</Sub>

        <View style={st.jar}>
          {wins.slice(0, 60).map((w) => <View key={w.id} style={[st.jarMarble, { backgroundColor: CATS[w.category].color }]} />)}
        </View>

        <WeekCard start={thisWeek} wins={wins} title="이번 주 유리병" />
        {pastWeeks.length > 0 && (
          <Pressable onPress={() => { setShowPast((v) => !v); if (!showPast) track('weekly_viewed', { weeks: pastWeeks.length }); }} style={{ marginBottom: 14 }}>
            <Text style={st.link}>{showPast ? '지난 주 접기' : `지난 주 돌아보기 (${pastWeeks.length})`}</Text>
          </Pressable>
        )}
        {showPast && pastWeeks.map((s) => (
          <WeekCard key={s} start={s} wins={wins} title={`${formatDay(s)} 주`} />
        ))}

        {days.length === 0 && <Text style={st.empty}>아직 구슬이 없어. 방에서 오늘 해낸 걸 하나 적어볼래?</Text>}
        {days.map(([d, ws]) => {
          const rows = groupDay(ws);
          const collapsed = ws.length > COLLAPSE_OVER && !open[d];
          return (
            <View key={d} style={{ marginBottom: 16 }}>
              <Text style={st.dayH}>{formatDay(d)}</Text>
              {collapsed ? (
                <Pressable onPress={() => setOpen((o) => ({ ...o, [d]: true }))} style={st.win}>
                  <Text style={[st.winText, { fontWeight: '700' }]}>{formatDay(d)} {ws.length}가지 · 펼치기</Text>
                </Pressable>
              ) : rows.map((r) => (
                <Pressable key={r.key} onPress={() => startEdit(r.latest)} style={st.win} accessibilityRole="button" accessibilityHint="눌러서 고치기">
                  <View style={[st.dot, { backgroundColor: CATS[r.category].color }]} />
                  <Text style={st.winText}>{r.text}{r.count > 1 ? `  ×${r.count}` : ''}</Text>
                  <Text style={st.tag}>{CATS[r.category].name}</Text>
                </Pressable>
              ))}
            </View>
          );
        })}
      </ScrollView>

      <Sheet visible={!!edit && !confirmDel} onClose={() => setEdit(null)}>
        <Text style={sheetSt.title}>기록 고치기</Text>
        <TextInput style={st.input} value={editText} onChangeText={setEditText} maxLength={100} accessibilityLabel="기록 내용" />
        <View style={st.catRow}>
          {CATEGORY_ORDER.map((c) => (
            <Pressable key={c} onPress={() => setEditCat(c)} style={[st.chip, editCat === c && { borderColor: C.accent, backgroundColor: '#fff' }]}>
              <Text style={{ fontSize: 13, color: C.ink }}>{CATS[c].prop} {CATS[c].name}</Text>
            </Pressable>
          ))}
        </View>
        {err ? <Text style={{ color: '#c0392b', fontSize: 13, marginBottom: 8 }}>{err}</Text> : null}
        <View style={sheetSt.row}>
          <Btn title="지우기" kind="ghost" onPress={() => setConfirmDel(true)} style={{ flex: 1 }} />
          <Btn title="저장" onPress={saveEdit} disabled={!editText.trim()} style={{ flex: 1 }} />
        </View>
      </Sheet>
      <Confirm
        visible={confirmDel} title="이 기록을 지울까?" body="이미 받은 씨앗은 그대로 있어." confirm="지우기" danger
        onConfirm={del} onCancel={() => setConfirmDel(false)}
      />
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, maxWidth: 520, width: '100%', alignSelf: 'center' },
  jar: { alignSelf: 'center', width: 150, height: 170, borderWidth: 4, borderTopWidth: 10, borderColor: '#d9c9b1', borderTopLeftRadius: 26, borderTopRightRadius: 26, borderBottomLeftRadius: 40, borderBottomRightRadius: 40, backgroundColor: '#fffaf2', flexDirection: 'row', flexWrap: 'wrap-reverse', alignContent: 'flex-start', padding: 10, gap: 5, overflow: 'hidden', marginBottom: 18 },
  jarMarble: { width: 20, height: 20, borderRadius: 10 },
  weekTitle: { fontSize: 13, color: C.muted, fontWeight: '700', marginBottom: 6 },
  weekBig: { fontSize: 18, fontWeight: '800', color: C.ink, marginBottom: 10 },
  weekBody: { fontSize: 15, color: C.ink, lineHeight: 22 },
  marbles: { flexDirection: 'row', flexWrap: 'wrap', gap: 4, marginBottom: 10, alignItems: 'center' },
  marble: { width: 14, height: 14, borderRadius: 7 },
  more: { fontSize: 12, color: C.muted, marginLeft: 4 },
  catRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 12 },
  catPill: { fontSize: 12, color: C.ink, backgroundColor: C.room, borderRadius: R.pill, paddingVertical: 4, paddingHorizontal: 9, overflow: 'hidden' },
  memory: { backgroundColor: C.room, borderRadius: 14, padding: 12 },
  memoryQ: { fontSize: 12, color: C.muted, marginBottom: 4 },
  memoryT: { fontSize: 14, color: C.ink, fontWeight: '600' },
  link: { fontSize: 14, color: C.accent, fontWeight: '700' },
  empty: { textAlign: 'center', color: C.muted, paddingVertical: 30, fontSize: 14 },
  dayH: { fontSize: 13, color: C.muted, fontWeight: '600', marginBottom: 8 },
  win: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: '#fff', borderRadius: 16, paddingVertical: 12, paddingHorizontal: 14, marginBottom: 6, borderWidth: 1, borderColor: C.line },
  dot: { width: 10, height: 10, borderRadius: 5 },
  winText: { flex: 1, fontSize: 15, color: C.ink },
  tag: { fontSize: 11, color: C.muted, backgroundColor: C.room, paddingVertical: 3, paddingHorizontal: 8, borderRadius: R.pill, overflow: 'hidden' },
  input: { fontSize: 16, padding: 12, borderRadius: R.input, borderWidth: 1.5, borderColor: C.line, backgroundColor: '#fff', color: C.ink, marginBottom: 12 },
  chip: { paddingVertical: 6, paddingHorizontal: 10, borderRadius: R.pill, borderWidth: 1, borderColor: C.line, backgroundColor: C.room },
});
