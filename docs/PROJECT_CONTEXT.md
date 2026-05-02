# Project Context — Color Fashion ops apps

Architecture **as actually deployed** (not plans). Last reconciled 2026-04-23.

## The business

Color Fashion is a textile dye house. Two apps in this repo serve operations:

- **GG Pickup** — drivers log greige goods (unfinished fabric) pickups from knitting factories. **Live in production.**
- **Shipping Schedule** — dispatch combines pickups + deliveries into a daily route. **Phase 3, not started.**

## Servers (only one matters for ggpickup)

| Host | Local IP | Public IP | Role |
|---|---|---|---|
| WEBSERVER | 192.168.1.121 | 76.83.45.123 | IIS 10, FastAPI, SQL Server 2008 R2, Tesseract OCR — **everything** |
| DYESERVER | 192.168.1.36 | — | Separate dye operations server (Phase 4 integration only) |
| IDSERVER (PET350) | 192.168.1.3 | — | Separate dye-related SQL Server — **not used by ggpickup** |

The `ggpickup` SQL Server database is on **WEBSERVER itself** (localhost), not on IDSERVER. Earlier plans assumed IDSERVER; reality differed.

## Domains (GoDaddy DNS)

- `gg.colorfashiondnf.com` — currently CNAME → Netlify (legacy). Production hits IIS via the public IP. Phase 5 cutover flips this to A → 76.83.45.123.
- `shipping-web.colorfashiondnf.com` — CNAME → Netlify currently. Phase 3 work needs this flipped to A → 76.83.45.123 before the new app goes live.

## SSL

- **win-acme** issues Let's Encrypt certs on WEBSERVER. Auto-renews **2026-06-16**.
- Certificate covers `gg.colorfashiondnf.com`. Add `shipping-web.colorfashiondnf.com` SAN before Phase 3 deploy.

## IIS sites on WEBSERVER

