import { Image } from 'expo-image';
import { useEffect, useState } from 'react';
import { Image as RNImage, Platform, Pressable, View } from 'react-native';

import { PET_ASPECT, PET_CLIPS, PET_FEET, PET_POSTER, type ClipKey } from '@/data/petClips';
import type { Category } from '@/lib/categories';

// 단짝(하마). 캐릭터 스레드가 렌더한 움직이는 WebP(design/character/export/v1)를 재생한다.
// - 대기(idle)는 항상 아래에 깔려 반복 재생
// - 동작은 위에 겹쳐 한 번 재생 → duration_ms 타이머로 끝을 판단하고 걷어낸다 (디코더 반복 횟수는 믿지 않음)
//   타이머는 동작 첫 프레임이 화면에 뜬 뒤(onDisplay/onLoad)부터 잰다. 마운트 시점부터 재면 로딩·디코딩에 걸린 만큼
//   동작이 잘리고, 로딩이 duration보다 길면 아예 안 보인 채 걷힌다 (2026-11-10 Expo Go 버그)
// - 클립은 앱 시작 때 디스크 캐시에 미리 받아 둔다 (Expo Go는 require 에셋을 Metro 서버에서 매번 내려받음)
// - 동작 클립은 대기 자세로 시작·끝나서 바꿔 끼워도 튀지 않는다
// - 'sit'(곁에 앉기, 자해 표현 대응): sit_in → sit_loop(SIT_HOLD_MS) → sit_out
// - 'endure'(버틴 하루): 같은 앉기를 짧게 (ENDURE_HOLD_MS)
// - space='garden': 텃밭 25° 클립. 대기 = garden_idle, 어떤 동작이든 garden_cheer(수확 만세). 방(6.5°) 클립과 섞지 않음
// - 탭 반응(tap_fart_hop): 600x800보다 큰 캔버스 클립. 같은 px 배율로 canvas 크기에 그리고 feet를 대기 발 위치에 맞춤,
//   mirror = 좌우 뒤집기(지금 쓰는 곳 없음, 구르기 삭제 2026-11-17). 단짝 몸(대기 포스터 알파 범위)만 탭 영역 — 여백 탭은 아래로 통과
export type PetKind = Category | 'sit' | 'eat_strawberry' | 'drink' | 'cook' | 'tap_fart_hop'; // drink·cook = '잘 먹기' 세부 동작 (eatVariant)
export type PetAction = { kind: PetKind; key: number; mirror?: boolean } | null;
// 대기 포스터에서 단짝 몸이 차지하는 범위 (600x800 기준 x 148~460, y 160~722) → 탭 영역
const BODY = { l: 148 / 600, r: 460 / 600, t: 160 / 800, b: 722 / 800 };

const SIT_HOLD_MS = 9000;
const ENDURE_HOLD_MS = 3000;
const END_GRACE_MS = 150; // 기기에서 재생이 살짝 밀려도 마지막 프레임(대기 자세)까지 보이게
const LOAD_GIVE_UP_MS = 5000; // 이 안에 첫 프레임이 안 뜨면 그 단계는 건너뜀 (단짝이 멈춰 있지 않게)

// 모든 클립을 디스크 캐시에 미리 받아 둔다 (한 번만). 메모리 캐시는 쓰지 않음: 재생 위치가 공유돼 처음부터 안 나올 수 있음
let prefetched = false;
function prefetchClips() {
  if (prefetched || Platform.OS === 'web') return; // 웹은 브라우저 캐시 + loading="eager"로 충분 (resolveAssetSource 없음)
  prefetched = true;
  try {
    const uris = Object.values(PET_CLIPS)
      .map((c) => RNImage.resolveAssetSource(c.source)?.uri)
      .filter((u): u is string => !!u);
    Image.prefetch(uris, 'disk').catch(() => {});
  } catch {
    // 미리 받기는 최적화일 뿐 — 실패해도 재생은 됨
  }
}

function sequence(kind: PetKind, space: 'room' | 'garden'): { clip: ClipKey; ms: number }[] {
  if (space === 'garden') return [{ clip: 'garden_cheer', ms: PET_CLIPS.garden_cheer.durationMs }];
  if (kind === 'sit' || kind === 'endure') {
    return [
      { clip: 'sit_in', ms: PET_CLIPS.sit_in.durationMs },
      { clip: 'sit_loop', ms: kind === 'sit' ? SIT_HOLD_MS : ENDURE_HOLD_MS },
      { clip: 'sit_out', ms: PET_CLIPS.sit_out.durationMs },
    ];
  }
  return [{ clip: kind, ms: PET_CLIPS[kind].durationMs }];
}

