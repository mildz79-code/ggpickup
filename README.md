# GG Pickup

Driver app for Color Fashion greige goods pickups. Mobile-first, static HTML app backed by a local FastAPI service.

**Live:** https://gg.colorfashiondnf.com

## Stack

- Static HTML/JS (no build)
- Hosted on Netlify (`colorfashiondnf` project) / IIS on WEBSERVER
- FastAPI backend (`C:\ai\ggapi\main.py`) running on port 8001, proxied via IIS URL Rewrite to `/api/*`
- JWT auth (HS256, 12h expiry) — token stored in `localStorage`

## Files

| File | Purpose |
|---|---|
| `index.html` | Login page (driver picker + admin auto-login) |
| `app.html` | Main driver app (list, detail, camera, mark picked up) |
| `api.js` | Centralised API client — all `/api/*` calls go through here |
| `netlify.toml` | Netlify config + security headers |

## Database

Managed by the FastAPI backend (`C:\ai\ggapi\`):

- `greige_pickup_requests` — request list with status (`Pending` / `Picked Up` / `Cancelled`)
- `app_users` — role-based access (`admin`, `driver`), flagged active via `is_active`

## Adding a driver account

1. Add the user via the FastAPI admin API or directly in the database.
2. Set `role = 'driver'` and `is_active = true`.
3. Share the login URL + credentials with the driver.

## Testing-mode auth (current)

The app currently runs in **shared-password test mode**. `index.html` has a
hard-coded `TEST_DRIVER_PASSWORD` and `DRIVERS` list; the login page shows
those drivers as tap-to-sign-in buttons. A yellow banner flags this.

Before production:

1. Create per-driver passwords in the FastAPI user store.
2. Remove `TEST_DRIVER_PASSWORD`, `DRIVERS` constants from `index.html`.
3. Replace the driver picker with a standard email/password form.
4. Remove the `.test-banner` markup from `index.html` and `app.html`.
5. Rotate the seeded admin password (`daniel@colorfashiondnf.com`).

## Deploying

Netlify auto-deploys on push to `main`.

```bash
git add .
git commit -m "Update driver app"
git push origin main
```

The actual production copy served to users is `D:\Data\Web\gg\` on WEBSERVER
(served by IIS at gg.colorfashiondnf.com). Confirm with Daniel whether the
Netlify deploy or the IIS copy is the one users hit in production.

## Local testing

Just serve the files and point at a running FastAPI backend:

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000 — you'll need `/api/*` proxied to the FastAPI
service (or run FastAPI with CORS enabled for localhost).

## Google Docs → Today's pickup sync

This repo includes Netlify Functions:

- `POST /.netlify/functions/sync-pickups-from-doc` — manual trigger (wires through to `lib/google-doc-sync.js`)
- `GET /.netlify/functions/pickup-sync-config` — returns `{ timezone, todayISO }` for date alignment
- `pickup-sync-hourly` — scheduled (hourly) sync from Google Sheet to the backend

The sync reads rows from a configured Google Sheet and replaces **today's**
rows via the FastAPI `POST /api/pickup-requests/sync-day` endpoint. **Today**
uses the timezone `PICKUP_DATE_TIMEZONE` (default `America/New_York`).

### Required Netlify environment variables

- `GOOGLE_DOC_ID` (Sheet ID from URL)
- `GOOGLE_SERVICE_ACCOUNT_EMAIL`
- `GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY` (paste full key; escaped `\n` is handled)
- `GG_API_URL` (e.g. `https://gg.colorfashiondnf.com/api`)
- `GG_API_TOKEN` (service token for the FastAPI backend)

Optional:

- `PICKUP_DATE_TIMEZONE` — IANA zone for "today" (default `America/New_York`).

Also share the Google Sheet with the service account email (Viewer).

### App usage

Admins can click the **Sync Doc** button in `app.html` to run sync on demand.
The button is hidden for non-admin users.

## Notes

- The camera uses `<input type="file" capture="environment">`, which opens the rear camera on phones and falls back to file picker on desktop.
- Geolocation is requested at mark-picked-up; it's optional and fails silently.
