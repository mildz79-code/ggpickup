import { runPickupDocSync } from '../../lib/google-doc-sync.js';

function json(statusCode, body) {
  return {
    statusCode,
    headers: { 'content-type': 'application/json; charset=utf-8' },
    body: JSON.stringify(body),
  };
}

export const handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return json(405, { error: 'Method not allowed. Use POST.' });
  }

  try {
    const result = await runPickupDocSync();
    if (!result.ok) {
      return json(500, { error: result.error || 'Sync failed' });
    }
    return json(200, {
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
    return json(500, { error: error?.message || 'Sync failed' });
  }
};
