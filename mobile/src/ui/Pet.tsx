import { Image } from 'expo-image';
import { useEffect, useState } from 'react';
import { View } from 'react-native';

import { PET_ASPECT, PET_CLIPS, PET_POSTER, type ClipKey } from '@/data/petClips';
import type { Category } from '@/lib/categories';

// 단짝(하마). 캐릭터 스레드가 렌더한 움직이는 WebP(design/character/export/v1)를 재생한다.
// - 대기(idle)는 항상 아래에 깔려 반복 재생
// - 동작은 위에 겹쳐 한 번 재생 → duration_ms 타이머로 끝을 판단하고 걷어낸다 (디코더 반복 횟수는 믿지 않음)
// - 동작 클립은 대기 자세로 시작·끝나서 바꿔 끼워도 튀지 않는다
// - 'sit'(곁에 앉기, 자해 표현 대응): sit_in → sit_loop(SIT_HOLD_MS) → sit_out
// - 'endure'(버틴 하루): 같은 앉기를 짧게 (ENDURE_HOLD_MS)
// - space='garden': 텃밭 25° 클립. 대기 = garden_idle, 어떤 동작이든 garden_cheer(수확 만세). 방(6.5°) 클립과 섞지 않음
export type PetKind = Category | 'sit' | 'eat_strawberry';
export type PetAction = { kind: PetKind; key: number } | null;

const SIT_HOLD_MS = 9000;
const ENDURE_HOLD_MS = 3000;

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

export function Pet({ action, size = 200, space = 'room' }: { action: PetAction; size?: number; space?: 'room' | 'garden' }) {
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

  // 다음 단계로 넘기는 타이머 (setState는 타이머 콜백 안에서만)
  const curMs = cur?.ms ?? 0;
  const actionKey = action?.key ?? -1;
  useEffect(() => {
    if (actionKey < 0 || !curMs) return;
    const t = setTimeout(() => setProg({ key: actionKey, step: step + 1 }), curMs);
    return () => clearTimeout(t);
  }, [actionKey, curMs, step]);

  const fill = { position: 'absolute' as const, left: 0, top: 0, width, height };

  return (
    <View style={{ width, height }} accessible accessibilityLabel="단짝">
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
          style={fill} /* 투명 배경이라 로딩 중엔 아래 대기가 비쳐 보임. opacity 0으로 숨기면 웹에서 lazy 로딩이 멈춤 */
          contentFit="contain"
          autoplay
          loading="eager"
          cachePolicy="none"
          onDisplay={() => setShownKey(overlayKey)}
          onLoad={() => setShownKey(overlayKey)}
        />
      )}
    </View>
  );
}
