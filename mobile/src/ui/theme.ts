// 앱 UI 색·모양 = "A 포근한 창" (2026-11-13 대표 선택, docs/ART_BIBLE.md 11장)
// 캐릭터·공간·아이템 그림은 건드리지 않는다. 여기는 그림 밖 UI만.
// 예전 주황(#ff8a5c)·보라(#aaa2dc)는 쓰지 않는다.
export const C = {
  bg: '#FBF6EC', // 바탕 (크림)
  ink: '#4A3226', // 글자
  muted: '#6E5848', // 보조 글자
  soft: '#F1E8D8', // 옅은 면 (칩·세그먼트 바탕)
  card: '#FFFFFF', // 카드·입력칸
  accent: '#2F7D6B', // 포인트 (주 버튼, 보내기, 씨앗 잎)
  accentBg: '#E3F1EC', // 활성 배경 (선택된 탭·칩)
  accentInk: '#1F5F50', // 활성 글자
  danger: '#A13A2A', // 위험 동작 글자
  divider: '#F1E8D8', // 흰 카드 안 줄 사이 (테두리 대신 면 색 한 줄)
  scrim: 'rgba(74,50,38,0.32)', // 시트 뒤
  chip: 'rgba(251,246,236,0.94)', // 그림 위에 뜨는 크림 칩
  seed: '#2F7D6B',
  white: '#FFFFFF',
};

// 모양은 두 계열만: 카드 22~28 / 알약(높이의 절반 → 999). 1px 테두리는 쓰지 않는다.
export const R = { card: 22, cardLg: 28, sheet: 32, pill: 999 };

// 알약 높이
export const H = { btn: 52, input: 56, chip: 36, tab: 68 };

// 화면 아래 떠 있는 탭 바가 차지하는 높이 (내용이 가려지지 않게 아래 여백으로 씀)
export const TAB_SPACE = H.tab + 24 + 12;
