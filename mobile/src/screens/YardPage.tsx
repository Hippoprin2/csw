import { StyleSheet, Text, View } from 'react-native';

import { useApp } from '@/state/app';
import { useSpaceSize } from '@/ui/layout';
import { C } from '@/ui/theme';

// 마당 = 첫 업데이트. 출시에는 잠긴 문만 (구슬 10개면 열림, 남은 개수 카운트다운은 넣지 않음 — WORLD 1장)
export const YARD_UNLOCK = 10;

export function YardPage() {
  const { jars } = useApp();
  const open = jars.total >= YARD_UNLOCK;
  const { gardenSize } = useSpaceSize();
  return (
    <View style={st.wrap}>
      <View style={[st.yard, { width: gardenSize, height: gardenSize }]}>
        <View style={st.hedge} />
        <Text style={st.tree}>🌳</Text>
        <Text style={st.pond}>💧</Text>
        <View style={st.gate}>
          <Text style={st.gateIcon}>{open ? '🏡' : '🚪'}</Text>
          <Text style={st.gateTitle}>{open ? '마당 문이 열렸어!' : `구슬 ${YARD_UNLOCK}개면 열려`}</Text>
          <Text style={st.gateSub}>{open ? '단짝이 뛰어놀 마당을 준비하고 있어. 곧 만나!' : '문 너머로 연못이 살짝 보여'}</Text>
        </View>
      </View>
    </View>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg },
  yard: { alignSelf: 'center', borderRadius: 28, overflow: 'hidden', backgroundColor: '#d7ecd0' },
  hedge: { position: 'absolute', left: 0, right: 0, top: 0, height: '26%', backgroundColor: '#a9d29b' },
  tree: { position: 'absolute', right: 24, top: '12%', fontSize: 64, opacity: 0.6 },
  pond: { position: 'absolute', left: 40, bottom: 40, fontSize: 48, opacity: 0.5 },
  gate: { position: 'absolute', left: 30, right: 30, top: '34%', backgroundColor: '#fffaf2ee', borderRadius: 22, padding: 18, alignItems: 'center' },
  gateIcon: { fontSize: 40, marginBottom: 6 },
  gateTitle: { fontSize: 18, fontWeight: '800', color: C.ink },
  gateSub: { fontSize: 13, color: C.muted, marginTop: 4, textAlign: 'center' },
});
