import type { Session } from '@supabase/supabase-js';
import { createContext, use, useCallback, useEffect, useMemo, useState, type PropsWithChildren } from 'react';
import { AppState } from 'react-native';

import { api, type Item, type Profile, type Win } from '@/lib/api';
import { track } from '@/lib/analytics';
import { kstToday } from '@/lib/dates';
import { reschedule } from '@/lib/notifications';
import { supabase } from '@/lib/supabase';

export type Celebration = { key: number; itemId: string; line: string };

type Ctx = {
  celebration: Celebration | null;
  celebrate: (c: Omit<Celebration, 'key'>) => void;
  ready: boolean;
  session: Session | null;
  profile: Profile | null;
  wins: Win[];
  balance: number;
  items: Item[];
  owned: string[];
  refresh: () => Promise<void>;
  setWins: React.Dispatch<React.SetStateAction<Win[]>>;
  setBalance: (n: number) => void;
  setOwned: React.Dispatch<React.SetStateAction<string[]>>;
  updateProfile: (patch: Partial<Profile>) => Promise<void>;
  signOut: () => Promise<void>;
};

const AppCtx = createContext<Ctx | null>(null);

export function useApp() {
  const v = use(AppCtx);
  if (!v) throw new Error('useApp outside AppProvider');
  return v;
}

export function AppProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<Session | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [loadedUid, setLoadedUid] = useState<string | null>(null);
  const [celebration, setCelebration] = useState<Celebration | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [wins, setWins] = useState<Win[]>([]);
  const [balance, setBalance] = useState(0);
  const [items, setItems] = useState<Item[]>([]);
  const [owned, setOwned] = useState<string[]>([]);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setAuthReady(true);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    // 앱이 앞에 있을 때만 토큰 자동 갱신 (Supabase RN 권장)
    const appSub = AppState.addEventListener('change', (st) => {
      if (st === 'active') supabase.auth.startAutoRefresh();
      else supabase.auth.stopAutoRefresh();
    });
    return () => {
      sub.subscription.unsubscribe();
      appSub.remove();
    };
  }, []);

  const uid = session?.user.id;

  const refresh = useCallback(async () => {
    if (!uid) return;
    const [p, w, b, it, ow] = await Promise.all([
      supabase.from('profiles').select('*').eq('id', uid).single(),
      supabase.from('wins').select('*').order('win_date', { ascending: false }).order('created_at', { ascending: false }).limit(2000),
      api.balance(),
      supabase.from('items').select('*').order('sort'),
      supabase.from('owned_items').select('item_id, created_at').order('created_at'),
    ]);
    if (p.data) setProfile(p.data as Profile);
    if (w.data) setWins(w.data as Win[]);
    setBalance(b);
    if (it.data) setItems(it.data as Item[]);
    if (ow.data) setOwned(ow.data.map((o) => o.item_id as string));
  }, [uid]);

  useEffect(() => {
    if (!authReady || !uid) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- 서버 데이터 비동기 로드 (외부 시스템 동기화)
    refresh().finally(() => setLoadedUid(uid));
    track('app_open');
  }, [authReady, uid, refresh]);

  // 알림 예약: 프로필·오늘 기록 여부가 바뀔 때마다 다시 잡는다
  const recordedToday = wins.some((w) => w.win_date === kstToday());
  useEffect(() => {
    if (!profile) return;
    reschedule({
      enabled: profile.notify_enabled,
      time: profile.notify_time.slice(0, 5),
      petName: profile.pet_name,
      recordedToday,
    }).catch(() => {});
  }, [profile, recordedToday]);

  const updateProfile = useCallback(async (patch: Partial<Profile>) => {
    if (!uid) return;
    const { data, error } = await supabase.from('profiles').update(patch).eq('id', uid).select().single();
    if (error) throw error;
    setProfile(data as Profile);
  }, [uid]);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
  }, []);

  const celebrate = useCallback((c: Omit<Celebration, 'key'>) => {
    const key = Date.now();
    setCelebration({ ...c, key });
    setTimeout(() => setCelebration((cur) => (cur?.key === key ? { ...cur, line: '' } : cur)), 3500);
  }, []);

  // 로그아웃 상태면 이전 사용자 데이터를 노출하지 않는다
  const mine = !!uid && loadedUid === uid;
  const value = useMemo<Ctx>(() => ({
    ready: authReady && (!uid || loadedUid === uid), session,
    profile: mine ? profile : null, wins: mine ? wins : [], balance: mine ? balance : 0,
    items, owned: mine ? owned : [], celebration,
    refresh, setWins, setBalance, setOwned, updateProfile, signOut, celebrate,
  }), [authReady, uid, loadedUid, mine, session, profile, wins, balance, items, owned, celebration, refresh, updateProfile, signOut, celebrate]);

  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>;
}
