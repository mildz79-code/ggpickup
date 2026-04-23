// api.js — GG Pickup local API client
// All frontend code must go through here. Never call fetch('/api/...') directly elsewhere.

const TOKEN_KEY = 'gg_token';
const USER_KEY  = 'gg_user';

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const getUser  = () => {
  try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); }
  catch { return null; }
};
export const setSession = (token, user) => {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
};
export const clearSession = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

async function request(path, { method = 'GET', body, headers = {}, isForm = false } = {}) {
  const token = getToken();
  const opts = {
    method,
    headers: {
      ...(isForm ? {} : { 'Content-Type': 'application/json' }),
      ...(token  ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  };
  if (body !== undefined) opts.body = isForm ? body : JSON.stringify(body);

  const res = await fetch(`/api${path}`, opts);

  if (res.status === 401) {
    clearSession();
    // Let the app decide how to react (redirect, show login, etc.)
    window.dispatchEvent(new CustomEvent('gg:unauthorized'));
    throw new Error('Unauthorized');
  }

  const isJson = (res.headers.get('content-type') || '').includes('application/json');
  const payload = isJson ? await res.json().catch(() => null) : await res.text();

  if (!res.ok) {
    const msg = (payload && payload.detail) || payload || `HTTP ${res.status}`;
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  return payload;
}

// ---------- Auth ----------
export const api = {
  health:        ()                   => request('/health'),
  login:         (email, password)    => request('/auth/login', { method: 'POST', body: { email, password } }),
  me:            ()                   => request('/auth/me'),

  // Pickup requests
  listRequests:  (params = {})        => {
    const qs = new URLSearchParams(params).toString();
    return request(`/pickup-requests${qs ? `?${qs}` : ''}`);
  },
  getRequest:    (id)                 => request(`/pickup-requests/${id}`),
  createRequest: (data)               => request('/pickup-requests', { method: 'POST', body: data }),
  updateRequest: (id, patch)          => request(`/pickup-requests/${id}`, { method: 'PATCH', body: patch }),
  deleteRequest: (id)                 => request(`/pickup-requests/${id}`, { method: 'DELETE' }),
  markPickedUp:  (id, { lat, lng })   => request(`/pickup-requests/${id}/pickup`, { method: 'PATCH', body: { lat, lng } }),

  // Photos (multipart)
  uploadPhoto:   (id, file, gps = {}) => {
    const fd = new FormData();
    fd.append('file', file);
    if (gps.lat != null) fd.append('lat', gps.lat);
    if (gps.lng != null) fd.append('lng', gps.lng);
    return request(`/pickup-requests/${id}/photos`, { method: 'POST', body: fd, isForm: true });
  },
  listPhotos:    (id)                 => request(`/pickup-requests/${id}/photos`),

  // Lookup + admin
  listUsers:     ()                   => request('/users'),
  listLocations: ()                   => request('/locations'),
  syncFromSheet: ()                   => request('/sync',  { method: 'POST' }),
  scanImage:     (file)               => {
    const fd = new FormData();
    fd.append('file', file);
    return request('/scan', { method: 'POST', body: fd, isForm: true });
  },
};

// Quick smoke test so we can confirm the proxy is alive.
api.health()
  .then(r => console.log('[gg-pickup] /api/health OK:', r))
  .catch(e => console.warn('[gg-pickup] /api/health failed — check IIS proxy + FastAPI on :8001:', e.message));
