// Supabase client for GG Pickup — Color Fashion project
// Repo: mildz79-code/ggpickup
// Deployed to: gg.colorfashiondnf.com (via Netlify)

import { createClient } from '@supabase/supabase-js';

// Color Fashion Supabase project
const SUPABASE_URL = 'https://cgsmzkafagnmsuzzkfnv.supabase.co';

// Publishable (anon) key — safe to expose in the browser; RLS enforces access.
// Modern sb_publishable_ format (preferred over legacy JWT anon key).
const SUPABASE_PUBLISHABLE_KEY = 'sb_publishable_Iyz9y-l6obNYuAbmP1EpXQ_OUF2psVs';

export const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});

// Storage bucket name for pickup photos (private bucket, authenticated access only)
export const PICKUP_PHOTOS_BUCKET = 'greige-pickup-photos';