export function Pet({ action, size = 200, space = 'room', onDone, onTap }: { action: PetAction; size?: number; space?: 'room' | 'garden'; onDone?: (key: number) => void; onTap?: () => void }) {
  const idle: ClipKey = space === 'garden' ? 'garden_idle' : 'idle';
  const width = size;
  const height = Math.round(size * PET_ASPECT);
  const [prog, setProg] = useState({ key: -1, step: 0 });
  const [shownKey, setShownKey] = useState('');

  const seq = action ? sequence(action.kind, space) : [];
  const step = action && prog.key === action.key ? prog.step : 0;
  const cur = action && step < seq.length ? seq[step] : null;
  const overlayKey = cur && action ? `${action.key}-${step}` : '';
  const overlayVisible = !!overlayKey && shownKey === overlayKey;

  useEffect(prefetchClips, []);

  // 다음 단계로 넘기는 타이머 (setState는 타이머 콜백 안에서만).
  // 첫 프레임이 뜨기 전: 너무 오래 걸릴 때만 건너뜀 / 뜬 뒤: 클립 길이만큼 보여주고 넘김
  const curMs = cur?.ms ?? 0;
  const actionKey = action?.key ?? -1;
  useEffect(() => {
    if (actionKey < 0 || !curMs) return;
    const wait = overlayVisible ? curMs + END_GRACE_MS : LOAD_GIVE_UP_MS;
    const t = setTimeout(() => setProg({ key: actionKey, step: step + 1 }), wait);
    return () => clearTimeout(t);
  }, [actionKey, curMs, step, overlayVisible]);

  // 동작이 다 끝나면 알림 (방 기록 줌 복귀용)
  const finished = !!action && seq.length > 0 && step >= seq.length;
  useEffect(() => {
    if (finished) onDone?.(actionKey);
  }, [finished, actionKey, onDone]);

  const fill = { position: 'absolute' as const, left: 0, top: 0, width, height };
  // 큰 캔버스 클립: 같은 배율(width/600)로 키우고 발 위치를 대기 클립 발에 맞춤
  const clipBox = (k: ClipKey, mirror?: boolean) => {
    const c = PET_CLIPS[k];
    if (!c.canvas || !c.feet) return fill;
    const px = width / 600;
    const fx = mirror ? c.canvas[0] - c.feet[0] : c.feet[0];
    return {
      position: 'absolute' as const,
      left: (PET_FEET[0] - fx) * px, top: (PET_FEET[1] - c.feet[1]) * px,
      width: c.canvas[0] * px, height: c.canvas[1] * px,
      ...(mirror ? { transform: [{ scaleX: -1 }] } : null),
    };
  };

  return (
    <View style={{ width, height }} accessible={!onTap} accessibilityLabel="단짝" pointerEvents={onTap ? 'box-none' : 'auto'}>
      {/* 대기: 동작 첫 프레임이 화면에 뜬 뒤에만 숨긴다 (빈 화면 깜빡임 방지) */}
      <Image
        source={PET_CLIPS[idle].source}
        placeholder={space === 'room' ? PET_POSTER : undefined}
        style={[fill, { opacity: overlayVisible ? 0 : 1 }]}
        contentFit="contain"
        loading="eager" /* 웹: 가로 넘기기 안 화면 밖에서 시작하면 lazy 로딩이 늦게 풀림 (네이티브 영향 없음) */
        autoplay={!overlayVisible}
      />
      {cur && (
        <Image
          key={overlayKey}
          source={PET_CLIPS[cur.clip].source}
          style={clipBox(cur.clip, action?.mirror)} /* 투명 배경이라 로딩 중엔 아래 대기가 비쳐 보임. opacity 0으로 숨기면 웹에서 lazy 로딩이 멈춤 */
          contentFit="contain"
          autoplay
          loading="eager"
          cachePolicy="disk" /* 디스크만: 다시 받지 않되 매번 첫 프레임부터 디코딩 (memory는 재생 위치 공유 위험) */
          onDisplay={() => setShownKey(overlayKey)}
          onLoad={() => setShownKey(overlayKey)}
        />
      )}
      {onTap && (
        <Pressable
          onPress={onTap}
          accessibilityRole="button"
          accessibilityLabel="단짝 쓰다듬기"
          style={{ position: 'absolute', left: width * BODY.l, top: height * BODY.t, width: width * (BODY.r - BODY.l), height: height * (BODY.b - BODY.t) }}
        />
      )}
    </View>
  );
}
