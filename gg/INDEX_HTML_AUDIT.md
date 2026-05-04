Phase: 1 | File: `gg/INDEX_HTML_AUDIT.md` | Risk: none

Audit of production-imported `gg/index.html` (verbatim save). Cross-checked with `docs/PHASES.md` Phase 1, `.cursor/rules/20-shipping-web.mdc` (Mockup 1 / shared-auth notes), and `ggapi/routers/*.py`.

---

## API contract

All HTTP calls use `fetch()`. There are **no** `XMLHttpRequest` usages.

Base URL: `const API_URL = 'https://gg.colorfashiondnf.com/api'` — requests use `API_URL + path` (browser sees `/api/...`; IIS strips `/api` before FastAPI).

### 1. `POST /auth/login`

- **Trigger:** `doLogin()` — `#loginBtn` click, or Enter in `#loginPassword`.
- **Uses:** Raw `fetch` (not the `api()` helper), so **401 does not** run `doLogout()` (only invalid-login handling via `res.ok`).
- **Headers:** `Content-Type: application/json`
- **Body:** `{ email: string, password: string }`
- **Expected response (success):** JSON with `access_token` (string) and `user` (object). Code reads `data.access_token`, `data.user` — matches repo `ggapi/routers/auth.py` (`access_token`, `user: { id, email, full_name, role }`).
- **Expected response (error):** JSON with `detail` (shown in `#loginError`), or network failure → generic “Cannot reach server…”.

### 2. `GET /pickup-requests?date={YYYY-MM-DD}` and optional `&status=Pending`

- **Trigger:** `loadRequests()` — `initApp()`, filter tabs that stay in daily mode (Today / Yesterday / dayBefore / Pending / All), after successful pick/create/status flows, `#refreshBtn` click, and the 90s auto-refresh when `currentMode === 'daily'` and `currentDateFilter === 'today'`.
- **Uses:** `api('GET', url)` → Bearer token when present.
- **Expected response:** JSON array of pickup rows. Each row is used as objects with at least: `id`, `knitter`, `customer`, `lot_number`, `qty`, `status` (`Pending` | `Picked Up` | `Cancelled`, etc.), `request_date`, optional `notes`, optional `picked_up_at`.
- **Note:** `docs/PHASES.md` Phase 1 example shows `date=today`; this frontend sends an **ISO calendar date** (`DATE_MAP.*`), not the literal string `today`.

### 3. `GET /pickup-requests?status=Picked+Up`

- **Trigger:** `loadWeekRequests(startISO, endISO)` — choosing **Picked Up** filter (initial week load) or a **week tab** in `#weekBar`.
- **Uses:** `api('GET', ...)`.
- **Expected response:** JSON array; client filters to `request_date >= startISO && request_date <= endISO`.

### 4. `PATCH /pickup-requests/{id}/pickup`

- **Trigger:** `markPickedUp(id)` — `.pick-btn` click on a row, or **Mark as Picked Up** in detail modal (`window._markPicked`). Prefaced by `confirm(...)`. Optionally uses `navigator.geolocation.getCurrentPosition` (5s timeout); sends coords or `null`.
- **Uses:** `api('PATCH', ...)`.
- **Body:** `{ lat: number | null, lng: number | null }`
- **Expected response:** Success: `res.ok`; code does not assume a specific JSON shape beyond non-OK → `toast` with `detail`. Repo returns `{ success: true }`.

### 5. `PATCH /pickup-requests/{id}`

- **Trigger:** `updateStatus(id, newStatus)` — **Cancel Pickup** (`window._cancelPickup` → `Cancelled`), **Undo** (`window._undoPickup` → `Pending`). Prefaced by `confirm(...)`.
- **Body:** `{ status: newStatus }`; if `newStatus === 'Pending'`, client also sends `picked_up_at`, `picked_up_by`, `lat`, `lng` set to `null`.
- **Expected response:** Non-OK → toast with `detail`. Repo returns `{ success: true }` when allowed fields update.

**Repo mismatch (important):** `update_request` in `ggapi/routers/pickup_requests.py` only allows `knitter`, `customer`, `lot_number`, `qty`, `status`, `notes`, `request_date`. Extra keys sent on undo are **ignored**. Also this route is guarded by **`admin_only`** — non-admin users calling Cancel/Undo may receive **403**, while the UI shows those buttons for any user who can open the modal.

### 6. `POST /pickup-requests`

