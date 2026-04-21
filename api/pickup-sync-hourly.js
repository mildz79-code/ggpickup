import { runPickupDocSync } from '../lib/google-doc-sync.js';

export default async function handler(req, res) {
  console.log('[pickup-sync-hourly] Vercel cron triggered');

  try {
    const result = await runPickupDocSync();
    const status = result.ok ? 200 : 500;
    return res.status(status).json(result);
  } catch (error) {
    console.error('[pickup-sync-hourly] error:', error);
    return res.status(500).json({ ok: false, error: error?.message || 'Sync failed' });
  }
}
