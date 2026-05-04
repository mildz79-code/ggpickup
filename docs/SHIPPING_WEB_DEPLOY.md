# Shipping-web IIS deploy runbook — `shipping-web.colorfashiondnf.com`

**Audience:** Daniel on **WEBSERVER**, signed in as **Administrator**.  
**Scope:** Deploy static files from this repo's `shipping-web/` to IIS at `D:\Data\Web\shipping-web\`, DNS + SSL aligned with Phase 3.  
**Infrastructure reference:** [`PRODUCTION_INVENTORY.md`](PRODUCTION_INVENTORY.md) (paths, IP, IIS facts win over other docs).

Do **not** run these steps unless **Section 1** passes. Steps are ordered: complete each numbered section before the next.

---

## 1. Pre-flight checks

### 1.1 IIS URL Rewrite + ARR modules

Already installed for the GG site — verify globals:

```powershell
Get-WebGlobalModule | Where-Object { $_.Name -match 'Rewrite|ApplicationRequestRouting' } | Format-Table Name
```

Expect entries for URL Rewrite (`RewriteModule`) and ARR proxy stack (names vary by IIS; if nothing matches Rewrite/ARR and API proxying breaks, reinstall per `PRODUCTION_INVENTORY.md`: URL Rewrite Module 2.1, Application Request Routing, and Server Proxy Settings → Enable proxy.)

### 1.2 Task Scheduler — GG Pickup API

```powershell
Get-ScheduledTask -TaskName "GG Pickup API"
```

Confirm the task exists and is usable (Registered / Ready — not only "does not exist"). If auto-start is still pending (`PRODUCTION_INVENTORY.md`), the API must still be **running manually** (`start_ggapi.bat` or uvicorn) before smoke tests — otherwise stop and start the API process first.

### 1.3 Phase 3 SQL migration applied

Uses `SQL_PASSWORD` from your session or vault-loaded env (same convention as [`PHASE_3_RUNBOOK.md`](PHASE_3_RUNBOOK.md)):

```powershell
sqlcmd -S localhost -U sa -P $env:SQL_PASSWORD -d ggpickup -Q "SELECT name FROM sys.tables WHERE name IN ('delivery_requests', 'schedule_days', 'schedule_stops')"
```

**Expect:** three rows (`delivery_requests`, `schedule_days`, `schedule_stops`).  
**If 0 rows:** apply migration first (`ggapi/sql/003_shipping_schema.sql` via SSMS or sqlcmd `-i`; full procedure in [`PHASE_3_RUNBOOK.md`](PHASE_3_RUNBOOK.md)). Do not deploy shipping-web against a DB without these tables.

### 1.4 FastAPI exposes `/shipping/*` (router-based ggapi live on WEBSERVER)

Shipping-web calls IIS `/api/shipping/*` → FastAPI `/shipping/*` (see [`ggapi/routers/shipping.py`](../ggapi/routers/shipping.py)).

**Verify on WEBSERVER:**

- Deployed **`C:\ai\ggapi\`** includes **`routers/shipping.py`** **and**
- **`main.py`** **`include_router`** for shipping (same pattern as repo [`ggapi/main.py`](../ggapi/main.py): `app.include_router(shipping.router)`).

**If production `main.py` is still an old monolithic file** without the shipping router, **STOP** — IIS and static files alone will serve HTML, but every schedule API call will **404**. Complete secrets + **code cutover** to router-based ggapi **before** go-live.

**Quick code check examples (adapt paths if needed):**

```powershell
Select-String -Path "C:\ai\ggapi\main.py" -Pattern "shipping"
Test-Path "C:\ai\ggapi\routers\shipping.py"
```

---

## 2. Create new IIS site

Run **Windows PowerShell as Administrator**:

```powershell
Import-Module WebAdministration

# Resolve application pool used by GG (document this name after you read it).
Get-Website -Name "gg" | Select-Object Name, @{n='ApplicationPool';e={$_.applicationPool}}

