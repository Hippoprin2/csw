# Render the app-format comparison table as a PNG (Slack has no tables).
from PIL import Image, ImageDraw, ImageFont
F = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
def font(sz, bold=False):
    return ImageFont.truetype(F, sz, index=6 if bold else 0)

rows = [
    ("항목", "A. 미리 렌더한 움직이는 이미지 (WebP)", "B. 앱 안에서 3D 직접 재생 (GLB)"),
    ("방식", "동작 1개 = 움직이는 이미지 1개 (GIF처럼)", "3D 파일 1개를 앱에서 실시간으로 그림"),
    ("앱 용량", "약 5~6MB (9개 동작, 원본 해상도)\n※ 만세 1개 실측 578KB", "약 2~3MB (최적화 후 추정)\n※ 현재 6.3MB"),
    ("품질", "지금 렌더와 똑같음 (색·조명·눈·소품)", "조명을 앱에서 다시 맞춰야 함\n→ 색이 달라질 위험"),
    ("개발 기간", "1~2일 (Pet.tsx만 교체)", "4~6일 (three.js 등 추가)"),
    ("새 라이브러리", "없음 (expo-image 기존 사용)", "필요 (expo-gl, three.js)"),
    ("폰 성능·배터리", "가벼움", "저가 안드로이드에서 확인 필요"),
    ("보는 각도", "고정 (3/4 구도)", "자유롭게 바꿀 수 있음"),
    ("꾸미기 아이템\n(모자·리본)", "아이템마다 겹칠 이미지를 따로 렌더\n아이템 늘수록 용량 증가", "머리에 바로 붙임\n아이템 늘어도 용량 거의 그대로"),
    ("탭 반응 등\n상호작용", "미리 만든 동작만 재생", "자유롭게 가능"),
    ("실기기 확인", "재생 끝 감지, 메모리", "속도, 배터리, 색 맞추기"),
    ("추천", "지금(MVP) 추천", "꾸미기 아이템이 많아지면"),
]
W = [260, 720, 720]
pad = 22
f_h, f_b, f_t = font(30, True), font(28), font(40, True)
def lines(t): return t.split("\n")
row_h = []
for r in rows:
    n = max(len(lines(c)) for c in r)
    row_h.append(n * 40 + 2 * pad)
title_h = 100
Wt, Ht = sum(W) + 40, sum(row_h) + title_h + 60
img = Image.new("RGB", (Wt, Ht), (250, 247, 240))
d = ImageDraw.Draw(img)
d.text((20, 30), "캐릭터 앱 형식 비교 (2026-11-08)", font=f_t, fill=(70, 50, 40))
y = title_h
for i, (r, h) in enumerate(zip(rows, row_h)):
    x = 20
    for j, (c, w) in enumerate(zip(r, W)):
        if i == 0:
            bg = (237, 150, 140) if j else (210, 190, 170)
        elif i == len(rows) - 1:
            bg = (255, 236, 190) if j == 1 else (245, 238, 228)
        else:
            bg = (255, 255, 255) if j else (242, 230, 214)
        d.rectangle([x, y, x + w, y + h], fill=bg, outline=(220, 205, 190), width=2)
        fnt = f_h if (i == 0 or j == 0 or i == len(rows) - 1) else f_b
        col = (255, 255, 255) if i == 0 and j else (60, 45, 38)
        for k, ln in enumerate(lines(c)):
            d.text((x + pad, y + pad + k * 40), ln, font=fnt, fill=col)
        x += w
    y += h
out = "/Users/soniakang/projects/csw/design/character/3d/share/app_format_comparison.png"
img.save(out); print(out, img.size)