- **Trigger:** `#submitNewBtn` click after validation (`knitter` required).
- **Uses:** `api('POST', ...)`.
- **Body:** `{ request_date: DATE_MAP.today, knitter, customer, lot_number | null, qty: number, notes | null }` (knitter/customer uppercased by client).
- **Expected response:** JSON with `id` on success (`toast` shows `Pickup #${data.id} created`). Repo returns `{ id, status: 'Pending' }`. Route is **admin-only** in repo; UI only shows `#newBtn` when `appUser.role === 'admin'`.

---

## sessionStorage / localStorage usage

- **`sessionStorage`:** **None** — no reads or writes.

- **`localStorage`**
  - **`gg_token` (read/write/clear):** JWT bearer string. Read on load; set on successful login; removed in `doLogout()`.
  - **`gg_user` (read/write/clear):** JSON-serialized user object from login response. Parsed with `JSON.parse(...|| 'null')`. Set on login; removed on logout. Used for `role === 'admin'` (show **+ New Pickup**).

---

## Hardcoded credentials

- **No driver passwords, API keys, or JWT secrets** appear in the HTML/JS.
- Login is **email + password** fields only; no tile/grid with embedded passwords (see Phase 1 gap below).

---

## Auth flow

### Tile login (driver grid)

- **Not implemented** in this file. Entry is a single **email/password** form (`#loginScreen`). Any “tile login” described in `docs/PHASES.md` Phase 1 is **absent** here.

### Email/password login (drivers and admins)

1. User submits `#loginEmail` + `#loginPassword` (button or Enter in password field).
2. `POST .../auth/login` with JSON body.
3. On success: store `gg_token`, `gg_user`, hide `#loginScreen`, show `#appShell`, call `initApp()`.
4. On failure: show `data.detail` or network error in `#loginError`; token not set.

### Auto-login

- If both `gg_token` and `gg_user` parse truthfully on load (`token && appUser`), skip the form and call `initApp()`.

### Token expiry / 401

- Any request through **`api()`** that receives **`res.status === 401`** calls **`doLogout()`** (clears storage, hides app, shows login), then throws **`Error('Session expired')`** — caught by callers and shown in table empty state or toast depending on path.
- **`doLogin`** does **not** use `api()`, so a 401 on bad credentials does **not** clear an old token via this path (normally login runs with empty inputs after logout anyway).

### Role behavior

- **`admin`:** `#newBtn` visible — creates pickups via `POST /pickup-requests`.
- **Non-admin:** `#newBtn` hidden; can still use list, pick-up PATCH, and modal actions that call PATCH by id (subject to backend `admin_only` on PATCH id — see mismatch above).

---

## Design tokens vs Mockup 1 spec

Spec source: `.cursor/rules/20-shipping-web.mdc` (GG Pickup Mockup 1 alignment: light background, **Fraunces** headers, **Inter** body, **JetBrains Mono** codes, **rust accent `#b8391a`**).

| Spec item | Mockup 1 | Actual in `index.html` | Verdict |
|-----------|----------|-------------------------|---------|
| Page background | `#f7f5f0` cream | `body { ... background: #f8f9fa; }`; meta `theme-color` `#f8f9fa` | **Drift** — cooler gray, not cream. |
| Accent | `#b8391a` rust | Primary UI accent `#2563eb`, hover `#1d4ed8`; many indigo/purple UI accents (`#1e3a8a`, `#3730a3`, `#c7d2fe`, etc.) | **Drift** — blue/indigo theme vs rust. |
| Headers font | Fraunces serif | `.topbar-left h1`, headings use inherited `body` font `'Segoe UI', system-ui, sans-serif` | **Drift**. |
| Body font | Inter | Same as above — Segoe UI / system-ui | **Drift**. |
| Codes / lot # | JetBrains Mono | `.lot-cell { font-family: Consolas, monospace; }` | **Drift** — Consolas, not JetBrains Mono. |
| Knitter group chevron | Accent (`#b8391a`) | `.expand-toggle { color: #888; }`, `.expand-toggle.open { color: #2563eb; }` | **Drift** — gray/blue, not rust. |
| PENDING badge yellow | (yellow) | `.status-Pending { background: #fef3c7; color: #92400e; }` | **Aligned** (amber/yellow family). |
| PICKED UP green | (green) | `.status-PickedUp { background: #d1fae5; color: #065f46; }` | **Aligned** (green family). |

---

## Buttons and modals

