/**
 * api.js — FastAPI client for GG Pickup
 *
 * All calls go to /api/* on the same origin (IIS reverse-proxies to FastAPI :8001).
 * Auth: JWT stored in sessionStorage. Call api.login() to obtain and store a token.
 * The token is attached as Bearer on every request.
 */

const BASE = '/api';
const TOKEN_KEY = 'ggpickup-jwt';

export function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(t) {
  if (t) sessionStorage.setItem(TOKEN_KEY, t);
  else sessionStorage.removeItem(TOKEN_KEY);
}

export function getUser() {
  const t = getToken();
  if (!t) return null;
  try {
    const payload = JSON.parse(atob(t.split('.')[1]));
    // payload shape from FastAPI backend: { sub, role, exp, ... }
    return payload;
  } catch {
    return null;
  }
}

export function isAdmin() {
  return getUser()?.role === 'admin';
}

/**
 * Core fetch wrapper.
 * Options:
 *   method  – HTTP verb (default GET)
 *   body    – plain object → JSON; or FormData → multipart (set isForm:true)
 *   isForm  – when true, body is sent as-is (FormData), no Content-Type header
 */
async function request(path, opts = {}) {
  const { method = 'GET', body, isForm = false } = opts;

  const headers = {};
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  if (body && !isForm) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(BASE + path, {
    method,
    headers,
    body: body
      ? isForm
        ? body           // FormData — let browser set multipart boundary
        : JSON.stringify(body)
      : undefined,
  });

  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      msg = j.detail || j.message || j.error || msg;
    } catch { /* ignore */ }
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }

  return res.json();
}

/** POST /api/auth/login — returns { access_token, token_type, user } */
export async function login(username, password) {
  // FastAPI OAuth2PasswordRequestForm expects form-encoded body
  const fd = new FormData();
  fd.append('username', username);
  fd.append('password', password);
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    body: fd,
  });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try { const j = await res.json(); msg = j.detail || msg; } catch { /* ignore */ }
    throw new Error(msg);
  }
  const data = await res.json();
  // Handle both {access_token, user} and {token, user} shapes
  const tok = data.access_token || data.token;
  if (tok) setToken(tok);
  return data;
}

export function logout() {
  setToken(null);
}

export const api = {
  /** GET /api/health */
  health: () => request('/health'),

  /** GET /api/pickup-requests?date=YYYY-MM-DD */
  getPickupRequests: (date) => request(`/pickup-requests${date ? '?date=' + encodeURIComponent(date) : ''}`),

  /** POST /api/pickup-requests */
  createPickupRequest: (body) => request('/pickup-requests', { method: 'POST', body }),

  /** PATCH /api/pickup-requests/:id  */
  updatePickupRequest: (id, body) => request(`/pickup-requests/${id}`, { method: 'PATCH', body }),

  /**
   * POST /api/scan
   * Upload an image file for OCR lot# matching.
   * Returns { ocr_text, candidates, saved_path, matches, status, attached_to? }
   */
  scanImage: (file) => {
    const fd = new FormData();
    fd.append('file', file);
    return request('/scan', { method: 'POST', body: fd, isForm: true });
  },

  /**
   * POST /api/scan/attach
   * Attach an already-saved scan file to a specific request.
   * saved_path: the /scans/... path returned by scanImage
   * mark_picked_up: also update request status to 'Picked Up'
   */
  attachScan: (saved_path, request_id, mark_picked_up = true) =>
    request('/scan/attach', {
      method: 'POST',
      body: { saved_path, request_id, mark_picked_up },
    }),
};
