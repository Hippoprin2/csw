import { Image } from 'expo-image';
import { createContext, use, useCallback, useEffect, useMemo, useRef, useState, type PropsWithChildren } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { PET_ASPECT, PET_POSTER } from '@/data/petClips';
import { api, friendlyError, type Win } from '@/lib/api';
import { track } from '@/lib/analytics';
import { CATEGORY_ORDER, CATS, eatVariant, type Category } from '@/lib/categories';
import { formatDay, formatTime } from '@/lib/dates';
import { useReduceMotion } from '@/lib/useReduceMotion';
import { useApp } from '@/state/app';
import { Icon } from '@/ui/Icon';
import { Btn } from '@/ui/kit';
import { Pet, type PetAction } from '@/ui/Pet';
import { Confirm, Sheet, st as sheetSt } from '@/ui/Sheet';
import { C, H, R } from '@/ui/theme';

// 기록 '크게 보기' 시트 (C9 M2·N1·N2·M3). 어디서든 기록·구슬을 누르면 이 시트 하나가 뜬다.
// 읽기 먼저: 날짜·시각 / 원문 / 그때 단짝 동작(자동 재생) / + 한 줄 더 남기기 / 분류 · ☆ 다시 보고 싶은 기록
// 고치기·지우기는 ··· 안. 원문은 그대로, 덧붙이기만 (메모는 따로 저장, 자해 감지 안 돌림 — 대표 결정)
// onChange: 이 기록을 들고 있는 화면의 로컬 목록(병 열기·목록·하루 한 장)도 고치라고 알림. 전역 wins는 여기서 고친다
type OnChange = (w: Win, deleted: boolean) => void;
type Ctx = { openWin: (w: Win, onChange?: OnChange) => void };
const WinCtx = createContext<Ctx | null>(null);

export function useWinSheet() {
  const v = use(WinCtx);
  if (!v) throw new Error('useWinSheet outside WinSheetProvider');
  return v;
}

const PET_W = 120;

