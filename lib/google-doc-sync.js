/**
 * Shared Google Doc → Supabase sync for greige_pickup_requests.
 * Used by HTTP function and scheduled function.
 */

import { google } from 'googleapis';

const REQUIRED_ENV = [
  'GOOGLE_DOC_ID',
  'GOOGLE_SERVICE_ACCOUNT_EMAIL',
  'GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY',
  'SUPABASE_URL',
  'SUPABASE_SERVICE_ROLE_KEY',
];

/** IANA timezone for "today" (e.g. America/New_York). Default matches typical US ops. */
export function getPickupTimezone() {
  return process.env.PICKUP_DATE_TIMEZONE || 'America/New_York';
}

export function getTodayISOInTimezone(timeZone) {
  const tz = timeZone || 'UTC';
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: tz,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
  const parts = formatter.formatToParts(new Date());
  const y = parts.find((p) => p.type === 'year')?.value;
  const m = parts.find((p) => p.type === 'month')?.value;
  const d = parts.find((p) => p.type === 'day')?.value;
  if (!y || !m || !d) {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  }
  return `${y}-${m}-${d}`;
}

export function listMissingEnv() {
  return REQUIRED_ENV.filter((k) => !process.env[k]);
}

function normalizeStatus(value) {
  const raw = String(value || '').trim().toLowerCase();
  if (!raw) return 'Pending';
  if (raw === 'pending') return 'Pending';
  if (raw === 'picked up' || raw === 'pickedup' || raw === 'done') return 'Picked Up';
  if (raw === 'cancelled' || raw === 'canceled') return 'Cancelled';
  return 'Pending';
}

function parseQty(value) {
  if (value == null) return 0;
  const n = Number(String(value).replace(/,/g, '').trim());
  return Number.isFinite(n) ? n : 0;
}

function getTextFromCell(cell) {
  if (!cell?.content) return '';
  return cell.content
    .map((part) => part?.paragraph?.elements || [])
    .flat()
    .map((el) => el?.textRun?.content || '')
    .join('')
    .replace(/\n/g, ' ')
    .trim();
}

/**
 * Parse date cells from Google Docs / Sheets paste (M/D/YYYY, MM/DD/YYYY, ISO, month names).
 */
export function readDate(input) {
  const value = String(input || '').trim();
  if (!value) return null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;

  const mdy = value.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})$/);
  if (mdy) {
    let month = Number(mdy[1]);
    let day = Number(mdy[2]);
    let year = Number(mdy[3]);
    if (year < 100) year += year >= 70 ? 1900 : 2000;
    if (month > 12 && day <= 12) {
      const t = month;
      month = day;
      day = t;
    }
    if (month >= 1 && month <= 12 && day >= 1 && day <= 31) {
      return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    }
  }

  const d = new Date(value);
  if (!Number.isNaN(d.getTime())) {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }
  return null;
}

function inferHeaderIndex(headers, candidates) {
  const normalized = headers.map((h) => h.toLowerCase().replace(/\s+/g, ' ').trim());
  return normalized.findIndex((h) => candidates.some((c) => h === c || h.includes(c)));
}

function tableRowsToRequests(tableRows) {
  if (!tableRows || tableRows.length < 2) return [];
  const headerCells = tableRows[0].tableCells || [];
  const headers = headerCells.map(getTextFromCell);

  const dateIdx = inferHeaderIndex(headers, ['date', 'request date']);
  const knitterIdx = inferHeaderIndex(headers, ['knitter']);
  const customerIdx = inferHeaderIndex(headers, ['customer', 'ship to']);
  const qtyIdx = inferHeaderIndex(headers, ['qty', 'quantity', 'lots']);
  const lotIdx = inferHeaderIndex(headers, ['lot', 'lot #', 'lot number']);
  const statusIdx = inferHeaderIndex(headers, ['status']);
  const notesIdx = inferHeaderIndex(headers, ['notes', 'remark']);

  if (dateIdx < 0 || knitterIdx < 0) {
    return [];
  }

  const rows = [];
  for (const row of tableRows.slice(1)) {
    const cells = row.tableCells || [];
    const requestDate = readDate(getTextFromCell(cells[dateIdx]));
    const knitter = getTextFromCell(cells[knitterIdx]).toUpperCase();
    if (!requestDate || !knitter) continue;

    rows.push({
      request_date: requestDate,
      knitter,
      customer: customerIdx >= 0 ? getTextFromCell(cells[customerIdx]).toUpperCase() || null : null,
      qty: qtyIdx >= 0 ? parseQty(getTextFromCell(cells[qtyIdx])) : 0,
      lot_number: lotIdx >= 0 ? getTextFromCell(cells[lotIdx]) || null : null,
      status: statusIdx >= 0 ? normalizeStatus(getTextFromCell(cells[statusIdx])) : 'Pending',
      notes: notesIdx >= 0 ? getTextFromCell(cells[notesIdx]) || null : null,
    });
  }
  return rows;
}