New-Website -Name "shipping-web" -PhysicalPath "D:\Data\Web\shipping-web" -HostHeader "shipping-web.colorfashiondnf.com" -Port 80
```

**Application pool:** Reuse the **same pool** as the `gg` site. If GG uses **DefaultAppPool**, you can leave shipping-web on the pool assigned by default; otherwise set shipping-web explicitly:

```powershell
$pool = (Get-Website -Name "gg").applicationPool
Set-ItemProperty "IIS:\Sites\shipping-web" -Name applicationPool -Value $pool
```

**Chosen pool name (fill in during run):** ___________________

**Verify:**

```powershell
Get-Website -Name "shipping-web"
```

Ensure **physical path exists** (`D:\Data\Web\shipping-web`). Create the folder if empty before copying files:

```powershell
New-Item -ItemType Directory -Path "D:\Data\Web\shipping-web" -Force
```

---

## 3. Deploy static files

### 3.1 Robocopy from repo → IIS path

Replace `<FULL_REPO_PATH>` with the actual path where this repo lives on WEBSERVER (or a UNC/copy location):

```powershell
robocopy "<FULL_REPO_PATH>\shipping-web" "D:\Data\Web\shipping-web" /E /R:2 /W:2 /XD __pycache__
```

- `/E` — include subdirectories (including empty).  
- `/R:2` / `/W:2` — retries and wait between retries.  
- `/XD __pycache__` — skip Python artifact folders if any.

### 3.2 Verify payloads

Confirm at minimum:

- `D:\Data\Web\shipping-web\index.html`
- `D:\Data\Web\shipping-web\web.config`
- `D:\Data\Web\shipping-web\assets\` (subfolder present with JS/CSS/views)

Repo `web.config` reverse-proxies **`/api/*`** to **`http://localhost:8001/*`** (**strips `/api/`**), mirroring GG — identical pattern to Phase 3.3 in [`PHASES.md`](PHASES.md).

---

## 4. DNS update (GoDaddy)

**Current intent:** `shipping-web` is a **CNAME** → `colorfashiondnf.netlify.app` (`PRODUCTION_INVENTORY.md`).

### 4.1 Target record

Use an **A** record pointing at WEBSERVER public IP:

| Field | Value |
|--------|--------|
| **Type** | A |
| **Name** | `shipping-web` |
| **Value** | `76.83.45.123` |
| **TTL** | `600` (seconds = ~10 minutes) |

### 4.2 GoDaddy constraint

**Delete** the existing **CNAME** for `shipping-web` **first**, then **add** the **A** record. GoDaddy will not host both names for the same host label.

### 4.3 Propagation check

Wait **≈10 minutes** after publishing DNS. Test from **cellular data** or another network outside office DNS caches:

```text
nslookup shipping-web.colorfashiondnf.com
```

Expect **`76.83.45.123`**. Netlify IPs mean DNS or TTL cache has not flipped yet — do **not** treat HTTPS success on wrong IP as a win.

---

## 5. SSL certificate (win-acme)

**Recommendation:** add **`shipping-web.colorfashiondnf.com`** as a **SAN** on the existing **`gg.colorfashiondnf.com`** renewal — single cert, dual hostname, aligned with `PRODUCTION_INVENTORY.md`.

### 5.1 Interactive win-acme

Locate `wacs.exe` if unsure:

```powershell
Get-ChildItem C:\ -Filter "wacs.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 5 FullName
```

Typical install per inventory: **`C:\win-acme`** (`PRODUCTION_INVENTORY.md` cites win-acme v2.2.9).

```powershell
cd C:\win-acme
.\wacs.exe
```

**Menu guidance (titles may vary slightly by version):**  
**Edit renewal** → select the renewal covering **`gg.colorfashiondnf.com`** → **Add identifier** → enter **`shipping-web.colorfashiondnf.com`** → confirm → **renew now** (or save and renew as prompted).

### 5.2 Verify cert subject alt names

```powershell
Get-ChildItem Cert:\LocalMachine\My | Where-Object { $_.Subject -match 'colorfashiondnf' } | Select-Object Subject, @{n='DnsNameList';e={ $_.DnsNameList.Unicode } }
```

**Expect:** **one** cert whose **SAN list** contains **both** `gg.colorfashiondnf.com` **and** `shipping-web.colorfashiondnf.com`.

---

## 6. HTTPS binding (SNI)

Run **PowerShell as Administrator**:

```powershell
Import-Module WebAdministration

$cert = Get-ChildItem Cert:\LocalMachine\My |
  Where-Object { $_.DnsNameList -contains "shipping-web.colorfashiondnf.com" } |
  Sort-Object NotAfter -Descending |
  Select-Object -First 1

if (-not $cert) { throw "No certificate found with SAN shipping-web.colorfashiondnf.com"; }

New-WebBinding -Name "shipping-web" -Protocol "https" -Port 443 -HostHeader "shipping-web.colorfashiondnf.com" -SslFlags 1

(Get-WebBinding -Name "shipping-web" -Protocol "https").AddSslCertificate($cert.Thumbprint, "My")
```

- **`SslFlags 1`** — SNI enabled (multiple HTTPS sites on **one IP** require SNI).

If `AddSslCertificate` errors on your IIS/PowerShell build, alternate pattern (same intent): bind via **IIS Manager** → site **shipping-web** → **Bindings…** → **https** · port **443** · host **`shipping-web.colorfashiondnf.com`** · choose the consolidated cert · **Require Server Name Indication**.

---

## 7. Smoke tests (WEBSERVER — `curl`)

Run with **FastAPI listening on port 8001**.

### 7.1 Direct to FastAPI (no IIS)

```powershell
curl.exe http://localhost:8001/health
```

**Expect:** JSON `{"status":"ok"}`.

```powershell
curl.exe http://localhost:8001/shipping/today
```

**Expect:** **401** Unauthorized — no bearer token sent.

### 7.2 Authenticated `/shipping/today`

Obtain a JWT via login (adjust email/password):

```powershell
$body = '{"email":"<ADMIN_EMAIL>","password":"<PASSWORD>"}'
curl.exe -s -X POST -H "Content-Type: application/json" -d $body http://localhost:8001/auth/login
```

Responses may use **`access_token`** (router-based ggapi repo) **`or`** **`token`** (legacy) — capture whichever field holds the JWT.

```powershell
$token = "<PASTE_JWT_HERE>"
curl.exe -s -H "Authorization: Bearer $token" http://localhost:8001/shipping/today
```

**Expect:** **200** with JSON containing **`schedule_date`**, **`pickups`**, **`deliveries`**, **`stops`** (possibly empty arrays if no rows yet).

### 7.3 Through IIS (shipping-web hostname + `/api/` prefix)

```powershell
curl.exe -s https://shipping-web.colorfashiondnf.com/api/shipping/today
```

**Expect:** **401** (no bearer).

```powershell
curl.exe -s https://shipping-web.colorfashiondnf.com/api/health
```

**Expect:** `{"status":"ok"}` (proves IIS → ARR/Rewrite → FastAPI `/health`).

```powershell
curl.exe -sI https://shipping-web.colorfashiondnf.com/
```

**Expect:** **200 OK** headers for **`index.html`**.

Optional — authorized through IIS:

```powershell
curl.exe -s -H "Authorization: Bearer $token" https://shipping-web.colorfashiondnf.com/api/shipping/today
```

**Expect:** **200** plus schedule JSON.

---

## 8. Browser verification plan

Real-user acceptance on Daniel's PC or phone (HTTPS).

1. Open **`https://gg.colorfashiondnf.com`** and log in as admin (GG Pickup sets **`sessionStorage`** keys **`cf_token`** / **`cf_user`** on **GG's origin only**).

2. Open **`https://shipping-web.colorfashiondnf.com`** in a **new tab**. **`sessionStorage` is not shared across subdomains** — **shipping-web** will **not** see GG's tokens. **`shipping-web` may redirect once to GG for login** via `assets/auth.js` when unauthenticated (`next=` return URL pattern). Regardless, **assume a separate login or redirect round-trip**, not invisible SSO. Blank schedule after auth is acceptable if pools have no Pending rows yet.

3. Complete login / return flow until schedule UI loads.

4. Drag pickups and deliveries from pool onto the schedule board.

5. Drag stops to reorder.

6. Assign drivers via dropdown.

7. **Print** sheets — verify per-driver printable pages show expected data (`print.html`).

8. **Logout** — expect shipping-web session cleared; GG tab may retain its own `sessionStorage` until signed out there.

---

## 9. Rollback (worst case)

Removes **only** the shipping-web IIS site and HTTPS binding — **does not** delete repo, FastAPI, or GG files.

```powershell
Import-Module WebAdministration
Remove-WebBinding -Name "shipping-web" -Protocol "https" -Port 443
Remove-Website -Name "shipping-web"
```

**GoDaddy:** Remove the **A** record for **`shipping-web`** and recreate **CNAME** → **`colorfashiondnf.netlify.app`** as before (`PRODUCTION_INVENTORY.md`). Allow DNS TTL to propagate before declaring rollback complete.

FastAPI **`C:\ai\ggapi`** and site **`gg`** remain as-is.

---

## 10. Operational notes

- **JWT / login payload vs UI:** Repo router login returns **`access_token`** **[`ggapi/routers/auth.py`](../ggapi/routers/auth.py)] and **`user.full_name`**; [`shipping-web/assets/auth.js`](../shipping-web/assets/auth.js) displays **`cf_user.display_name`** in the header. **Production** may still return **`token`** or **`display_name`** only (**[`PHASES.md`](PHASES.md)**). Before calling go-live stable, verify **GG Pickup login** persists **`cf_token`** and a **`cf_user`** object that satisfies shipping-web (**at minimum** bearer token validity; **`display_name` vs `full_name`** mismatch may hide the user's name but should not block API calls if tokens are issued).

- **No cross-subdomain `sessionStorage`:** `gg.colorfashiondnf.com` and **`shipping-web.colorfashiondnf.com`** are distinct origins → **distinct `sessionStorage`**. Users naturally **authenticate per host** unless you later add **cross-site SSO** (e.g. **HTTP-only cookie** with **`Domain=.colorfashiondnf.com`**) — that is **out of scope** for this deploy.

- **Ports / routing:** IIS on **443** terminates TLS; **`localhost:8001`** stays **FastAPI**. [`PHASES.md`](PHASES.md) Phase 4+ (DYESERVER, etc.) does not change this runbook sequence.
