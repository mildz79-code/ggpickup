# GG Pickup

Driver app for Color Fashion greige goods pickups. Mobile-first, static HTML +
ES modules — no build step.

**Live:** https://gg.colorfashiondnf.com

## Stack

- Static HTML/JS (no build)
- Served in production by **IIS** on the WEBSERVER at `D:\Data\Web\gg\`
- Backed by a **local FastAPI** service at `C:\ai\ggapi\main.py` on port 8001
- IIS URL Rewrite + ARR proxies `/api/*` and `/photos/*` to `http://localhost:8001`
- The browser only ever talks to same-origin `/api/...` — never directly to `:8001`
- Netlify still auto-deploys this repo as a mirror/preview

## Files

| File | Purpose |
|---|---|
| `index.html` | Login / driver picker |
| `app.html` | Main driver app (list, detail, camera, mark picked up) |
| `api.js` | Shared API client for the local FastAPI backend |
| `netlify.toml` | Netlify mirror config + security headers |

## Auth

- JWT (HS256, 12h expiry) issued by `POST /api/auth/login`
- Token stored in `localStorage` (`gg_token`), sent as `Authorization: Bearer <token>`
- `/api/auth/me` returns the current user (role, is_active, etc.)
- On any `401`, the client clears the session and reloads to the login screen

### Current test-mode auth

- `index.html` auto-signs-in `daniel@colorfashiondnf.com` (admin) on cold boot
- Drivers pick a tile; the tile POSTs `/api/auth/login` with a shared test password
- `sessionStorage.skipAutoLogin = '1'` prevents auto-login loops after explicit sign-out

Before production:

1. Replace the shared driver password with per-driver credentials.
2. Drop the test banner and the auto-login block.
3. Rotate `daniel@colorfashiondnf.com`'s admin password.

## Adding a driver account

Drivers live in the FastAPI backend's user table. Add one via the API / admin
tooling in `C:\ai\ggapi\`, then either share per-driver credentials or (for
test mode) use the shared `TEST_DRIVER_PASSWORD` in `index.html`.

## Deploying

Netlify auto-deploys on push to `main`, but the **real** production target is
`D:\Data\Web\gg\` on WEBSERVER (served by IIS). Copy the repo contents there.

```bash
git add .
git commit -m "Update driver app"
git push origin main
```

## Local testing

Just serve the files:

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000. Note that `/api/*` calls will 404 unless you
proxy them to a running FastAPI on :8001, or point `api.js` at a running
backend yourself.

## API surface (talks to local FastAPI via `/api/*`)

See `api.js` for the full client. The key endpoints:

- `POST /api/auth/login` → `{ token | access_token, user }`
- `GET  /api/auth/me` → current user
- `GET  /api/pickup-requests?request_date=YYYY-MM-DD&status=…`
- `POST /api/pickup-requests` — create
- `PATCH /api/pickup-requests/{id}` — update
- `PATCH /api/pickup-requests/{id}/pickup` — mark picked up (with optional `{lat,lng}`)
- `POST /api/pickup-requests/{id}/photos` (multipart) — upload pickup photo
- `POST /api/sync` — admin-only Google Sheet → DB sync
- `GET  /api/health` — used by the client as a boot-time proxy smoke test

## Notes

- The camera uses `<input type="file" capture="environment">`, which opens the
  rear camera on phones and falls back to file picker on desktop.
- Geolocation is requested at upload + mark-picked-up; it's optional and fails
  silently.
- The browser never needs to know the backend URL — same-origin `/api/*` is
  rewritten by IIS (`web.config`) to `http://localhost:8001`.
