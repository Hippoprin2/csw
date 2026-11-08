import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

// S3 하루 알림 + S4 일요일 주간 돌아보기. 로컬 예약 알림만 (서버 푸시 없음).
// 규칙: 하루 최대 1회 / 오늘 이미 기록했으면 오늘 것은 안 보냄 / 앞으로 7일은 매일,
// 그 뒤로는 일요일만 → 앱을 7일 안 열면 자연스럽게 주 1회로 줄고, 다시 열면 매일로 복귀.
// 문구: 질문형·초대형만. 부재·숫자·죄책감·명령형 금지.

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldPlaySound: false, shouldSetBadge: false, shouldShowBanner: true, shouldShowList: true,
  }),
});

const daily = (pet: string) => [
  '오늘 해낸 거 하나만 알려줄래?',
  '물 한 잔 마신 것도 승리야. 오늘은 뭐 했어?',
  `${pet}가 오늘 이야기 듣고 싶대`,
  '아주 작은 일이어도 좋아. 오늘 해낸 거 있어?',
  '오늘 하루, 잘 넘긴 일 하나 같이 떠올려볼까?',
  '침대 정리도, 답장 하나도 다 승리야. 오늘은?',
  `${pet}가 유리병에 구슬 넣을 준비 됐대`,
  '오늘의 작은 승리, 들려줄래?',
  '오늘 너를 위해 한 일 하나만 적어볼까?',
  '하루 중에 "이건 했다" 싶은 거 있어?',
];

export async function askPermission(): Promise<boolean> {
  const cur = await Notifications.getPermissionsAsync();
  if (cur.granted) return true;
  const req = await Notifications.requestPermissionsAsync();
  return req.granted;
}

export async function hasPermission() {
  return (await Notifications.getPermissionsAsync()).granted;
}

export async function reschedule(opts: { enabled: boolean; time: string; petName: string; recordedToday: boolean }) {
  await Notifications.cancelAllScheduledNotificationsAsync();
  if (!opts.enabled || !(await hasPermission())) return;
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('daily', { name: '하루 알림', importance: 3 /* DEFAULT */ });
  }
  const [h, m] = opts.time.split(':').map(Number);
  const lines = daily(opts.petName);
  const now = new Date();
  const seed = Math.floor(now.getTime() / 86400000);

  const at = (dayOffset: number) => {
    const d = new Date(now);
    d.setDate(d.getDate() + dayOffset);
    d.setHours(h, m, 0, 0);
    return d;
  };
  const schedule = (date: Date, body: string, kind: string) =>
    Notifications.scheduleNotificationAsync({
      content: { title: opts.petName, body, data: { kind } },
      trigger: { type: Notifications.SchedulableTriggerInputTypes.DATE, date, channelId: 'daily' },
    });

  for (let i = 0; i < 7; i++) {
    const date = at(i);
    if (date <= now) continue;
    const sunday = date.getDay() === 0;
    if (i === 0 && opts.recordedToday && !sunday) continue;
    if (sunday) await schedule(date, '이번 주 유리병이 준비됐어. 같이 돌아볼래?', 'weekly');
    else await schedule(date, lines[(seed + i) % lines.length], 'daily');
  }
  // 7일 뒤부터는 일요일만 8주
  let i = 7;
  let added = 0;
  while (added < 8) {
    const date = at(i);
    if (date.getDay() === 0) {
      await schedule(date, '이번 주에 한 가장 작은 일 하나만 떠올려볼래?', 'weekly');
      added++;
    }
    i++;
  }
}