| Site | Port | Host | Path |
|---|---|---|---|
| gg | 80 + 443 | gg.colorfashiondnf.com | `D:\Data\Web\gg\` |
| shipping-web | 80 + 443 (planned) | shipping-web.colorfashiondnf.com | `D:\Data\Web\shipping-web\` (Phase 3) |

Both sites' `web.config` reverse-proxies `/api/*` → `http://localhost:8001/*` (note: **strips** the `/api/` prefix). URL Rewrite + ARR modules already installed.

## FastAPI backend

- Path: `C:\ai\ggapi\` on WEBSERVER
- Python: `C:\ai\python\python.exe` (system install, not venv currently)
- Port: `8001` (bound localhost-only)
- Run command:
  ```
  cd C:\ai\ggapi
  C:\ai\python\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001
  ```
- Health: `https://gg.colorfashiondnf.com/api/health` returns `{"status":"ok"}`
- Auto-start: **PENDING** — Task Scheduler job not yet wired to `start_ggapi.bat`

### Production routes (no /api prefix on the backend; IIS strips it)

| Method | Production path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | none | Health check |
| POST | `/auth/login` | none | JWT login (bcrypt) |
| GET | `/auth/me` | any | Current user info |
| GET | `/pickup-requests` | any | Filtered list (date/status/knitter) |
| POST | `/pickup-requests` | admin | Create request |
| GET | `/pickup-requests/{id}` | any | Single request |
| PATCH | `/pickup-requests/{id}` | admin | Update |
| DELETE | `/pickup-requests/{id}` | admin | Delete |
| PATCH | `/pickup-requests/{id}/pickup` | any | Mark picked up + GPS |
| POST | `/pickup-requests/{id}/photos` | any | Multipart photo upload |
| GET | `/pickup-requests/{id}/photos` | any | List photos |
| GET | `/users` | admin | User list |
| GET | `/locations` | any | Ship-to locations |
| POST | `/sync` | admin | Google Sheets → SQL Server |
| POST | `/scan` | admin | Tesseract OCR on uploaded image |

Browser hits all of these prefixed with `/api/`. Example: the frontend calls `/api/auth/login`, IIS forwards to FastAPI as `/auth/login`.

## Database

- **Host**: `localhost` (on WEBSERVER itself)
- **Engine**: SQL Server 2008 R2 — **strict T-SQL compatibility required** (see `.cursor/rules/30-sql-server-2008.mdc`)
- **Database**: `ggpickup`
- **Auth**: SQL auth as `sa` (operational password in `.env`, never in git)
- **ODBC driver**: `{ODBC Driver 17 for SQL Server}` (installed)

### Tables (current, Phase 0 baseline)

```
app_users               id, email, password_hash, role, display_name, is_active, created_at
greige_pickup_requests  id, request_date, knitter, customer, lot_number, qty,
                        status, notes, picked_up_at, picked_up_by, lat, lng, created_at
greige_pickup_photos    id, request_id, file_path, uploaded_by, lat, lng, created_at
ship_to_locations       id, code, name, street, city, state, zip, phone, lat, lng, is_active
packing_memos           id, customer, lot_number, total_rolls, total_weight, pieces_json,
                        source_file, source_hash, raw_ocr_text, ocr_confidence,
                        matched_request_id, match_status, scanned_at, created_at
```

### Tables added in later phases

```
delivery_requests       (Phase 3 — see ggapi/sql/003_shipping_schema.sql)
schedule_days           (Phase 3)
schedule_stops          (Phase 3)
dyeserver_sync_log      (Phase 4 — see ggapi/sql/004_dyeserver_sync_log.sql)
```

## Photo storage

- Path: `C:\ai\ggapi\photos\` (FastAPI mounts this as `/photos/*`)
- IIS proxies `/api/photos/*` to FastAPI's static mount.
- File naming: `{request_id}_{timestamp}_{uuid4}.jpg`

## Google Sheets sync

| Item | Value |
|---|---|
| Sheet ID | `1TSJNTWouAV1x4W6Ouh3uTKM-PDNJL9952eYqYcjoPAA` |
| Tab | `TODAY` |
| Service account | `netlify-sync@delivery-dashboard-487000.iam.gserviceaccount.com` |
| Credentials file | `C:\ai\ggapi\google-credentials.json` |
| Behavior | Reads rows 3+, carries forward merged knitter cells, filters TOTAL rows, deletes today's Pending rows then re-inserts |

## OCR (Tesseract)

- Binary: `C:\Program Files\Tesseract-OCR\tesseract.exe` (v5.5)
- Handles JPG/PNG. **Pending**: Poppler install for PDF support.

## Users (production)

| Email | Role |
|---|---|
| daniel@colorfashiondnf.com | admin |
| ryan@colorfashiondnf.com | admin |
| driver1@colorfashiondnf.com | driver |
| driver2@colorfashiondnf.com | driver |
| driver3@colorfashiondnf.com | driver |
| brian.colorfashion@gmail.com | user |
| ap@colorfashiondnf.com | user |
| pearlie.colorfashion@gmail.com | user |
| monica@colorfashiondnf.com | user |

Production passwords are in the team password vault, **not** in this repo.

## Pending operational items (separate from build phases)

- [ ] Task Scheduler auto-start for FastAPI (`start_ggapi.bat`)
- [ ] Orbi router: forward port 443 → 192.168.1.121
- [ ] Hosts file on each local PC: `192.168.1.121 gg.colorfashiondnf.com` (so internal access doesn't need to round-trip through public DNS)
- [ ] Poppler install on WEBSERVER for PDF scan support
- [ ] Sync + Scan buttons in the frontend `index.html` admin UI

## Historical / legacy

- **Supabase project `cgsmzkafagnmsuzzkfnv`** was the original backend. **Retired.** See `docs/SUPABASE_CUTOVER.md`. Any code referencing Supabase is legacy or migration-only.
- **Onetex Supabase project `mtxokbgpmkggolyfeehz`** belongs to a separate company. **Never touch.** If any connection string contains that ID, stop and alert Daniel.
