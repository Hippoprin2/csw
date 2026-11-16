// 앱 UI 색·모양 = "A 포근한 창" (2026-11-13 대표 선택, docs/ART_BIBLE.md 11장)
// 바탕 = 순백 (2026-11-13 대표 결정, 크림 #FBF6EC에서 변경). 흰 바탕이라 카드는 아주 옅은 회백색.
// ★ 화면 코드에 색 값(#… / rgba)을 직접 쓰지 않는다. 필요한 색은 여기 C(UI) 또는 ART(화면 속 그림 소품)에 이름을 붙여 넣고 쓴다.
//   → 바탕을 또 바꿔도 이 파일만 고치면 모든 화면에 반영된다. npm run lint가 직접 쓴 색을 오류로 잡는다.
// 캐릭터·공간·아이템 그림은 건드리지 않는다. 여기는 그림 밖 UI만.
// 예전 주황(#ff8a5c)·보라(#aaa2dc)는 쓰지 않는다.
export const C = {
  bg: '#FFFFFF', // 바탕 (순백)
  ink: '#4A3226', // 글자
  muted: '#6E5848', // 보조 글자
  soft: '#F2F0EB', // 옅은 면 (칩·세그먼트 바탕)
  card: '#F7F6F3', // 카드·입력칸·탭 바 (흰 바탕과 면 색으로 구분)
  accent: '#2F7D6B', // 포인트 (주 버튼, 보내기, 씨앗 잎)
  accentBg: '#E3F1EC', // 활성 배경 (선택된 탭·칩)
  accentInk: '#1F5F50', // 활성 글자
  danger: '#A13A2A', // 위험 동작 글자
  divider: '#ECE9E3', // 카드 안 줄 사이 (테두리 대신 면 색 한 줄)
  scrim: 'rgba(74,50,38,0.32)', // 시트 뒤
  chip: 'rgba(255,255,255,0.94)', // 그림 위에 뜨는 칩 (바탕색 반투명)
  veil: 'rgba(255,255,255,0.25)', // 잠긴 마당 그림 위 옅은 막
  stageVeil: 'rgba(255,255,255,0.42)', // 홈 하마 무대: 흐린 방 위 흰 막 (H1, 2026-11-16)
  composeScrim: 'rgba(74,50,38,0.14)', // 홈 입력 펼침 뒤 옅은 막
  toast: 'rgba(74,50,38,0.9)', // 잠깐 뜨는 알림 바탕 (글자는 white)
  track: '#E4E0D8', // 스위치 꺼짐·시트 손잡이 막대
  placeholder: '#A8968A', // 입력칸 안내 글자
  placeholderSoft: '#C9BBA8', // 인증번호처럼 자리만 보여주는 안내 글자
  shadow: '#4A3226', // 떠 있는 탭 바 그림자
  kakao: '#FEE500', kakaoInk: '#191919', // 카카오 로그인 버튼 (브랜드 규정 색)
  seed: '#2F7D6B',
  white: '#FFFFFF',
};

// 화면 속 그림 소품 색 (UI가 아니라 그림의 일부라 바탕색이 바뀌어도 그대로 둔다)
export const ART = {
  roomFill: '#EADBC4', // 방 그림 뒤 (그림 로딩 전·가장자리)
  zoomDim: '#1D140C', // 기록 축하 줌 때 주변 어둡게 (불투명도 0.28)
  gardenFill: '#cfe8c4', // 텃밭 그림 뒤
  sparkle: '#B07A1E', // 텃밭 반짝 아이콘
  jarGlass: '#fffaf2', jarLine: '#d9c9b1', jarLid: '#c9a27a', // 유리병·선반
};

// 모양은 두 계열만: 카드 22~28 / 알약(높이의 절반 → 999). 1px 테두리는 쓰지 않는다.
export const R = { card: 22, cardLg: 28, sheet: 32, pill: 999 };

// 알약 높이
export const H = { btn: 52, input: 56, chip: 36, tab: 68 };

// 화면 아래 떠 있는 탭 바가 차지하는 높이 (내용이 가려지지 않게 아래 여백으로 씀)
export const TAB_SPACE = H.tab + 24 + 12;
