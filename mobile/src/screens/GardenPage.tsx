import { useRef, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { api, FIRST_CROP, friendlyError, plotStage, type Crop, type Plot } from '@/lib/api';
import { track } from '@/lib/analytics';
import { useApp } from '@/state/app';
import { Icon } from '@/ui/Icon';
import { Btn, Price } from '@/ui/kit';
import { Pet, type PetAction } from '@/ui/Pet';
import { Sheet, st as sheetSt } from '@/ui/Sheet';
import { useSpaceSize } from '@/ui/layout';
import { PANEL_OVERLAP, SpaceChips, SpaceSwitch, useSceneLayout, type SpaceNav } from '@/ui/SpaceChrome';
import { CANVAS, GARDEN, ICONS } from '@/data/world';
import { Image } from 'expo-image';
import { ART, C, R, TAB_SPACE } from '@/ui/theme';

// 텃밭 (docs/FEATURES.md 7장, docs/WORLD.md 1·2장)
// - 3칸 처음부터. 기록한 날 3일마다 한 단계(작심삼일), 9일에 수확. 쉬어도 리셋 없음
// - 첫 작물은 고구마 고정·무료, 다음 날 기록하면 수확
// - 3일 이상 안 들어오면 "졸고 있음" → 탭 한 번에 깸 (진행 영향 없음)
// - 입력창 없음. 그림은 공간 스레드 export(design/world/export/v1): 배경 → 단짝(25° garden_idle/cheer) → 작물 3칸 → UI(진행 점·Zzz·반짝임)
// - 사이 날에는 진행 점 + 작물 그림 +5%씩 커지기 (WORLD 1장)

function Overlay({ plot, crop, dozing, s, i }: { plot?: Plot; crop?: Crop; dozing: boolean; s: number; i: number }) {
  const P = GARDEN.plots[i];
  const pill = (text: string, strong = false, plus = false) => (
    <View pointerEvents="none" style={[st.pill, strong && st.pillStrong, { left: P.cx * s - 60, top: (P.tap.y + P.tap.h) * s - 30 }]}>
      {plus && <Icon name="plus" size={13} color={C.white} stroke={2.4} />}
      <Text style={[st.pillText, strong && { color: C.white }]} numberOfLines={1}>{text}</Text>
    </View>
  );
  if (!plot || !crop) return pill('심기', true, true);
  const { stage, dots } = plotStage(plot);
  const ready = stage === 3;
  const nine = plot.required_days > 1;
  const mark = (name: 'zzz' | 'sparkle') => (
    <View pointerEvents="none" style={[st.mark, { left: P.cx * s + 20 * s, top: (P.cy - 250) * s }]}>
      <Icon name={name} size={18} color={name === 'sparkle' ? ART.sparkle : C.muted} stroke={2} />
    </View>
  );
  return (
    <>
      {dozing ? mark('zzz') : ready ? mark('sparkle') : null}
      {pill(ready ? `${crop.name} 수확하기` : nine ? `${crop.name} ${'●'.repeat(dots)}${'○'.repeat(3 - dots)}` : `${crop.name} · 내일 수확`, ready)}
    </>
  );
}

function cropImage(plot: Plot | undefined, dozing: boolean) {
  if (!plot) return null;
  const { stage, dots } = plotStage(plot);
  if (stage === 0) return { src: GARDEN.crops.mound, scale: 1 };
  const key = `${plot.crop_id}_${stage}${dozing ? '_doze' : ''}`;
  return { src: GARDEN.crops[key], scale: stage === 3 ? 1 : 1 + 0.05 * dots };
}

export function GardenPage({ nav }: { nav?: SpaceNav } = {}) {
  const { crops, plots, profile, balance, setBalance, dozing, wakeGarden, reloadGarden, refresh } = useApp();
  const [picking, setPicking] = useState<number | null>(null);
  const [action, setAction] = useState<PetAction>(null);
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const seq = useRef(0);
  // 그림: 화면 위쪽 가로 꽉(약 420). 정사각 캔버스를 넉넉한 쪽에 맞추고 가운데 기준으로 잘라 보여준다
  const { fullWidth } = useSpaceSize();
  const { canvasH, sceneH } = useSceneLayout();
  const sc = Math.max(fullWidth, canvasH) / CANVAS;
  const ox = (CANVAS * sc - fullWidth) / 2, oy = (CANVAS * sc - canvasH) / 2; // 판이 덮는 부분 위(canvasH) 안에서 가운데 맞춤

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
      setMsg(`${c?.name} 수확! 방 창턱에 놓아 뒀어 (${c?.deco_name})`);
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
    <ScrollView style={st.wrap} contentContainerStyle={{ paddingBottom: TAB_SPACE + 12 }}>
      <View style={[st.garden, { width: fullWidth, height: sceneH }]}>
      <View style={{ position: 'absolute', left: -ox, top: -oy, width: CANVAS * sc, height: CANVAS * sc }}>
        <Image source={GARDEN.background} style={StyleSheet.absoluteFill} contentFit="cover" loading="eager" />
        <View style={{ position: 'absolute', left: GARDEN.pet.x * sc, top: GARDEN.pet.y * sc }} pointerEvents="none">
          <Pet action={action} size={GARDEN.pet.w * sc} space="garden" />
        </View>
        {GARDEN.plots.map((P, i) => {
          const img = cropImage(bySlot[i + 1], dozing);
          if (!img?.src) return null;
          const size = GARDEN.cropSize * sc;
          return (
            <Image key={i} source={img.src} contentFit="contain" loading="eager" pointerEvents="none"
              style={{ position: 'absolute', left: P.cropX * sc, top: P.cropY * sc, width: size, height: size, transform: [{ scale: img.scale }] }} />
          );
        })}
        {GARDEN.plots.map((P, i) => {
          const plot = bySlot[i + 1];
          const crop = cropOf(plot?.crop_id);
          return (
            <Pressable key={`t${i}`} onPress={() => onPlot(i + 1)} accessibilityRole="button"
              accessibilityLabel={!plot || !crop ? '빈 칸, 심기' : `${crop.name}, ${plotStage(plot).stage === 3 ? '수확할 수 있어요' : `기록한 날 ${plot.days}일`}`}
              style={{ position: 'absolute', left: P.tap.x * sc, top: P.tap.y * sc, width: P.tap.w * sc, height: P.tap.h * sc }} />
          );
        })}
        {GARDEN.plots.map((_, i) => (
          <Overlay key={`o${i}`} i={i} s={sc} plot={bySlot[i + 1]} crop={cropOf(bySlot[i + 1]?.crop_id)} dozing={dozing && !!bySlot[i + 1]} />
        ))}
      </View>
      <SpaceChips space="garden" />
      </View>
      <View style={st.panel}>
        {nav && <SpaceSwitch nav={nav} />}
        <Text style={st.title}>{profile?.pet_name ?? '단짝'}의 텃밭</Text>
        <Text style={st.help}>
          {dozing && plots.length ? '식물들이 졸고 있어. 톡 건드려서 깨워줘.' : '작심삼일이면 충분해. 기록한 날 3일마다 한 단계씩, 9일이면 수확. 쉬었다 와도 처음부터가 아니야.'}
        </Text>
        {msg ? <Text style={st.msg}>{msg}</Text> : null}
      </View>

      <Sheet visible={picking != null} onClose={() => setPicking(null)}>
        <Text style={sheetSt.title}>{firstFree ? '첫 작물은 고구마!' : '뭘 심을까?'}</Text>
        <Text style={sheetSt.body}>
          {firstFree ? '첫 고구마는 선물이야. 내일 오늘 해낸 걸 적으면 바로 수확할 수 있어.' : `심기 씨앗 3개 · 기록한 날 9일이면 수확 (지금 씨앗 ${balance}개)`}
        </Text>
        {choices.map((c) => {
          const cost = firstFree ? 0 : c.price;
          return (
            <View key={c.id} style={st.choice}>
              <Image source={ICONS[`packet_${c.id}`]} style={{ width: 44, height: 44 }} contentFit="contain" />
              <View style={{ flex: 1 }}>
                <Text style={st.choiceName}>{c.name}</Text>
                <Text style={st.choiceSub}>{c.kind === 'edible' ? '수확하면 방에서 먹이기' : '수확하면 방에서 선물하기'} · 수확하면 창턱에 {c.deco_name}</Text>
              </View>
              {cost ? (
                <Pressable onPress={() => plant(c.id)} disabled={busy || balance < cost} accessibilityRole="button" accessibilityLabel={`씨앗 ${cost}개로 심기`}
                  style={[st.buy, (busy || balance < cost) && { opacity: 0.4 }]}>
                  <Price n={cost} color={C.white} />
                </Pressable>
              ) : <Btn title="무료" onPress={() => plant(c.id)} disabled={busy} />}
            </View>
          );
        })}
      </Sheet>
    </ScrollView>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg },
  garden: { overflow: 'hidden', backgroundColor: ART.gardenFill },
  panel: { marginTop: -PANEL_OVERLAP, backgroundColor: C.bg, borderTopLeftRadius: R.sheet, borderTopRightRadius: R.sheet, paddingHorizontal: 20, paddingTop: 18 },
  title: { fontSize: 21, fontWeight: '800', color: C.ink, marginTop: 20, marginBottom: 6 },
  pill: { position: 'absolute', width: 120, height: 26, flexDirection: 'row', gap: 3, alignItems: 'center', justifyContent: 'center', backgroundColor: C.chip, borderRadius: R.pill },
  pillStrong: { backgroundColor: C.accent },
  pillText: { fontSize: 12, fontWeight: '700', color: C.ink },
  mark: { position: 'absolute', width: 30, height: 30, borderRadius: R.pill, backgroundColor: C.chip, alignItems: 'center', justifyContent: 'center' },
  msg: { marginTop: 12, backgroundColor: C.card, borderRadius: R.card, paddingVertical: 14, paddingHorizontal: 18, fontSize: 14, color: C.ink, overflow: 'hidden' },
  help: { fontSize: 14, color: C.muted, lineHeight: 21 },
  choice: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 10, backgroundColor: C.card, borderRadius: R.card, padding: 10, paddingLeft: 12 },
  choiceName: { fontSize: 15, fontWeight: '700', color: C.ink },
  choiceSub: { fontSize: 12, color: C.muted, marginTop: 2 },
  buy: { height: 44, minWidth: 64, paddingHorizontal: 16, borderRadius: R.pill, backgroundColor: C.accent, alignItems: 'center', justifyContent: 'center' },
});
