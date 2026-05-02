// assets/api.js — fetch wrapper for the shipping-web frontend.
//
// All paths below include the /api/ prefix because that's what IIS expects.
// IIS reverse-proxies /api/* to localhost:8001, STRIPPING the /api prefix,
// so the FastAPI route handler sees /shipping/today (no /api).
//
// Never hardcode http://localhost:8001 here — relative URLs work both via
// IIS in production and in dev when you proxy through a local server.

const TOKEN_KEY = "cf_token";

function headers(extra = {}) {
  const h = { "Accept": "application/json", ...extra };
  const tok = sessionStorage.getItem(TOKEN_KEY);
  if (tok) h["Authorization"] = `Bearer ${tok}`;
  return h;
}

async function handle(res) {
  if (res.status === 401) {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem("cf_user");
    location.href = "https://gg.colorfashiondnf.com/index.html";
    throw new Error("Session expired");
  }
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try { const body = await res.json(); msg = body.detail || body.message || msg; } catch {}
    throw new Error(msg);
  }
  if (res.status === 204) return null;
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}

export async function apiGet(path) {
  return handle(await fetch(path, { headers: headers() }));
}
export async function apiPost(path, body) {
  return handle(await fetch(path, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json" }),
    body: JSON.stringify(body ?? {}),
  }));
}
export async function apiPatch(path, body) {
  return handle(await fetch(path, {
    method: "PATCH",
    headers: headers({ "Content-Type": "application/json" }),
    body: JSON.stringify(body ?? {}),
  }));
}
export async function apiDelete(path) {
  return handle(await fetch(path, { method: "DELETE", headers: headers() }));
}

// Domain-specific wrappers. Note every path starts with /api/.
export const shipping = {
  today:          ()         => apiGet("/api/shipping/today"),
  day:            (iso)      => apiGet(`/api/shipping/day/${iso}`),
  createDelivery: (body)     => apiPost("/api/shipping/deliveries", body),
  updateDelivery: (id, body) => apiPatch(`/api/shipping/deliveries/${id}`, body),
  addStop:        (body)     => apiPost("/api/shipping/stops", body),
  reorderStops:   (list)     => apiPost("/api/shipping/stops/reorder", list),
  removeStop:     (id)       => apiDelete(`/api/shipping/stops/${id}`),
};

// Convenience: existing GG Pickup endpoints if shipping-web ever needs them.
export const pickups = {
  list:    (params) => apiGet("/api/pickup-requests" + (params ? `?${new URLSearchParams(params)}` : "")),
  get:     (id)     => apiGet(`/api/pickup-requests/${id}`),
};
