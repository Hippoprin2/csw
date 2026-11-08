import { useEffect } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Animated, {
  Easing, cancelAnimation, useAnimatedStyle, useSharedValue, withDelay, withRepeat, withSequence, withTiming,
} from 'react-native-reanimated';
import Svg, { Circle, Ellipse, Path, Rect } from 'react-native-svg';

import { CATS, type Category } from '@/lib/categories';
import { C } from './theme';

// 임시 꼬마하마 (프로토타입 SVG 이식). 최종 캐릭터 에셋이 나오면 이 컴포넌트만 교체한다.
// 동작 = 공통 7종 + 'sit'(곁에 앉기: 자해 표현 대응용 조용한 동작)
export type PetAction = { kind: Category | 'sit'; key: number } | null;

const PROP_POS: Record<Category, object> = {
  tidy: { left: '58%', bottom: 0 },
  move: { right: -6, top: 20 },
  study: { left: '35%', bottom: 40 },
  eat: { left: '38%', top: '46%' },
  care: { right: 0, top: 0 },
  people: { right: -10, top: 30 },
  cheer: { left: -10, top: 0 },
};

export function Pet({ action, size = 200 }: { action: PetAction; size?: number }) {
  const hy = useSharedValue(0);
  const hx = useSharedValue(0);
  const hr = useSharedValue(0);
  const hry = useSharedValue(0);
  const hsy = useSharedValue(1);
  const armL = useSharedValue(0);
  const armR = useSharedValue(0);
  const headR = useSharedValue(0);
  const snout = useSharedValue(1);
  const eyes = useSharedValue(1);
  const idle = useSharedValue(0);
  const propO = useSharedValue(0);
  const propS = useSharedValue(0.4);

  // 기본: 숨쉬기 + 눈 깜빡임
  useEffect(() => {
    idle.value = withRepeat(withSequence(withTiming(-3, { duration: 1500 }), withTiming(0, { duration: 1500 })), -1);
    eyes.value = withRepeat(withSequence(withTiming(1, { duration: 4200 }), withTiming(0.1, { duration: 110 }), withTiming(1, { duration: 110 })), -1);
  }, [idle, eyes]);

  useEffect(() => {
    if (!action) return;
    const all = [hy, hx, hr, hry, hsy, armL, armR, headR, snout];
    all.forEach((v) => cancelAnimation(v));
    hy.value = 0; hx.value = 0; hr.value = 0; hry.value = 0; hsy.value = 1;
    armL.value = 0; armR.value = 0; headR.value = 0; snout.value = 1;
    const ease = Easing.inOut(Easing.quad);
    const rep = (to: number, ms: number, n: number, rest = 0) =>
      withRepeat(withSequence(withTiming(to, { duration: ms / 2, easing: ease }), withTiming(rest, { duration: ms / 2, easing: ease })), n);
    const jump = (n: number) =>
      withRepeat(withSequence(
        withTiming(-38, { duration: 300, easing: Easing.out(Easing.quad) }),
        withTiming(0, { duration: 300, easing: Easing.in(Easing.quad) }),
      ), n);

    switch (action.kind) {
      case 'tidy':
        hr.value = withRepeat(withSequence(withTiming(-7, { duration: 125 }), withTiming(7, { duration: 250 }), withTiming(0, { duration: 125 })), 5);
        armR.value = rep(40, 500, 5);
        break;
      case 'move':
        hy.value = jump(4);
        break;
      case 'study':
        headR.value = rep(8, 700, 4);
        break;
      case 'eat':
        snout.value = rep(0.82, 300, 8, 1);
        break;
      case 'care':
        hry.value = withRepeat(withSequence(withTiming(360, { duration: 1200, easing: ease }), withTiming(0, { duration: 0 })), 2);
        armL.value = rep(70, 1200, 2);
        armR.value = rep(-70, 1200, 2);
        break;
      case 'people':
        armR.value = rep(-120, 400, 7);
        break;
      case 'cheer':
        armL.value = rep(130, 600, 4);
        armR.value = rep(-130, 600, 4);
        hy.value = jump(4);
        break;
      case 'sit':
        // 곁에 앉기: 앞으로 살짝 다가와 낮게 앉고, 천천히 숨쉰다. 폭죽·점프 없음.
        hsy.value = withSequence(withTiming(0.92, { duration: 900, easing: ease }),
          withRepeat(withSequence(withTiming(0.95, { duration: 1600 }), withTiming(0.92, { duration: 1600 })), 3),
          withTiming(1, { duration: 900 }));
        hy.value = withSequence(withTiming(8, { duration: 900, easing: ease }), withDelay(9600, withTiming(0, { duration: 900 })));
        hx.value = withSequence(withTiming(-24, { duration: 900, easing: ease }), withDelay(9600, withTiming(0, { duration: 900 })));
        headR.value = withSequence(withTiming(-6, { duration: 900 }), withDelay(9600, withTiming(0, { duration: 900 })));
        break;
    }
    if (action.kind !== 'sit') {
      propO.value = withSequence(withTiming(1, { duration: 300 }), withDelay(1900, withTiming(0, { duration: 400 })));
      propS.value = withSequence(withTiming(1.1, { duration: 300 }), withTiming(1, { duration: 200 }));
    }
  }, [action, hy, hx, hr, hry, hsy, armL, armR, headR, snout, propO, propS]);

  const body = useAnimatedStyle(() => ({
    transform: [
      { perspective: 600 },
      { translateX: hx.value },
      { translateY: hy.value + idle.value },
      { rotate: `${hr.value}deg` },
      { rotateY: `${hry.value}deg` },
      { scaleY: hsy.value },
    ],
  }));
  const aL = useAnimatedStyle(() => ({ transform: [{ rotate: `${armL.value}deg` }] }));
  const aR = useAnimatedStyle(() => ({ transform: [{ rotate: `${armR.value}deg` }] }));
  const head = useAnimatedStyle(() => ({ transform: [{ rotate: `${headR.value}deg` }, { translateY: headR.value * 0.4 }] }));
  const sn = useAnimatedStyle(() => ({ transform: [{ scaleY: snout.value }] }));
  const ey = useAnimatedStyle(() => ({ transform: [{ scaleY: eyes.value }] }));
  const prop = useAnimatedStyle(() => ({ opacity: propO.value, transform: [{ scale: propS.value }] }));

  const layer = { position: 'absolute' as const, width: size, height: size, left: 0, top: 0 };

  return (
    <View style={{ width: size, height: size }} accessibilityLabel="꼬마하마">
      <View style={layer}>
        <L size={size}><Ellipse cx={100} cy={186} rx={52} ry={8} fill="#00000012" /></L>
      </View>
      <Animated.View style={[layer, { transformOrigin: '50% 90%' }, body]}>
        <View style={layer}>
          <L size={size}>
            <Rect x={70} y={150} width={22} height={32} rx={10} fill={C.hippoDark} />
            <Rect x={108} y={150} width={22} height={32} rx={10} fill={C.hippoDark} />
          </L>
        </View>
        <Animated.View style={[layer, { transformOrigin: '31% 59%' }, aL]}>
          <L size={size}><Ellipse cx={58} cy={132} rx={11} ry={18} transform="rotate(20 58 132)" fill={C.hippoDark} /></L>
        </Animated.View>
        <Animated.View style={[layer, { transformOrigin: '69% 59%' }, aR]}>
          <L size={size}><Ellipse cx={142} cy={132} rx={11} ry={18} transform="rotate(-20 142 132)" fill={C.hippoDark} /></L>
        </Animated.View>
        <View style={layer}>
          <L size={size}>
            <Ellipse cx={100} cy={138} rx={46} ry={40} fill={C.hippo} />
            <Ellipse cx={100} cy={146} rx={28} ry={24} fill={C.belly} />
          </L>
        </View>
        <Animated.View style={[layer, { transformOrigin: '50% 55%' }, head]}>
          <View style={layer}>
            <L size={size}>
              <Ellipse cx={68} cy={44} rx={10} ry={9} fill={C.hippoDark} />
              <Ellipse cx={132} cy={44} rx={10} ry={9} fill={C.hippoDark} />
              <Ellipse cx={68} cy={45} rx={5} ry={4} fill={C.cheek} />
              <Ellipse cx={132} cy={45} rx={5} ry={4} fill={C.cheek} />
              <Ellipse cx={100} cy={76} rx={46} ry={38} fill={C.hippo} />
              <Ellipse cx={66} cy={88} rx={7} ry={4.5} fill={C.cheek} opacity={0.7} />
              <Ellipse cx={134} cy={88} rx={7} ry={4.5} fill={C.cheek} opacity={0.7} />
            </L>
          </View>
          <Animated.View style={[layer, { transformOrigin: '50% 32%' }, ey]}>
            <L size={size}>
              <Circle cx={82} cy={64} r={5.5} fill={C.ink} />
              <Circle cx={118} cy={64} r={5.5} fill={C.ink} />
              <Circle cx={84} cy={62} r={1.8} fill="#fff" />
              <Circle cx={120} cy={62} r={1.8} fill="#fff" />
            </L>
          </Animated.View>
          <Animated.View style={[layer, { transformOrigin: '50% 46%' }, sn]}>
            <L size={size}>
              <Ellipse cx={100} cy={94} rx={34} ry={21} fill={C.belly} />
              <Ellipse cx={89} cy={88} rx={3.5} ry={4.5} fill={C.hippoDark} />
              <Ellipse cx={111} cy={88} rx={3.5} ry={4.5} fill={C.hippoDark} />
              <Path d="M90 100 Q100 108 110 100" stroke={C.ink} strokeWidth={2.6} fill="none" strokeLinecap="round" />
            </L>
          </Animated.View>
        </Animated.View>
      </Animated.View>
      {action && action.kind !== 'sit' && (
        <Animated.View key={action.key} pointerEvents="none" style={[styles.prop, PROP_POS[action.kind], prop]}>
          <Text style={styles.propText}>{CATS[action.kind].prop}</Text>
        </Animated.View>
      )}
    </View>
  );
}

function L({ size, children }: { size: number; children: React.ReactNode }) {
  return <Svg width={size} height={size} viewBox="0 0 200 200">{children}</Svg>;
}

const styles = StyleSheet.create({
  prop: { position: 'absolute' },
  propText: { fontSize: 40 },
});
