/**
 * Shared Google Sheet → FastAPI sync for greige_pickup_requests.
 * Reads from a Google Spreadsheet via the Sheets API.
 */

import { google } from 'googleapis';

/**
 * Required env vars — needs at least one of GOOGLE_SHEET_ID / GOOGLE_DOC_ID.
 */
const REQUIRED_ENV_ALWAYS = [
  'GOOGLE_SERVICE_ACCOUNT_EMAIL',
  'GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY',
  'GG_API_URL',
  'GG_API_TOKEN',
];

/** IANA timezone for "today". Default matches typical US ops. */
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
  const missing = REQUIRED_ENV_ALWAYS.filter((k) => !process.env[k]);
  if (!process.env.GOOGLE_SHEET_ID && !process.env.GOOGLE_DOC_ID) {
    missing.push('GOOGLE_SHEET_ID (or GOOGLE_DOC_ID)');
  }
  return missing;
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

/**
 * Parse date cells (M/D/YYYY, MM/DD/YYYY, ISO, long-form like "Monday, April 20, 2026").
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
  const normalized = headers.map((h) =>
    String(h || '').toLowerCase().replace(/[#]/g, '').replace(/\s+/g, ' ').trim()
  );
  return normalized.findIndex((h) =>
    candidates.some((c) => h === c || h.includes(c))
  );
}

/**
 * Parse raw 2D array from Google Sheets into pickup request objects.
 * Handles the "TODAY" tab format:
 *   - Date in a title row (can be in any column, e.g. col C)
 *   - Header row: KNITTER | CUSTOMER | (blank=qty) | LOT NUMBER
 *   - Knitter names carried forward for grouped rows
 *   - Summary rows like "TOTAL LOTS =" are skipped
 *   - Knitter-only rows with no customer/qty are skipped (0 pickups that day)
 */
function parseSheetRows(rawRows) {
  if (!rawRows || rawRows.length < 2) return [];

  // Find the header row — scan first 20 rows for one containing "knitter"
  let headerRowIdx = -1;
  for (let i = 0; i < Math.min(rawRows.length, 20); i++) {
    const row = rawRows[i] || [];
    const joined = row.map((v) => String(v || '').toLowerCase()).join(' ');
    if (
      joined.includes('knitter') &&
      (joined.includes('customer') || joined.includes('qty') || joined.includes('lot'))
    ) {
      headerRowIdx = i;
      break;
    }
  }

  if (headerRowIdx < 0) {
    console.log('[parseSheetRows] No header row found in first 20 rows');
    return [];
  }

  const headers = rawRows[headerRowIdx];
  const dateIdx = inferHeaderIndex(headers, ['date', 'request date']);
  const knitterIdx = inferHeaderIndex(headers, ['knitter']);
  const customerIdx = inferHeaderIndex(headers, ['customer', 'ship to']);
  let qtyIdx = inferHeaderIndex(headers, ['qty', 'quantity', 'lots']);
  const lotIdx = inferHeaderIndex(headers, ['lot', 'lot number']);
  const statusIdx = inferHeaderIndex(headers, ['status']);
  const notesIdx = inferHeaderIndex(headers, ['notes', 'remark']);

  if (knitterIdx < 0) {
    console.log('[parseSheetRows] No knitter column found');
    return [];
  }

  // Auto-detect unlabeled QTY column: find a column with blank/empty header
  // that has mostly numeric data in the rows below
  if (qtyIdx < 0) {
    const knownIdxs = [knitterIdx, customerIdx, lotIdx, statusIdx, notesIdx].filter(
      (i) => i >= 0
    );
    for (let col = 0; col < (headers.length || 0); col++) {
      if (knownIdxs.includes(col)) continue;
      const hdr = String(headers[col] || '').trim();
      if (hdr) continue; // skip columns that have a header label
      let numericCount = 0;
      let checked = 0;
      for (let r = headerRowIdx + 1; r < Math.min(rawRows.length, headerRowIdx + 15); r++) {
        const val = String(rawRows[r]?.[col] || '').trim();
        if (!val) continue;
        checked++;
        if (/^\d+$/.test(val)) numericCount++;
      }
      if (numericCount >= 2 && checked > 0 && numericCount >= checked * 0.5) {
        qtyIdx = col;
        console.log(
          `[parseSheetRows] Auto-detected QTY at col ${col} (${numericCount}/${checked} numeric)`
        );
        break;
      }
    }
  }

  console.log(
    `[parseSheetRows] Header row ${headerRowIdx}: date=${dateIdx} knitter=${knitterIdx} customer=${customerIdx} qty=${qtyIdx} lot=${lotIdx} status=${statusIdx}`
  );

  // If there is no date column, look for a date in ANY CELL of rows ABOVE the header
  let contextDate = null;
  if (dateIdx < 0) {
    for (let i = headerRowIdx - 1; i >= 0; i--) {
      const row = rawRows[i];
      if (!row || !row.length) continue;
      for (const cell of row) {
        const cellVal = String(cell || '').trim();
        if (cellVal) {
          const parsed = readDate(cellVal);
          if (parsed) {
            contextDate = parsed;
            break;
          }
        }
      }
      if (contextDate) break;
    }
    console.log(`[parseSheetRows] contextDate from title rows = ${contextDate}`);
  }

  const rows = [];
  let currentKnitter = null;

  for (let i = headerRowIdx + 1; i < rawRows.length; i++) {
    const row = rawRows[i];
    if (!row || !row.length) continue;

    const nonEmpty = row.filter((c) => String(c || '').trim());
    if (!nonEmpty.length) continue;

    // Skip summary/total rows
    const firstCell = String(row[0] || '').trim().toLowerCase();
    if (firstCell.includes('total')) continue;

    // Check if this row is a standalone date (between day sections)
    if (dateIdx < 0 && nonEmpty.length <= 2) {
      let foundDate = null;
      for (const cell of nonEmpty) {
        const cv = String(cell || '').trim();
        if (cv && !/^\d+$/.test(cv)) {
          const parsed = readDate(cv);
          if (parsed) {
            foundDate = parsed;
            break;
          }
        }
      }
      if (foundDate) {
        contextDate = foundDate;
        currentKnitter = null;
        continue;
      }
    }

    // Determine date
    let requestDate;
    if (dateIdx >= 0) {
      requestDate = readDate(String(row[dateIdx] || '').trim());
    } else {
      requestDate = contextDate;
    }

    // Determine knitter (carry forward)
    let knitter = knitterIdx >= 0 ? String(row[knitterIdx] || '').trim().toUpperCase() : '';
    if (knitter) {
      currentKnitter = knitter;
    } else {
      knitter = currentKnitter || '';
    }

    // Get customer
    const customer =
      customerIdx >= 0 ? String(row[customerIdx] || '').trim().toUpperCase() : '';

    // Get qty
    const qtyVal = qtyIdx >= 0 ? parseQty(row[qtyIdx]) : 0;

    // Skip rows with no customer AND no qty (knitter-only rows = 0 pickups that day)
    if (!customer && qtyVal === 0) continue;
    if (!requestDate) continue;

    rows.push({
      request_date: requestDate,
      knitter: knitter || 'UNKNOWN',
      customer: customer || null,
      qty: qtyVal,
      lot_number: lotIdx >= 0 ? String(row[lotIdx] || '').trim() || null : null,
      status: statusIdx >= 0 ? normalizeStatus(row[statusIdx]) : 'Pending',
      notes: notesIdx >= 0 ? String(row[notesIdx] || '').trim() || null : null,
    });
  }

  console.log(`[parseSheetRows] Parsed ${rows.length} data rows`);
  return rows;
}

