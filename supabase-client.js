// Shared Supabase client for GG Pickup driver app
// Color Fashion project: mtxokbgpmkggolyfeehz
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const SUPABASE_URL = 'https://mtxokbgpmkggolyfeehz.supabase.co';
const SUPABASE_PUBLISHABLE_KEY = 'sb_publishable_aghPRPsaoB8FBYqlNDSeWg_hdmAsQc8';

export const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: false,
    storageKey: 'ggpickup-auth',
  },
});

export async function requireSession() {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) {
    window.location.href = '/index.html';
    return null;
  }
  return session;
}

export async function getCurrentUserRole() {
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return null;
  const { data } = await supabase
    .from('app_users')
    .select('role, status, full_name')
    .eq('id', user.id)
    .maybeSingle();
  return data;
}

export function logout() {
  supabase.auth.signOut().finally(() => {
    window.location.href = '/index.html';
  });
}

export const BUCKET = 'greige-pickup-photos';
