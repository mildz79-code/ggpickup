import { getPickupTimezone, getTodayISOInTimezone } from '../lib/google-doc-sync.js';

export default function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const timezone = getPickupTimezone();
  const todayISO = getTodayISOInTimezone(timezone);

  res.setHeader('Cache-Control', 'no-store');
  return res.status(200).json({ timezone, todayISO });
}
