// https://docs.expo.dev/guides/using-eslint/
const { defineConfig } = require('eslint/config');
const expoConfig = require('eslint-config-expo/flat');

module.exports = defineConfig([
  expoConfig,
  {
    ignores: ['dist/*'],
  },
  {
    // 색은 src/ui/theme.ts(C·ART)에만 둔다 → 바탕색 등을 바꾸면 모든 화면에 한 번에 반영 (ART_BIBLE 11장)
    files: ['src/**/*.{ts,tsx}'],
    ignores: ['src/ui/theme.ts', 'src/lib/categories.ts', 'src/ui/YardScene.tsx', 'src/data/**'],
    rules: {
      'no-restricted-syntax': ['error',
        { selector: 'Literal[value=/^#[0-9a-fA-F]{3,8}$/]', message: '색 값을 직접 쓰지 말고 ui/theme.ts의 C(UI) 또는 ART(그림 소품)에 이름을 붙여 쓰세요.' },
        { selector: 'Literal[value=/^rgba?\\(/]', message: '색 값을 직접 쓰지 말고 ui/theme.ts의 C 또는 ART에 넣어 쓰세요.' },
      ],
    },
  },
]);
