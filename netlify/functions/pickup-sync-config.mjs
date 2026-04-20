import { getPickupTimezone, getTodayISOInTimezone } from '../../lib/google-doc-sync.js';

export const handler = async (event) => {
  if (event.httpMethod !== 'GET') {
    return {
      statusCode: 405,
      headers: { 'content-type': 'application/json; charset=utf-8' },
      body: JSON.stringify({ error: 'Method not allowed' }),
    };
  }

  const timezone = getPickupTimezone();
  const todayISO = getTodayISOInTimezone(timezone);

  return {
    statusCode: 200,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
    },
    body: JSON.stringify({ timezone, todayISO }),
  };
};
