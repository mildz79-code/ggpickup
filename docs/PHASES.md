# Build Phases

The project ships in five sequenced phases. **Each phase is a complete, working system before the next begins.**

Status legend: ⬜ not started · 🟨 in progress · ✅ done

Reconciled with production reality on 2026-04-23. Earlier versions of this doc had the wrong starting point.

---

## Phase 0 — Local infrastructure baseline (✅ done)

Already live in production:

- [x] WEBSERVER IIS sites + URL Rewrite + ARR reverse proxy (gg.colorfashiondnf.com)
- [x] FastAPI at `C:\ai\ggapi\main.py` running on port 8001
- [x] SQL Server 2008 R2 on WEBSERVER localhost, database `ggpickup`
- [x] Baseline tables: `app_users`, `greige_pickup_requests`, `greige_pickup_photos`, `ship_to_locations`, `packing_memos`
- [x] 9 user accounts seeded (admin/driver/user roles)
- [x] All core API endpoints working: `/auth/login`, `/auth/me`, `/pickup-requests`, `/users`, `/locations`, `/sync`, `/scan`
- [x] Bcrypt password hashing, JWT 12h expiry
- [x] Photo storage at `C:\ai\ggapi\photos\` mounted as `/photos/*`
- [x] Google Sheets sync (sheet 1TSJNTWouAV1x4W6Ouh3uTKM-PDNJL9952eYqYcjoPAA tab TODAY)
- [x] Tesseract OCR v5.5 installed for `/scan` endpoint
- [x] win-acme SSL cert, auto-renews 2026-06-16
- [x] Mockup 1 UI design approved (light background, real schema)

---

## Phase 1 — GG Pickup driver app (🟨 active)

Wire the approved Mockup 1 design into `D:\Data\Web\gg\index.html`. Endpoints already exist; this is purely a frontend pass.

### Tasks

- [ ] **1.1** Confirm production endpoints respond as documented in `PROJECT_CONTEXT.md`. Test from a phone:
  - `POST /api/auth/login` with driver1 → returns `{token, role, display_name}`
  - `GET /api/pickup-requests?date=today&status=Pending` with bearer → returns array
  - `PATCH /api/pickup-requests/{id}/pickup` with `{lat, lng}` → marks picked up
  - `POST /api/pickup-requests/{id}/photos` multipart → saves to `C:\ai\ggapi\photos\`
- [ ] **1.2** Update `D:\Data\Web\gg\index.html` to the Mockup 1 design. The page currently has earlier UI — replace with:
  - Tile login (drivers grid + "Sign in as admin")
  - Date header (e.g. "Thursday, April 23, 2026")
  - List grouped by Knitter (factory) with Customer code + Qty + Lot Number columns
  - "Total Lots" footer
  - Test mode banner preserved
- [ ] **1.3** Frontend re-groups the flat `/pickup-requests` array by `knitter` for display.
- [ ] **1.4** Driver tap row → "Mark Picked Up" → captures `navigator.geolocation`, opens camera via `<input type="file" capture>`, posts both endpoints in sequence.
- [ ] **1.5** Login token stored in `sessionStorage` under key `cf_token`, user object under `cf_user`. Same keys used by shipping-web.
- [ ] **1.6** Add a small "Sync from Sheet" button visible to admin role only — calls `POST /api/sync`.
- [ ] **1.7** Verify zero Supabase traffic in browser Network tab.
- [ ] **1.8** Test end-to-end on Daniel's phone: login as driver1 → mark one pickup → see row flip + photo on disk.

### Exit criteria

Daniel picks a test pickup on his phone, marks it complete with photo, sees the row flip to Picked Up, photo lands in `C:\ai\ggapi\photos\`, and zero Supabase requests appear in DevTools Network.

---

## Phase 2 — Admin dispatch view on GG Pickup (⬜)

Same app, admin-gated views. Daniel runs the whole pickup day from `gg.colorfashiondnf.com`.

### Tasks

- [ ] **2.1** Reuse existing `/pickup-requests` GET/POST/PATCH/DELETE with admin role. No new endpoints needed.
- [ ] **2.2** Add `D:\Data\Web\gg\admin.html` — dispatch board:
  - Filter by date / knitter / status / driver
  - Inline edit of qty, customer, lot
  - "Add row" form
  - Soft-delete button → PATCH status='Cancelled'
  - "Assign driver" dropdown (writes to `picked_up_by` as a soft assignment until pickup completes)
- [ ] **2.3** Top nav: driver list ↔ admin board (admin role only).
- [ ] **2.4** Bulk paste from Google Sheet → preview → commit (uses existing `/sync` endpoint plus a new "preview" mode if needed).
- [ ] **2.5** Add the "Scan" button: upload image → `POST /api/scan` → preview parsed fields → confirm to insert as new pickup request.

### Exit criteria

Daniel runs an entire pickup day from `admin.html` without opening SSMS or the Google Sheet directly.

---

## Phase 3 — Shipping Schedule skeleton (manual data) (⬜)

New IIS site `shipping-web.colorfashiondnf.com`. Same FastAPI, new tables, new HTML frontend. Deliveries entered manually — **no DYESERVER yet**.

### Tasks

- [ ] **3.0** GoDaddy DNS: flip `shipping-web` from CNAME → Netlify to A → 76.83.45.123. Add SAN to win-acme cert before this site goes live.
- [ ] **3.1** Apply migration `ggapi/sql/003_shipping_schema.sql` via SSMS on WEBSERVER (creates `delivery_requests`, `schedule_days`, `schedule_stops`).
- [ ] **3.2** Implement `routers/shipping.py` endpoints:
  - `GET /shipping/today`
  - `GET /shipping/day/{yyyy-mm-dd}`
  - `POST /shipping/deliveries` (admin) — manual entry
  - `PATCH /shipping/deliveries/{id}` (admin)
  - `POST /shipping/stops` (admin)
  - `POST /shipping/stops/reorder` (admin)
  - `DELETE /shipping/stops/{id}` (admin)
- [ ] **3.3** Create IIS site `shipping-web` (host `shipping-web.colorfashiondnf.com`, path `D:\Data\Web\shipping-web\`). Drop in `web.config` from this repo.
- [ ] **3.4** Deploy `shipping-web/` frontend (index.html, deliveries.html, print.html, assets/).
- [ ] **3.5** Test end-to-end: build tomorrow's route, assign drivers, print sheets.

### Exit criteria

Daniel builds tomorrow's route by combining real pickups + manually typed deliveries, assigns each stop to a driver, prints a sheet per driver from the new shipping-web site.

---

## Phase 4 — Dyeserver integration (⬜)

Final phase. Auto-populate `delivery_requests` from DYESERVER (192.168.1.36).

### Tasks

- [ ] **4.1** Discover DYESERVER schema. SSMS from WEBSERVER → DYESERVER, inventory shipping-ready tables. Document in `docs/DYESERVER_SCHEMA.md`.
- [ ] **4.2** Create `ggapi/sync/dyeserver.py` — pyodbc connection + pull query + upsert into `delivery_requests` using `dyeserver_ref` for idempotency.
- [ ] **4.3** Apply `ggapi/sql/004_dyeserver_sync_log.sql`.
- [ ] **4.4** Add `POST /sync/dyeserver` endpoint (admin only) and `GET /sync/dyeserver/status`.
- [ ] **4.5** Windows Task Scheduler: every 10 minutes, `curl http://localhost:8001/sync/dyeserver` (with service token).
- [ ] **4.6** Admin UI: "Sync now" button + last-sync indicator on shipping-web.
- [ ] **4.7** Monitor for 1 week. Tune idempotency if duplicates appear.

### Exit criteria

Manual delivery entry stops. Deliveries appear within 10 minutes of being shipping-ready on DYESERVER.

---

## Phase 5 — Supabase retirement (⬜)

Run `docs/SUPABASE_CUTOVER.md`. Only after Phases 1–4 are stable for 1 week.

### Tasks

- [ ] **5.1** Final data snapshot via `scripts/supabase_snapshot.py`.
- [ ] **5.2** Code audit — zero Supabase references outside `scripts/` and `docs/`.
- [ ] **5.3** GoDaddy DNS: `gg` from CNAME → Netlify to A → 76.83.45.123. (May already be effectively bypassed; verify and make explicit.)
- [ ] **5.4** Pause Supabase project. Wait 2 weeks.
- [ ] **5.5** Delete Supabase project. Archive the snapshot offsite.
- [ ] **5.6** Remove the Netlify project `colorfashiondnf` (or archive).

---

## Operational items (always-on, not phased)

These move independently of the build phases. Track them here so they don't get lost.

- [ ] Task Scheduler auto-start for FastAPI (`start_ggapi.bat`)
- [ ] Orbi router port-forward 443 → 192.168.1.121 (for external HTTPS access)
- [ ] Hosts file entry on each local PC: `192.168.1.121 gg.colorfashiondnf.com` (and shipping-web after Phase 3.3)
- [ ] Install Poppler on WEBSERVER for PDF scan support
- [ ] Move JWT secret from `main.py` (if hardcoded) to `.env`
- [ ] Move SQL Server password from connection string to `.env`