/**
 * Fetch rows from Google Sheets.
 */
async function fetchDocRows() {
  const sheetId = process.env.GOOGLE_SHEET_ID || process.env.GOOGLE_DOC_ID;
  if (!sheetId) {
    throw new Error('Missing GOOGLE_SHEET_ID or GOOGLE_DOC_ID environment variable');
  }

  const client = new google.auth.JWT({
    email: process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL,
    key: process.env.GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY.replace(/\\n/g, '\n'),
    scopes: ['https://www.googleapis.com/auth/spreadsheets.readonly'],
  });
  await client.authorize();

  const sheets = google.sheets({ version: 'v4', auth: client });

  // Use configured tab name, or auto-detect the first sheet
  let tabName = process.env.GOOGLE_SHEET_TAB;
  if (!tabName) {
    const meta = await sheets.spreadsheets.get({
      spreadsheetId: sheetId,
      fields: 'sheets.properties.title',
    });
    const firstSheet = meta.data.sheets?.[0];
    tabName = firstSheet?.properties?.title || 'Sheet1';
    console.log(`[fetchDocRows] Auto-detected tab: "${tabName}"`);
  }

  const res = await sheets.spreadsheets.values.get({
    spreadsheetId: sheetId,
    range: `'${tabName}'!A:Z`,
    valueRenderOption: 'FORMATTED_VALUE',
  });

  const rawRows = res.data.values || [];
  console.log(`[fetchDocRows] Read ${rawRows.length} rows from "${tabName}"`);
  return parseSheetRows(rawRows);
}

async function replaceTodayViaApi(todaysRows, todayISO) {
  const baseUrl = process.env.GG_API_URL; // e.g. https://gg.colorfashiondnf.com/api
  const token   = process.env.GG_API_TOKEN;
  const headers = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };

  // Replace today's rows via the FastAPI bulk-sync endpoint
  const resp = await fetch(`${baseUrl}/pickup-requests/sync-day`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ request_date: todayISO, rows: todaysRows }),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`API sync-day failed (${resp.status}): ${text}`);
  }
  return resp.json();
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
    await replaceTodayViaApi([], todayISO);
    return {
      ok: true,
      synced: 0,
      scanned: 0,
      scanned_today: 0,
      request_date: todayISO,
      message: 'No valid rows found in Google Sheet; cleared today.',
    };
  }

  const result = await replaceTodayViaApi(todaysRows, todayISO);
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
        ? `Sheet has ${rows.length} row(s) but none for ${todayISO} (${tz}). Dates in sheet (sample): ${uniqueDates.slice(0, 8).join(', ') || '—'}.`
        : undefined,
  };
}
