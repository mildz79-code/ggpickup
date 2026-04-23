import { runPickupDocSync } from '../../lib/google-doc-sync.js';

export const config = {
  schedule: '0 * * * *',
};

/**
 * Scheduled sync: Netlify invokes this on the schedule in `export const config`.
 * Keeps today's rows aligned with the Google Doc.
 */
export default async (req) => {
  let nextRun;
  try {
    const body = await req.json();
    nextRun = body?.next_run;
  } catch {
    nextRun = undefined;
  }
  console.log('[pickup-sync-hourly] next_run=', nextRun);

  const result = await runPickupDocSync();
  const status = result.ok ? 200 : 500;
  return new Response(JSON.stringify(result), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8' },
  });
};
