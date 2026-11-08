// 웹은 알림 미지원 (개발 확인용)
export async function askPermission() { return false; }
export async function hasPermission() { return false; }
export async function reschedule(_: { enabled: boolean; time: string; petName: string; recordedToday: boolean }) {}
