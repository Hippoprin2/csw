import { Platform } from 'react-native';

// 웹 테스트판(폰 사파리) 전용: 문서가 화면보다 커져 위가 잘리고, body overflow:hidden이어도 iOS는 손가락 스크롤·입력 포커스로
// 문서를 밀어 버림(대표 폰 2026-11-16, 위 날짜·씨앗 칩이 주소창 밑으로). html·body를 화면에 고정해 문서 자체가 못 움직이게 함.
// 높이는 고정된 body 높이(= 주소창·툴바 사이 실제 보이는 칸, 키보드엔 안 줄어듦)를 씀. 네이티브 앱은 해당 없음
if (Platform.OS === 'web' && typeof document !== 'undefined' && !document.getElementById('csw-viewport-fix')) {
  const el = document.createElement('style');
  el.id = 'csw-viewport-fix';
  el.textContent = 'html,body{position:fixed;top:0;left:0;right:0;bottom:0;width:100%;height:100%;overflow:hidden;overscroll-behavior:none;margin:0}#root{height:100%}';
  document.head.appendChild(el);
}

export function webBodyHeight() {
  return Platform.OS === 'web' && typeof document !== 'undefined' ? document.body.clientHeight : 0;
}
