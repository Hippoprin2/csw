// 공통 동작 7종 (docs/GAME_DESIGN.md). 한마디는 카테고리별 템플릿 (FEATURES D2=A).
export type Category = 'tidy' | 'move' | 'study' | 'eat' | 'care' | 'people' | 'cheer';

export const CATEGORY_ORDER: Category[] = ['tidy', 'move', 'study', 'eat', 'care', 'people', 'cheer'];

export const CATS: Record<Category, { name: string; prop: string; color: string; kw: string[]; say: string[] }> = {
  tidy: {
    name: '정리·청소', prop: '🧹', color: '#9ccfd8',
    kw: ['정리', '청소', '설거지', '빨래', '이불', '침대', '쓰레기', '분리수거', '치우', '개켰', '닦', '빨았', '세탁'],
    say: ['방이 반짝반짝해졌어!', '정리한 너, 진짜 멋져', '깨끗해진 만큼 마음도 가벼워졌지?', '쓱싹쓱싹, 해냈다!', '정돈된 자리에 기분도 좋아져', '치운 사람 최고야'],
  },
  move: {
    name: '몸 움직이기', prop: '💦', color: '#f6b26b',
    kw: ['운동', '산책', '걷', '스트레칭', '요가', '헬스', '러닝', '뛰', '계단', '자전거', '수영', '필라테스', '등산', '춤'],
    say: ['몸을 움직였구나! 최고야', '오늘도 한 걸음!', '땀 흘린 너를 응원해', '몸이 고마워하고 있을 거야', '움직인 만큼 가벼워졌지?', '폴짝! 같이 신나'],
  },
  study: {
    name: '공부·일', prop: '📖', color: '#a4c2f4',
    kw: ['공부', '책', '읽', '과제', '숙제', '업무', '일했', '회의', '보고서', '메일', '강의', '출근', '코딩', '시험', '발표', '복습'],
    say: ['집중한 너, 대단해', '오늘 한 만큼 분명히 쌓였어', '머리 쓰느라 고생했어', '한 줄이라도 나아간 거야', '끄덕끄덕, 잘했어', '해야 할 걸 해낸 너, 멋져'],
  },
  eat: {
    name: '잘 먹기', prop: '🍙', color: '#f9cb9c',
    kw: ['먹', '요리', '밥', '아침', '점심', '저녁', '물 한', '물을', '물 마', '도시락', '채소', '과일', '마셨'],
    say: ['잘 챙겨 먹었구나, 냠냠', '너를 먹여 살린 너, 칭찬해', '든든하지?', '몸에 좋은 걸 줬네', '맛있게 먹은 것도 승리야', '냠냠, 나도 배불러'],
  },
  care: {
    name: '나 돌보기', prop: '✨', color: '#d5a6bd',
    kw: ['씻', '샤워', '양치', '약', '잠', '일찍', '명상', '쉬었', '쉬기', '피부', '일기', '병원', '낮잠', '목욕', '휴식'],
    say: ['너를 돌봐준 거, 정말 잘했어', '오늘 너한테 다정했네', '반짝반짝 빛나는 중', '쉬는 것도 해낸 일이야', '너를 아껴줘서 고마워', '개운하지?'],
  },
  people: {
    name: '사람·마음', prop: '💌', color: '#ea9999',
    kw: ['연락', '전화', '친구', '엄마', '아빠', '가족', '아이', '고마', '칭찬', '만나', '안부', '사과', '인사', '선물', '도와'],
    say: ['마음을 전했구나', '누군가에게 따뜻한 하루가 됐을 거야', '다정한 너, 좋아', '연결된 마음, 멋져', '그 마음 분명히 닿았을 거야', '손 흔들어 줄게!'],
  },
  cheer: {
    name: '그 밖의 승리', prop: '🎉', color: '#b6d7a8',
    kw: [],
    say: ['해냈다! 축하해', '작은 승리도 승리야', '오늘의 너, 칭찬해', '만세! 정말 잘했어', '이것도 분명한 한 걸음이야', '네가 해낸 거 다 기억할게'],
  },
};

export function classifyByKeyword(text: string): Category {
  for (const k of CATEGORY_ORDER) if (CATS[k].kw.some((w) => text.includes(w))) return k;
  return 'cheer';
}

export const pickLine = (k: Category) => CATS[k].say[Math.floor(Math.random() * CATS[k].say.length)];

export const CHIPS = ['침대 정리했다', '물 한 잔 마셨다', '10분 산책', '책 5쪽 읽었다', '엄마한테 전화', '샤워했다'];

export const SAFETY_LINE = '말해줘서 고마워. 오늘 버틴 것도 정말 큰 일이야.';