async function fetchDocRows() {
  const client = new google.auth.JWT({
    email: process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL,
    key: process.env.GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY.replace(/\\n/g, '\n'),
    scopes: ['https://www.googleapis.com/auth/documents.readonly'],
  });
  await client.authorize();
  const docs = google.docs({ version: 'v1', auth: client });
  const res = await docs.documents.get({ documentId: process.env.GOOGLE_DOC_ID });
  const document = res?.data;
  const bodyContent = document?.body?.content || [];
  const rows = [];
  for (const block of bodyContent) {
    const table = block?.table;
    if (!table?.tableRows?.length) continue;
    rows.push(...tableRowsToRequests(table.tableRows));
  }
  return rows;
}

async function replaceTodayInSupabase(todaysRows, todayISO) {
  const baseHeaders = {
    'Content-Type': 'application/json',
    apikey: process.env.SUPABASE_SERVICE_ROLE_KEY,
    Authorization: `Bearer ${process.env.SUPABASE_SERVICE_ROLE_KEY}`,
  };

  const deleteResp = await fetch(
    `${process.env.SUPABASE_URL}/rest/v1/greige_pickup_requests?request_date=eq.${todayISO}`,
    {
      method: 'DELETE',
      headers: {
        ...baseHeaders,
        Prefer: 'return=minimal',
      },
    }
  );
  if (!deleteResp.ok) {
    const text = await deleteResp.text();
    throw new Error(`Supabase delete failed (${deleteResp.status}): ${text}`);
  }

  if (!todaysRows.length) {
    return [];
  }

  const insertResp = await fetch(`${process.env.SUPABASE_URL}/rest/v1/greige_pickup_requests`, {
    method: 'POST',
    headers: {
      ...baseHeaders,
      Prefer: 'return=representation',
    },
    body: JSON.stringify(todaysRows),
  });
  if (!insertResp.ok) {
    const text = await insertResp.text();
    throw new Error(`Supabase insert failed (${insertResp.status}): ${text}`);
  }
  return insertResp.json();
}

/**
 * @returns {{ ok: boolean, synced: number, scanned: number, scanned_today: number, request_date: string, message?: string, error?: string }}
 */
export async function runPickupDocSync() {
  const missing = listMissingEnv();
  if (missing.length) {
    return {
      ok: false,
      error: `Missing required environment variables: ${missing.join(', ')}`,
      synced: 0,
      scanned: 0,
      scanned_today: 0,
      request_date: getTodayISOInTimezone(getPickupTimezone()),
    };
  }

  const tz = getPickupTimezone();
  const todayISO = getTodayISOInTimezone(tz);
  const rows = await fetchDocRows();
  const todaysRows = rows.filter((r) => r.request_date === todayISO);

  if (!rows.length) {
    await replaceTodayInSupabase([], todayISO);
    return {
      ok: true,
      synced: 0,
      scanned: 0,
      scanned_today: 0,
      request_date: todayISO,
      message: 'No valid rows found in Google Doc tables; cleared today in Supabase.',
    };
  }

  const result = await replaceTodayInSupabase(todaysRows, todayISO);
  const uniqueDates = [...new Set(rows.map((r) => r.request_date))].sort();
  return {
    ok: true,
    synced: Array.isArray(result) ? result.length : todaysRows.length,
    scanned: rows.length,
    scanned_today: todaysRows.length,
    request_date: todayISO,
    timezone: tz,
    doc_dates_sample: uniqueDates.slice(0, 12),
    message:
      todaysRows.length === 0 && rows.length > 0
        ? `Doc has ${rows.length} row(s) but none for ${todayISO} (${tz}). Dates in doc (sample): ${uniqueDates.slice(0, 8).join(', ') || '—'}.`
        : undefined,
  };
}
