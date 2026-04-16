// Supabase client for GG Pickup — Color Fashion project
// Repo: mildz79-code/ggpickup
// Deployed to: gg.colorfashiondnf.com (via Netlify)

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const SUPABASE_URL = 'https://cgsmzkafagnmsuzzkfnv.supabase.co';
const SUPABASE_PUBLISHABLE_KEY = 'sb_publishable_Iyz9y-l6obNYuAbmP1EpXQ_OUF2psVs';

export const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
    storageKey: 'ggpickup-auth',
  },
});

export const PICKUP_PHOTOS_BUCKET = 'greige-pickup-photos';

// TODO: replace shared password with per-driver auth before production
export const TEST_DRIVER_PASSWORD = 'Driver_CF_2026!';

export const DRIVERS = [
  { email: 'driver1@colorfashiondnf.com', name: 'Driver 1' },
  { email: 'driver2@colorfashiondnf.com', name: 'Driver 2' },
  { email: 'driver3@colorfashiondnf.com', name: 'Driver 3' },
];

// TODO: remove before production — dev auto-login
export const AUTO_LOGIN_EMAIL = 'daniel@colorfashiondnf.com';
export const AUTO_LOGIN_PASSWORD = 'CF2026admin';

export async function signInAsAdmin() {
  sessionStorage.removeItem('skipAutoLogin');
  return supabase.auth.signInWithPassword({
    email: AUTO_LOGIN_EMAIL,
    password: AUTO_LOGIN_PASSWORD,
  });
}

export async function signInAsDriver(email) {
  return supabase.auth.signInWithPassword({ email, password: TEST_DRIVER_PASSWORD });
}

export async function getCurrentAppUser() {
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return null;
  const { data, error } = await supabase
    .from('app_users')
    .select('id, email, full_name, role, is_active')
    .eq('id', user.id)
    .maybeSingle();
  if (error) { console.error('getCurrentAppUser:', error); return null; }
  return data;
}

export async function requireSession() {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) {
    window.location.replace('/index.html');
    return null;
  }
  return session;
}

export async function signOut() {
  sessionStorage.setItem('skipAutoLogin', '1');
  await supabase.auth.signOut();
  window.location.replace('/index.html');
}
