// app.json + 키에 따라 붙는 네이티브 로그인 플러그인 (2026-11-21 K6)
// 키는 EAS 환경 변수(scripts/eas_env_sync.py) 또는 로컬 .env.local. 키가 없으면 플러그인을 빼서 빌드는 그대로 됨(브라우저 로그인).
module.exports = ({ config }) => {
  const kakao = process.env.EXPO_PUBLIC_KAKAO_NATIVE_KEY;
  const googleIos = process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID; // ….apps.googleusercontent.com
  const plugins = [...(config.plugins ?? [])];
  plugins.push([
    'expo-build-properties',
    { android: { extraMavenRepos: ['https://devrepo.kakao.com/nexus/content/groups/public/'] } },
  ]);
  if (kakao) plugins.push(['@react-native-kakao/core', { nativeAppKey: kakao, android: { authCodeHandlerActivity: true }, ios: { handleKakaoOpenUrl: true } }]);
  if (googleIos) {
    const scheme = 'com.googleusercontent.apps.' + googleIos.replace('.apps.googleusercontent.com', '');
    plugins.push(['@react-native-google-signin/google-signin', { iosUrlScheme: scheme }]);
  } else {
    plugins.push('@react-native-google-signin/google-signin');
  }
  return { ...config, plugins };
};
