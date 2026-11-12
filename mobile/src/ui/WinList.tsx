import { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { api, friendlyError, type Win } from '@/lib/api';
import { track } from '@/lib/analytics';
import { CATEGORY_ORDER, CATS, type Category } from '@/lib/categories';
import { formatDay } from '@/lib/dates';
import { useApp } from '@/state/app';
import { Btn } from '@/ui/kit';
import { Confirm, Sheet, st as sheetSt } from '@/ui/Sheet';
import { C, H, R } from '@/ui/theme';

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

export function byDay(wins: Win[]): [string, Win[]][] {
  const m = new Map<string, Win[]>();
  wins.forEach((w) => m.set(w.win_date, [...(m.get(w.win_date) ?? []), w]));
  return [...m.entries()].sort((a, b) => (a[0] < b[0] ? 1 : -1));
}

// 날짜별 기록 목록 + 눌러서 고치기·지우기. 유리병 화면·병 열기·검색이 같이 씀.
// onChange: 이 목록이 가진 로컬 상태(병 안 기록, 검색 결과)도 갱신하라고 알림
export function WinList({ wins, onChange }: { wins: Win[]; onChange?: (w: Win, deleted: boolean) => void }) {
  const { setWins, reloadJars } = useApp();
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [edit, setEdit] = useState<Win | null>(null);
  const [editText, setEditText] = useState('');
  const [editCat, setEditCat] = useState<Category>('cheer');
  const [confirmDel, setConfirmDel] = useState(false);
  const [err, setErr] = useState('');

  function startEdit(w: Win) {
    setEdit(w); setEditText(w.text); setEditCat(w.category); setErr('');
  }
  async function saveEdit() {
    if (!edit) return;
    try {
      const w = await api.editWin(edit.id, editText.trim(), editCat);
      setWins((ws) => ws.map((x) => (x.id === w.id ? w : x)));
      onChange?.(w, false);
      reloadJars().catch(() => {});
      track('win_edited');
      setEdit(null);
    } catch (e) { setErr(friendlyError(e)); }
  }
  async function del() {
    if (!edit) return;
    const target = edit;
    try {
      await api.deleteWin(target.id);
      setWins((ws) => ws.filter((x) => x.id !== target.id));
      onChange?.(target, true);
      reloadJars().catch(() => {});
      track('win_deleted');
      setConfirmDel(false); setEdit(null);
    } catch (e) { setErr(friendlyError(e)); setConfirmDel(false); }
  }

  return (
    <>
      {byDay(wins).map(([d, ws]) => {
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

      <Sheet visible={!!edit && !confirmDel} onClose={() => setEdit(null)}>
        <Text style={sheetSt.title}>기록 고치기</Text>
        <TextInput style={st.input} value={editText} onChangeText={setEditText} maxLength={100} accessibilityLabel="기록 내용" />
        <View style={st.catRow}>
          {CATEGORY_ORDER.map((c) => (
            <Pressable key={c} onPress={() => setEditCat(c)} style={[st.chip, editCat === c && st.chipOn]} accessibilityState={{ selected: editCat === c }}>
              <View style={[st.dot, { width: 8, height: 8, backgroundColor: CATS[c].color }]} />
              <Text style={{ fontSize: 13, color: editCat === c ? C.accentInk : C.ink, fontWeight: editCat === c ? '700' : '400' }}>{CATS[c].name}</Text>
            </Pressable>
          ))}
        </View>
        {err ? <Text style={{ color: C.danger, fontSize: 13, marginBottom: 8 }}>{err}</Text> : null}
        <View style={sheetSt.col}>
          <Btn title="저장" onPress={saveEdit} disabled={!editText.trim()} />
          <Btn title="지우기" kind="danger" onPress={() => setConfirmDel(true)} />
        </View>
      </Sheet>
      <Confirm
        visible={confirmDel} title="이 기록을 지울까?" body="이미 받은 씨앗은 그대로 있어." confirm="지우기" danger
        onConfirm={del} onCancel={() => setConfirmDel(false)}
      />
    </>
  );
}

export const st = StyleSheet.create({
  dayH: { fontSize: 13, color: C.muted, fontWeight: '700', marginBottom: 8, marginLeft: 4 },
  win: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: C.card, borderRadius: R.card, paddingVertical: 14, paddingHorizontal: 18, marginBottom: 6 },
  dot: { width: 10, height: 10, borderRadius: R.pill },
  winText: { flex: 1, fontSize: 15, color: C.ink },
  tag: { fontSize: 11, color: C.muted, backgroundColor: C.soft, paddingVertical: 4, paddingHorizontal: 10, borderRadius: R.pill, overflow: 'hidden' },
  input: { fontSize: 16, height: H.input, paddingHorizontal: 22, borderRadius: R.pill, backgroundColor: C.card, color: C.ink, marginBottom: 12 },
  catRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 14 },
  chip: { flexDirection: 'row', alignItems: 'center', gap: 6, height: H.chip, paddingHorizontal: 14, borderRadius: R.pill, backgroundColor: C.soft },
  chipOn: { backgroundColor: C.accentBg },
});
