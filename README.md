# GG Pickup

Driver app for Color Fashion greige goods pickups. Mobile-first, static, Supabase-backed.

**Live:** https://gg.colorfashiondnf.com

## Stack

- Static HTML/JS (no build)
- Hosted on Netlify (`colorfashiondnf` project)
- Supabase for auth + data + photo storage (Color Fashion project)

## Files

| File | Purpose |
|---|---|
| `index.html` | Login page |
| `app.html` | Main driver app (list, detail, camera, mark picked up) |
| `supabase-client.js` | Shared client + session helper |
| `netlify.toml` | Netlify config + security headers |

## Database

Lives in the Color Fashion Supabase project (`cgsmzkafagnmsuzzkfnv`):

- `greige_pickup_requests` — request list with status (`Pending` / `Picked Up` / `Cancelled`)
- `greige_pickup_photos` — photo metadata, FK to request
- `app_users` — role-based access (`admin`, `user`, `driver`), flagged active via `is_active`
- `ship_to_locations` — seeded customer addresses used for the new-pickup typeahead
- Storage bucket `greige-pickup-photos` (private, 10 MB limit, images only)

## Adding a driver account

1. Create the auth user in Supabase → Authentication → Users (email + password).
2. Insert into `app_users` with `role = 'driver'` and `is_active = true`. Example:

   ```sql
   INSERT INTO app_users (id, email, full_name, role, is_active)
   VALUES ('<auth-user-uuid>', 'driver@example.com', 'Driver Name', 'driver', true);
   ```

3. Share the login URL + credentials with the driver.

## Testing-mode auth (current)

The app currently runs in **shared-password test mode**. `supabase-client.js`
exports a hard-coded `TEST_DRIVER_PASSWORD` and a `DRIVERS` list; the login
page shows those drivers as tap-to-sign-in buttons. A yellow banner on every
page flags this.

Before production:

1. Create per-driver passwords in Supabase Authentication.
2. Remove `TEST_DRIVER_PASSWORD`, `DRIVERS`, and `signInAsDriver()` from
   `supabase-client.js`.
3. Replace the driver picker in `index.html` with a standard email/password
   form (the admin panel already shows the pattern).
4. Remove the `.test-banner` markup from `index.html` and `app.html`.
5. Rotate the seeded admin password (`daniel@colorfashiondnf.com`).

## Deploying

Netlify auto-deploys on push to `main`.

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

Then open http://localhost:8000.

## Google Docs -> Today's pickup sync

This repo now includes Netlify Functions:

- `POST /.netlify/functions/sync-pickups-from-doc` — manual sync (admin **Sync Doc** button)
- `GET /.netlify/functions/pickup-sync-config` — returns `{ timezone, todayISO }` so the app uses the same calendar day as the server
- `pickup-sync-hourly` — scheduled sync (hourly) so Supabase stays aligned with the Google Doc after deploy

The sync reads tables from a configured Google Doc and replaces **today's**
rows in `greige_pickup_requests` with today's rows from the doc. **Today** uses
the timezone `PICKUP_DATE_TIMEZONE` (default `America/New_York`) so Netlify
(UTC) and your doc dates stay aligned.

### Expected Google Doc table headers

At minimum, include these columns in a table header row:

- `Date`
- `Knitter`

Optional columns:

- `Customer`
- `Qty` / `Quantity` / `Lots`
- `Lot` / `Lot #` / `Lot Number`
- `Status`
- `Notes`

Rows with invalid/missing date or knitter are skipped.

### Required Netlify environment variables

- `GOOGLE_DOC_ID` (Doc ID from URL)
- `GOOGLE_SERVICE_ACCOUNT_EMAIL`
- `GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY` (paste full key; escaped `\n` is handled)
- `SUPABASE_URL` (e.g. `https://<project>.supabase.co`)
- `SUPABASE_SERVICE_ROLE_KEY` (server key; never expose in client code)

Optional:

- `PICKUP_DATE_TIMEZONE` — IANA zone for “today” (default `America/New_York`). Set to match where your doc dates are authored (e.g. `America/Los_Angeles`).

Also share the Google Doc with the service account email (Viewer).

### App usage

Admins can click the **Sync Doc** button in `app.html` to run sync on demand.
The button is hidden for non-admin users.

## Notes

- Uses Supabase publishable (anon) key — safe to ship in the client. Server-side is protected by RLS.
- The camera uses `<input type="file" capture="environment">`, which opens the rear camera on phones and falls back to file picker on desktop.
- Geolocation is requested at upload + mark-picked-up; it's optional and fails silently.
