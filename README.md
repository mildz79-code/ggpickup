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

## Notes

- Uses Supabase publishable (anon) key — safe to ship in the client. Server-side is protected by RLS.
- The camera uses `<input type="file" capture="environment">`, which opens the rear camera on phones and falls back to file picker on desktop.
- Geolocation is requested at upload + mark-picked-up; it's optional and fails silently.
