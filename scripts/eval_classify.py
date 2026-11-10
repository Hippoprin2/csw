#!/usr/bin/env python3
"""분류 정확도 확인 (키워드 / LLM). 공부·업무 분리 후 헷갈리기 쉬운 문장 위주.
사용: python3 scripts/eval_classify.py
"""
import pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sb import req, temp_user, delete_user, ROOT  # noqa: E402

CASES = [
    ('study', '영어 단어 30개 외웠다'), ('study', '인강 한 강 들었다'), ('study', '시험공부 2시간'), ('study', '책 10쪽 읽었다'),
    ('study', '과제 제출했다'), ('study', '자격증 문제집 풀었다'), ('study', '수업 빠지지 않고 들음'), ('study', '코딩 강의 들으면서 공부'),
    ('work', '보고서 마감했다'), ('work', '출근했다'), ('work', '회의에서 의견 말했다'), ('work', '메일 답장 다 했다'),
    ('work', '야근 끝내고 퇴근'), ('work', '알바 4시간 했다'), ('work', '엑셀 정리 끝'), ('work', '클라이언트 미팅 잘 끝냄'),
    ('tidy', '설거지 했다'), ('move', '30분 걸었다'), ('eat', '아침밥 챙겨 먹음'), ('care', '일찍 잤다'),
    ('people', '엄마한테 전화했다'), ('cheer', '용기 내서 병원 예약 전화'),
    ('endure', '힘들다'), ('endure', '오늘 너무 지쳤어'), ('endure', '우울해'), ('endure', '오늘 하루 망했다'),
    ('endure', '아무것도 못 했어'), ('endure', '팔을 그었어'), ('endure', '외롭다'), ('endure', '회사에서 혼나서 속상해'),
    ('move', '힘들었지만 운동했다'), ('work', '지쳤지만 출근했다'), ('tidy', '우울했는데 설거지는 했다'), ('care', '힘들어서 일찍 잤다'),
]

# 앱 키워드 분류를 그대로 재현 (mobile/src/lib/categories.ts)
src = (ROOT / 'mobile/src/lib/categories.ts').read_text()
order = re.search(r"CATEGORY_ORDER: Category\[\] = \[([^\]]+)\]", src).group(1).replace("'", '').replace(' ', '').split(',')
kws = {k: re.findall(r"'([^']+)'", re.search(rf"\n  {k}: \{{.*?kw: \[([^\]]*)\]", src, re.S).group(1)) for k in order}
def kw_classify(t):
    for k in order:
        if any(w in t for w in kws[k]):
            return k
    return 'cheer'

T, uid = temp_user()
try:
    kw_ok = llm_ok = 0
    for want, t in CASES:
        s, r = req('POST', '/functions/v1/classify', {'text': t}, token=T)
        k, l = kw_classify(t), r.get('category')
        kw_ok += k == want; llm_ok += l == want
        flag = '' if l == want else '  ← LLM 틀림'
        print(f'{want:6s} kw={k:6s} llm={l}  {t}{flag}')
    print(f'\n키워드 {kw_ok}/{len(CASES)} · LLM {llm_ok}/{len(CASES)}')
finally:
    delete_user(uid)
