import { useRef, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { api, FIRST_CROP, friendlyError, plotStage, type Crop, type Plot } from '@/lib/api';
import { track } from '@/lib/analytics';
import { useApp } from '@/state/app';
import { Btn } from '@/ui/kit';
import { Pet, type PetAction } from '@/ui/Pet';
import { Sheet, st as sheetSt } from '@/ui/Sheet';
import { useSpaceSize } from '@/ui/layout';
import { C, R } from '@/ui/theme';

// 텃밭 (docs/FEATURES.md 7장, docs/WORLD.md 1·2장)
// - 3칸 처음부터. 기록한 날 3일마다 한 단계(작심삼일), 9일에 수확. 쉬어도 리셋 없음
// - 첫 작물은 고구마 고정·무료, 다음 날 기록하면 수확
// - 3일 이상 안 들어오면 "졸고 있음" → 탭 한 번에 깸 (진행 영향 없음)
// - 입력창 없음. 임시 그림(이모지) → 공간 스레드 렌더가 나오면 교체. 단짝은 25° 클립 전까지 방 클립 임시 사용
const STAGE_ART = ['', '🌱', '🌿'] as const;

function PlotTile({ plot, crop, dozing, onPress }: { plot?: Plot; crop?: Crop; dozing: boolean; onPress: () => void }) {
  if (!plot || !crop) {
    return (
      <Pressable style={st.plot} onPress={onPress} accessibilityRole="button" accessibilityLabel="빈 칸, 심기">
        <View style={st.soil} />
        <Text style={st.plantLabel}>＋ 심기</Text>
      </Pressable>
    );
  }
  const { stage, dots } = plotStage(plot);
  const ready = stage === 3;
  const art = ready ? crop.emoji : stage === 0 ? '' : STAGE_ART[stage];
  const nine = plot.required_days > 1;
  return (
    <Pressable style={st.plot} onPress={onPress} accessibilityRole="button"
      accessibilityLabel={`${crop.name}, ${ready ? '수확할 수 있어요' : `기록한 날 ${plot.days}일`}`}>
      <View style={st.soil}>{stage === 0 && <View style={st.mound} />}</View>
      {art ? (
        <Text style={[st.crop, { fontSize: ready ? 40 : 30 + dots * 2 }, dozing && st.dozing]}>{art}</Text>
      ) : null}
      {ready && !dozing && <Text style={st.sparkle}>✨</Text>}
      {dozing && <Text style={st.zzz}>💤</Text>}
      <Text style={st.plotName}>{crop.name}</Text>
      <Text style={st.dots}>
        {ready ? '수확하기' : nine ? `${'●'.repeat(dots)}${'○'.repeat(3 - dots)} · ${['심음', '싹', '자람'][stage]}` : '내일 기록하면 수확'}
      </Text>
    </Pressable>
  );
}

export function GardenPage() {
  const { crops, plots, profile, balance, setBalance, dozing, wakeGarden, reloadGarden, refresh } = useApp();
  const [picking, setPicking] = useState<number | null>(null);
  const [action, setAction] = useState<PetAction>(null);
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const seq = useRef(0);
  const { spaceH, gardenPetW } = useSpaceSize();

  const firstFree = !profile?.first_crop_used;
  const bySlot = Object.fromEntries(plots.map((p) => [p.slot, p]));
  const cropOf = (id?: string) => crops.find((c) => c.id === id);

  async function onPlot(slot: number) {
    setMsg('');
    if (dozing) {
      wakeGarden();
      setMsg('다시 와줘서 좋아!');
      track('garden_woke');
      return;
    }
    const p = bySlot[slot];
    if (!p) { setPicking(slot); return; }
    if (plotStage(p).stage !== 3) {
      setMsg(p.required_days > 1 ? `기록한 날 ${p.days}일째. 작심삼일이면 한 단계씩 자라!` : '내일 오늘 해낸 걸 적으면 수확할 수 있어');
      return;
    }
    setBusy(true);
    try {
      const r = await api.harvest(slot);
      const c = cropOf(r.crop_id);
      setAction({ kind: 'cheer', key: ++seq.current });
      setMsg(r.first_unlock ? `${c?.name} 수확! 방 창턱에 ${c?.deco_name}이 생겼어` : `${c?.name} 수확! 방에서 바구니를 열어봐`);
      track('harvested', { crop: r.crop_id, first: r.first_unlock });
      await reloadGarden();
    } catch (e) {
      setMsg(friendlyError(e));
    } finally {
      setBusy(false);
    }
  }

  async function plant(cropId: string) {
    if (picking == null) return;
    setBusy(true);
    try {
      const bal = await api.plant(picking, cropId);
      setBalance(bal);
      setPicking(null);
      setMsg(firstFree ? '고구마를 심었어! 내일 기록하면 수확할 수 있어' : '심었어! 기록한 날 3일마다 한 단계씩 자라');
      track('planted', { crop: cropId, first: firstFree });
      await Promise.all([reloadGarden(), firstFree ? refresh() : Promise.resolve()]);
    } catch (e) {
      setMsg(friendlyError(e));
    } finally {
      setBusy(false);
    }
  }

  const choices = firstFree ? crops.filter((c) => c.id === FIRST_CROP) : crops;

  return (
    <ScrollView style={st.wrap} contentContainerStyle={{ paddingBottom: 32 }}>
      <View style={[st.garden, { height: spaceH }]}>
        <View style={st.hedge} />
        <View style={st.fence} />
        <Text style={st.sign}>🪧</Text>
        <Text style={st.can}>🪣</Text>
        <View style={st.plots}>
          {[1, 2, 3].map((slot) => (
            <PlotTile key={slot} plot={bySlot[slot]} crop={cropOf(bySlot[slot]?.crop_id)} dozing={dozing && !!bySlot[slot]} onPress={() => onPlot(slot)} />
          ))}
        </View>
        <View style={st.pet}><Pet action={action} size={gardenPetW} /></View>
      </View>
      {msg ? <Text style={st.msg}>{msg}</Text> : null}
      <Text style={st.help}>
        {dozing && plots.length ? '식물들이 졸고 있어. 톡 건드려서 깨워줘.' : '작심삼일이면 충분해. 기록한 날 3일마다 한 단계씩, 9일이면 수확. 쉬었다 와도 처음부터가 아니야.'}
      </Text>

      <Sheet visible={picking != null} onClose={() => setPicking(null)}>
        <Text style={sheetSt.title}>{firstFree ? '첫 작물은 고구마!' : '뭘 심을까?'}</Text>
        <Text style={sheetSt.body}>
          {firstFree ? '첫 고구마는 선물이야. 내일 오늘 해낸 걸 적으면 바로 수확할 수 있어.' : `심기 씨앗 3개 · 기록한 날 9일이면 수확 (지금 씨앗 ${balance}개)`}
        </Text>
        {choices.map((c) => {
          const cost = firstFree ? 0 : c.price;
          return (
            <View key={c.id} style={st.choice}>
              <Text style={{ fontSize: 28 }}>{c.emoji}</Text>
              <View style={{ flex: 1 }}>
                <Text style={st.choiceName}>{c.name}</Text>
                <Text style={st.choiceSub}>{c.kind === 'edible' ? '수확하면 방에서 먹이기' : '수확하면 방에서 선물하기'} · 처음 수확하면 {c.deco_name}</Text>
              </View>
              <Btn title={cost ? `씨앗 ${cost}` : '무료'} onPress={() => plant(c.id)} disabled={busy || balance < cost} />
            </View>
          );
        })}
      </Sheet>
    </ScrollView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg },
  garden: { marginHorizontal: 16, borderRadius: 28, overflow: 'hidden', backgroundColor: '#cfe8c4' },
  hedge: { position: 'absolute', left: 0, right: 0, top: 0, height: '30%', backgroundColor: '#9cc98f', borderBottomLeftRadius: 60, borderBottomRightRadius: 60 },
  fence: { position: 'absolute', left: 0, right: 0, top: '27%', height: 10, backgroundColor: '#fffaf2', opacity: 0.9 },
  sign: { position: 'absolute', left: 14, top: '30%', fontSize: 28 },
  can: { position: 'absolute', right: 14, top: '32%', fontSize: 24 },
  plots: { position: 'absolute', left: 12, right: 12, top: '34%', flexDirection: 'row', justifyContent: 'space-between' },
  plot: { width: '31%', height: 112, alignItems: 'center', justifyContent: 'flex-end', paddingBottom: 6 },
  soil: { position: 'absolute', bottom: 34, width: '92%', height: 34, borderRadius: 16, backgroundColor: '#9b7653', alignItems: 'center', justifyContent: 'flex-start' },
  mound: { width: 34, height: 14, borderTopLeftRadius: 17, borderTopRightRadius: 17, backgroundColor: '#7d5c3e', marginTop: -6 },
  crop: { position: 'absolute', bottom: 52 },
  dozing: { transform: [{ rotate: '-22deg' }], opacity: 0.8 },
  sparkle: { position: 'absolute', bottom: 88, right: 8, fontSize: 16 },
  zzz: { position: 'absolute', bottom: 86, right: 6, fontSize: 16 },
  plantLabel: { position: 'absolute', bottom: 41, fontSize: 13, fontWeight: '700', color: '#fff' },
  plotName: { fontSize: 12, fontWeight: '700', color: C.ink },
  dots: { fontSize: 11, color: C.muted, marginTop: 1 },
  pet: { position: 'absolute', alignSelf: 'center', bottom: -14 },
  msg: { marginHorizontal: 16, marginTop: 12, backgroundColor: '#fff', borderRadius: 14, padding: 12, fontSize: 14, color: C.ink, borderWidth: 1, borderColor: C.line, overflow: 'hidden' },
  help: { fontSize: 12, color: C.muted, marginHorizontal: 20, marginTop: 10, lineHeight: 18 },
  choice: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 12, backgroundColor: '#fff', borderRadius: R.input, padding: 10 },
  choiceName: { fontSize: 15, fontWeight: '700', color: C.ink },
  choiceSub: { fontSize: 12, color: C.muted, marginTop: 2 },
});