export function WinSheetProvider({ children }: PropsWithChildren) {
  const { setWins, reloadJars } = useApp();
  const reduce = useReduceMotion();
  const [win, setWin] = useState<Win | null>(null);
  const onChangeRef = useRef<OnChange | undefined>(undefined);
  const [mode, setMode] = useState<'view' | 'menu' | 'edit'>('view');
  const [note, setNote] = useState('');
  const [editText, setEditText] = useState('');
  const [editCat, setEditCat] = useState<Category>('cheer');
  const [confirmDel, setConfirmDel] = useState(false);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const [pet, setPet] = useState<PetAction>(null);
  const petKey = useRef(0);

  const playPet = useCallback((w: Win) => { petKey.current += 1; setPet({ kind: eatVariant(w.category, w.text) ?? w.category, key: petKey.current }); }, []);

  const openWin = useCallback((w: Win, onChange?: OnChange) => {
    onChangeRef.current = onChange;
    setWin(w); setMode('view'); setNote(w.note ?? ''); setErr(''); setConfirmDel(false);
    setPet(null);
    track('win_viewed');
  }, []);
  // 시트가 다 올라온 뒤 동작 재생 (올라오는 중에 시작하면 앞부분이 안 보임)
  const winId = win?.id;
  useEffect(() => {
    if (!winId || reduce || !win) return;
    const t = setTimeout(() => playPet(win), 350);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [winId, reduce]);

  function applied(w: Win, deleted = false) {
    setWins((ws) => (deleted ? ws.filter((x) => x.id !== w.id) : ws.map((x) => (x.id === w.id ? w : x))));
    onChangeRef.current?.(w, deleted);
  }
  const close = () => { setWin(null); setPet(null); };

  async function saveNote() {
    if (!win || busy) return;
    const n = note.trim();
    if (n === (win.note ?? '')) return;
    setBusy(true); setErr('');
    try {
      const w = await api.setNote(win.id, n);
      setWin(w); setNote(w.note ?? ''); applied(w);
      track('win_note_saved', { cleared: !w.note });
    } catch (e) { setErr(friendlyError(e)); }
    setBusy(false);
  }
  async function toggleStar() {
    if (!win || busy) return;
    const on = !win.starred;
    setWin({ ...win, starred: on }); // 바로 반영, 실패하면 되돌림
    try {
      const w = await api.setStar(win.id, on);
      setWin((cur) => (cur && cur.id === w.id ? { ...cur, starred: w.starred } : cur)); applied(w);
      track('win_starred', { on });
    } catch (e) { setWin((cur) => (cur ? { ...cur, starred: !on } : cur)); setErr(friendlyError(e)); }
  }
  async function saveEdit() {
    if (!win) return;
    setBusy(true); setErr('');
    try {
      const w = await api.editWin(win.id, editText.trim(), editCat);
      setWin(w); applied(w); setMode('view');
      reloadJars().catch(() => {});
      track('win_edited');
    } catch (e) { setErr(friendlyError(e)); }
    setBusy(false);
  }
  async function del() {
    if (!win) return;
    const target = win;
    try {
      await api.deleteWin(target.id);
      applied(target, true);
      reloadJars().catch(() => {});
      track('win_deleted');
      setConfirmDel(false); close();
    } catch (e) { setErr(friendlyError(e)); setConfirmDel(false); }
  }

  const value = useMemo(() => ({ openWin }), [openWin]);
  const noteDirty = !!win && note.trim() !== (win.note ?? '');

  return (
    <WinCtx value={value}>
      {children}
      <Sheet visible={!!win && !confirmDel} onClose={close}>
        {win && mode !== 'edit' && (
          <>
            <View style={st.top}>
              <Text style={st.when}>{formatDay(win.win_date)} {formatTime(win.created_at)}</Text>
              <Pressable onPress={() => setMode(mode === 'menu' ? 'view' : 'menu')} hitSlop={12} accessibilityRole="button" accessibilityLabel="더 보기: 고치기, 지우기">
                <Icon name="more" size={22} color={C.muted} />
              </Pressable>
            </View>
            {mode === 'menu' && (
              <View style={st.menu}>
                <Pressable style={st.menuRow} onPress={() => { setEditText(win.text); setEditCat(win.category); setErr(''); setMode('edit'); }} accessibilityRole="button">
                  <Text style={st.menuText}>고치기</Text>
                </Pressable>
                <View style={st.menuLine} />
                <Pressable style={st.menuRow} onPress={() => { setMode('view'); setConfirmDel(true); }} accessibilityRole="button">
                  <Text style={[st.menuText, { color: C.danger }]}>지우기</Text>
                </Pressable>
              </View>
            )}
            <Text style={st.text} selectable>{win.text}</Text>

            {/* N1: 그때 단짝 동작. 동작 줄이기 켜면 멈춘 그림. 탭하면 다시 재생 */}
            <Pressable
              style={st.petBox} onPress={() => { if (!reduce) playPet(win); }} disabled={reduce}
              accessibilityRole={reduce ? undefined : 'button'} accessibilityLabel={reduce ? '단짝' : '그때 단짝 동작 다시 보기'}
            >
              {reduce
                ? <Image source={PET_POSTER} style={{ width: PET_W, height: PET_W * PET_ASPECT }} contentFit="contain" />
                : <Pet action={pet} size={PET_W} />}
              {!reduce && <Text style={st.petCap}>눌러서 그때 동작 다시 보기</Text>}
            </Pressable>

            {/* N2: 덧붙이는 한 줄 (원문은 그대로) */}
            <View style={st.noteRow}>
              <TextInput
                style={st.note} value={note} onChangeText={(v) => { setNote(v); setErr(''); }} onSubmitEditing={saveNote}
                placeholder="+ 한 줄 더 남기기" placeholderTextColor={C.placeholder} maxLength={200} returnKeyType="done"
                accessibilityLabel="이 기록에 한 줄 더 남기기"
              />
              {noteDirty && (
                <Pressable onPress={saveNote} disabled={busy} style={st.noteSave} accessibilityRole="button">
                  <Text style={st.noteSaveText}>{note.trim() ? '남기기' : '지우기'}</Text>
                </Pressable>
              )}
            </View>

            <View style={st.chips}>
              <View style={st.chip}>
                <View style={[st.dot, { backgroundColor: CATS[win.category].color }]} />
                <Text style={st.chipText}>{CATS[win.category].name}</Text>
              </View>
              <Pressable onPress={toggleStar} style={[st.chip, win.starred && st.chipOn]} accessibilityRole="button" accessibilityState={{ selected: win.starred }}>
                <Icon name="star" size={15} color={win.starred ? C.accentInk : C.ink} fill={win.starred ? C.accentInk : undefined} />
                <Text style={[st.chipText, win.starred && st.chipTextOn]}>다시 보고 싶은 기록</Text>
              </Pressable>
            </View>
            {err ? <Text style={st.err}>{err}</Text> : null}
            <Btn title="닫기" kind="ghost" onPress={close} />
          </>
        )}
        {win && mode === 'edit' && (
          <>
            <Text style={sheetSt.title}>기록 고치기</Text>
            <TextInput style={st.input} value={editText} onChangeText={setEditText} maxLength={100} accessibilityLabel="기록 내용" />
            <View style={st.catRow}>
              {CATEGORY_ORDER.map((c) => (
                <Pressable key={c} onPress={() => setEditCat(c)} style={[st.chip, editCat === c && st.chipOn]} accessibilityState={{ selected: editCat === c }}>
                  <View style={[st.dot, { backgroundColor: CATS[c].color }]} />
                  <Text style={[st.chipText, editCat === c && st.chipTextOn]}>{CATS[c].name}</Text>
                </Pressable>
              ))}
            </View>
            {err ? <Text style={st.err}>{err}</Text> : null}
            <View style={sheetSt.col}>
              <Btn title="저장" onPress={saveEdit} disabled={!editText.trim() || busy} />
              <Btn title="취소" kind="ghost" onPress={() => { setMode('view'); setErr(''); }} />
            </View>
          </>
        )}
      </Sheet>
      <Confirm
        visible={confirmDel} title="이 기록을 지울까?" body="이미 받은 씨앗은 그대로 있어." confirm="지우기" danger
        onConfirm={del} onCancel={() => setConfirmDel(false)}
      />
    </WinCtx>
  );
}

const st = StyleSheet.create({
  top: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 },
  when: { fontSize: 13, color: C.muted },
  menu: { position: 'absolute', right: 22, top: 50, zIndex: 10, backgroundColor: C.bg, borderRadius: R.card, paddingVertical: 4, minWidth: 140, shadowColor: C.shadow, shadowOpacity: 0.16, shadowRadius: 14, shadowOffset: { width: 0, height: 4 }, elevation: 6 },
  menuRow: { paddingVertical: 13, paddingHorizontal: 18 },
  menuText: { fontSize: 15, color: C.ink, fontWeight: '600' },
  menuLine: { height: 1, backgroundColor: C.divider, marginHorizontal: 12 },
  text: { fontSize: 22, fontWeight: '800', color: C.ink, lineHeight: 31, marginBottom: 14 },
  petBox: { alignItems: 'center', backgroundColor: C.card, borderRadius: R.card, paddingTop: 8, paddingBottom: 10, marginBottom: 12 },
  petCap: { fontSize: 12, color: C.muted, marginTop: 2 },
  noteRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  note: { flex: 1, minWidth: 0, fontSize: 15, minHeight: 48, paddingHorizontal: 20, borderRadius: R.pill, backgroundColor: C.card, color: C.ink },
  noteSave: { height: 48, justifyContent: 'center', paddingHorizontal: 16, borderRadius: R.pill, backgroundColor: C.accent },
  noteSaveText: { fontSize: 14, fontWeight: '700', color: C.white },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 10 },
  chip: { flexDirection: 'row', alignItems: 'center', gap: 6, height: H.chip, paddingHorizontal: 14, borderRadius: R.pill, backgroundColor: C.soft },
  chipOn: { backgroundColor: C.accentBg },
  chipText: { fontSize: 13, color: C.ink },
  chipTextOn: { color: C.accentInk, fontWeight: '700' },
  dot: { width: 8, height: 8, borderRadius: R.pill },
  err: { color: C.danger, fontSize: 13, marginBottom: 8 },
  input: { fontSize: 16, height: H.input, paddingHorizontal: 22, borderRadius: R.pill, backgroundColor: C.card, color: C.ink, marginBottom: 12 },
  catRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 14 },
});