| Element | What it does | Handler location |
|---------|----------------|------------------|
| `#loginBtn` | Submit login | `addEventListener('click', doLogin)` |
| `#loginPassword` | Enter submits | `keydown` → `doLogin` if Enter |
| `#newBtn` | Open new pickup modal, reset fields | `click` listener |
| `#refreshBtn` | Calls `loadRequests()` only | `click` → `loadRequests` (**note:** not `loadWeekRequests` — weekly “Picked Up” view may jump back to daily fetch behavior) |
| `#logoutBtn` | Confirm then `doLogout()` | `click` |
| `.filter-tab` | Change date/status/week mode; load data | `click` on each tab |
| `.week-tab` (dynamic) | Change week range; `loadWeekRequests` | Attached in `renderWeekBar()` |
| `.expand-toggle` | Toggle knitter group expand | `attachEvents()` |
| `.parent-row` | Toggle expand (not when clicking toggle button) | `attachEvents()` |
| `tr[data-id]` | Open detail modal | `attachEvents()` → `openDetail` |
| `.pick-btn` | `markPickedUp` without opening detail | `attachEvents()` |
| `#closeDetail` | Close detail overlay | `click` |
| `#detailOverlay` | Click backdrop (target id) closes | delegated `click` |
| Detail buttons | Inline `onclick`: `_markPicked`, `_cancelPickup`, `_undoPickup`, Close | `openDetail()` HTML string |
| `#closeNew`, `#cancelNewBtn` | Close new modal | `click` |
| `#newOverlay` | Click backdrop closes | delegated |
| `#submitNewBtn` | `POST /pickup-requests` | `async click` handler |

**Modals:** `#detailOverlay` + `#detailBody` (dynamic content); `#newOverlay` (static form).

---

## TODO comments and known issues

- Searched for `TODO`, `FIXME`, `XXX`, `HACK` in `gg/index.html`: **no matches**.
- **Comment only:** Config notes IIS proxy URL variant (`// After IIS proxy is set up...`) — not a code TODO marker.

---

## API endpoints used vs implemented in repo

### Frontend calls (via `API_URL`)

| Method | Path (after `/api`) | In repo |
|--------|---------------------|---------|
| POST | `/auth/login` | Yes — `ggapi/routers/auth.py` |
| GET | `/pickup-requests` (query variants) | Yes — `pickup_requests.py` `list_requests` |
| PATCH | `/pickup-requests/{id}/pickup` | Yes |
| PATCH | `/pickup-requests/{id}` | Yes (**admin_only**) |
| POST | `/pickup-requests` | Yes (**admin_only**) |

### Implemented in repo but **not** called by this page

From `ggapi/main.py` router inventory:

- `GET /auth/me` — auth router
- `GET /pickup-requests/{id}` — single row
- `DELETE /pickup-requests/{id}`
- `POST /pickup-requests/{id}/photos`, `GET /pickup-requests/{id}/photos`
- `/users`, `/locations`, `/sync`, `/scan`, `/shipping/*`, `GET /health`

### Behavioral gaps vs backend

- Cancel / Undo use **`PATCH /pickup-requests/{id}`** — **admin-only** in repo; UI does not gate those buttons by role.
- Undo sends nulls for pickup metadata fields **not** whitelisted by repo PATCH handler — **clearing `picked_up_*` / lat/lng on undo may require backend change** if that behavior is required.

---

## Missing features per Phase 1 spec in PHASES.md

From `docs/PHASES.md` **Phase 1 — GG Pickup driver app**, compared to this `index.html`:

| Phase 1 item | Present? |
|--------------|------------|
| **1.1** Endpoint checklist / phone test | Not verifiable from static HTML (operational task). |
| **1.2** Mockup 1 design **with tile login** (drivers grid + “Sign in as admin”), **test mode banner** | **Missing** — email/password screen only; no test banner called out in markup. |
| **1.3** Regroup flat `/pickup-requests` by knitter | **Present** — `renderTable()` groups by `knitter`. |
| **1.4** Row tap → Mark Picked Up → **geolocation + camera (`capture`) + POST photos** in sequence | **Partial** — geolocation yes for pick; **no** `<input type="file" capture>`, **no** `POST .../photos`. |
| **1.5** Token in **`sessionStorage`** keys **`cf_token`** / **`cf_user`** | **Missing** — uses **`localStorage`** `gg_token` / `gg_user` instead. |
| **1.6** Admin **“Sync from Sheet”** → `POST /api/sync` | **Missing** — no sync button or `/sync` call. |
| **1.7** Zero Supabase traffic | No Supabase URLs in source — **OK** for this file. |
| **1.8** E2E with photo on disk | Depends on 1.4 — **not supported** by current JS. |

Additional Phase 1 bullets from the **Tasks** prose: **date header** — partially met via `#dateLabel` (formatted date); **Total Lots footer** — `#tableFoot` / `#totalQty` present.

---

*Generated as part of importing production HTML into the repo; no edits were made to `gg/index.html` beyond storing the pasted source.*
