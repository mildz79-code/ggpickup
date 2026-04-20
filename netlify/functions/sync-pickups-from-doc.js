import { google } from 'googleapis';

const REQUIRED_ENV = [
  'GOOGLE_DOC_ID',
  'GOOGLE_SERVICE_ACCOUNT_EMAIL',
  'GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY',
  'SUPABASE_URL',
  'SUPABASE_SERVICE_ROLE_KEY',
];

function json(statusCode, body) {
  return {
    statusCode,
    headers: { 'content-type': 'application/json; charset=utf-8' },
    body: JSON.stringify(body),
  };
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

function readDate(input) {
  const value = String(input || '').trim();
  if (!value) return null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;

  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
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
  const doc = await docs.documents.get({ documentId: process.env.GOOGLE_DOC_ID });
  const bodyContent = doc?.data?.body?.content || [];
  const rows = [];
  for (const block of bodyContent) {
    const table = block?.table;
    if (!table?.tableRows?.length) continue;
    rows.push(...tableRowsToRequests(table.tableRows));
  }
  return rows;
}

async function upsertRows(rows) {
  const today = new Date();
  const todayISO = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  const todaysRows = rows.filter((r) => r.request_date === todayISO);

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

export const handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return json(405, { error: 'Method not allowed. Use POST.' });
  }

  const missing = REQUIRED_ENV.filter((k) => !process.env[k]);
  if (missing.length) {
    return json(500, { error: `Missing required environment variables: ${missing.join(', ')}` });
  }

  try {
    const rows = await fetchDocRows();
    const today = new Date();
    const todayISO = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
    const todaysRows = rows.filter((r) => r.request_date === todayISO);

    if (!rows.length) {
      return json(200, { ok: true, synced: 0, message: 'No valid rows found in Google Doc tables.' });
    }
    const result = await upsertRows(rows);
    return json(200, {
      ok: true,
      synced: Array.isArray(result) ? result.length : rows.length,
      scanned: rows.length,
      scanned_today: todaysRows.length,
      request_date: todayISO,
    });
  } catch (error) {
    console.error('sync-pickups-from-doc error:', error);
    return json(500, { error: error?.message || 'Sync failed' });
  }
};
