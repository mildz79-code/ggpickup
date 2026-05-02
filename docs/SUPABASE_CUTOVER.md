# Supabase Cutover Checklist

Project being retired: **`cgsmzkafagnmsuzzkfnv`** (Color Fashion).
Separate project `mtxokbgpmkggolyfeehz` (Onetex) is **not** part of this cutover — leave it alone.

Do not run any of this until Phases 1–4 are stable in production for at least one week.

---

## Step 1 — Final data snapshot

Run the snapshot script to pull everything from Supabase into a timestamped SQL file for archival:

```bash
python scripts/supabase_snapshot.py --out scripts/snapshots/supabase_$(date +%Y%m%d).sql
```

The script (see `scripts/supabase_snapshot.py`) dumps:

- `app_users` (no password hashes — auth.users is Supabase-managed)
- `greige_pickup_requests` — full history
- `greige_pickup_photos` — metadata only (photo files are already in `C:\ggphotos\` on WEBSERVER)
- `ship_to_locations` — full
- `pl_line_items`, `pl_monthly` — P&L data, preserved as-is
- `meter_reading` — utility readings, preserved as-is

Verify row counts against live Supabase before proceeding:

```sql
-- Supabase:
SELECT (SELECT COUNT(*) FROM greige_pickup_requests)     AS pickups,
       (SELECT COUNT(*) FROM ship_to_locations)          AS locations,
       (SELECT COUNT(*) FROM greige_pickup_photos)       AS photos;

-- SQL Server ggpickup:
SELECT (SELECT COUNT(*) FROM greige_pickup_requests)     AS pickups,
       (SELECT COUNT(*) FROM ship_to_locations)          AS locations,
       (SELECT COUNT(*) FROM greige_pickup_photos)       AS photos;
```

Counts should match. If not, re-run the migration script (`scripts/migrate_from_supabase.py`) before continuing.

---

## Step 2 — Code audit (zero Supabase references)

From repo root:

```bash
# must return nothing
grep -r "supabase" --include="*.html" --include="*.js" --include="*.py" \
  --exclude-dir=scripts --exclude-dir=docs .

# must return nothing
grep -r "cgsmzkafagnmsuzzkfnv" --exclude-dir=scripts --exclude-dir=docs .
```

Only `scripts/` and `docs/` may mention Supabase. If either command returns matches elsewhere, fix those files before flipping DNS.

---

## Step 3 — DNS flip for gg.colorfashiondnf.com

Currently (from `CF-Domain-Infrastructure-Reference.md`): `gg` is a CNAME → `colorfashiondnf.netlify.app`.

In GoDaddy DNS for `colorfashiondnf.com`:

1. **Delete** CNAME: `gg` → `colorfashiondnf.netlify.app`
2. **Add** A record: `gg` → `76.83.45.123`
3. TTL: 600 seconds
4. Wait 10 minutes, then test from a phone on cellular (not WiFi, to bypass local DNS):
   ```
   gg.colorfashiondnf.com  →  should load from WEBSERVER (IIS), not Netlify
   ```
5. If still hitting Netlify, check Orbi port forwarding (80/443 → 192.168.1.121).

Also flip `dashboard.colorfashiondnf.com` and `shipping-web.colorfashiondnf.com` to A records if they're still CNAME to Netlify.

---

## Step 4 — Add shipping-web A record

If not already done (Phase 3):

```
Type: A   Name: shipping-web   Value: 76.83.45.123   TTL: 600
```

---

## Step 5 — Pause Supabase project

In Supabase dashboard:

1. Go to Project Settings → General
2. Click **Pause project**
3. Confirm. Billing stops, data is preserved, project can be resumed if needed.

Leave paused for **at least 2 weeks**.

---

## Step 6 — Final deletion

After 2 weeks of no missed data, in Supabase dashboard:

1. Project Settings → General → **Delete project**
2. Type the project name to confirm
3. Archive the snapshot file from Step 1 to a safe location (e.g. OneDrive, external drive)

---

## Step 7 — Netlify cleanup

1. Go to `https://app.netlify.com/projects/colorfashiondnf`
2. Remove the site, or archive it.
3. Remove `mildz79-code/ggpickup` GitHub integration from Netlify (the repo stays — it's now the source of truth for the local deployment instead).

---

## Rollback

If something breaks during Steps 3–5, rollback is:

1. Flip `gg` back to CNAME → `colorfashiondnf.netlify.app` (Supabase is still paused — will need to be resumed)
2. Resume Supabase project
3. Identify the failure, fix, re-attempt

Never proceed past Step 5 until you're certain.
