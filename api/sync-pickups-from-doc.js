import { runPickupDocSync } from '../lib/google-doc-sync.js';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed. Use POST.' });
  }

  try {
    const result = await runPickupDocSync();
    if (!result.ok) {
      return res.status(500).json({ error: result.error || 'Sync failed' });
    }
    return res.status(200).json({
      ok: true,
      synced: result.synced,
      scanned: result.scanned,
      scanned_today: result.scanned_today,
      request_date: result.request_date,
      timezone: result.timezone,
      message: result.message,
    });
  } catch (error) {
    console.error('sync-pickups-from-doc error:', error);
    return res.status(500).json({ error: error?.message || 'Sync failed' });
  }
}
