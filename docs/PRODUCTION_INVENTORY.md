# Production Inventory — WEBSERVER

What's actually deployed, where it lives, how to operate it. Updated 2026-04-23.

This file is the **single source of truth** for the running system. If anything in `PROJECT_CONTEXT.md` or `PHASES.md` contradicts this file, this file wins.

---

## Hardware / network

| | |
|---|---|
| Hostname | WEBSERVER |
| Local IP | 192.168.1.121 |
| Public IP (Spectrum static) | 76.83.45.123 |
| Gateway | 192.168.1.1 (Netgear Orbi) |
| OS | Windows Server (IIS 10) |

---

## File paths

| Purpose | Path |
|---|---|
| FastAPI source | `C:\ai\ggapi\` |
| Python interpreter | `C:\ai\python\python.exe` (system install, not venv) |
| Photo storage | `C:\ai\ggapi\photos\` |
| Google credentials | `C:\ai\ggapi\google-credentials.json` |
| API logs | `C:\ai\ggapi\ggapi.log` |
| Tesseract OCR | `C:\Program Files\Tesseract-OCR\tesseract.exe` (v5.5) |
| GG frontend | `D:\Data\Web\gg\` (default doc: `index.html`) |
| Shipping frontend (planned) | `D:\Data\Web\shipping-web\` |
| Other IIS sites | `D:\Data\Web\Dashboard\`, `D:\Data\Web\Shipping\`, `D:\lekosweb\`, `D:\Data\WebDAV\` |

---

## Services

### FastAPI (ggapi)

```powershell
# Start manually:
cd C:\ai\ggapi
C:\ai\python\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001

# OR via the bat file:
C:\ai\ggapi\start_ggapi.bat
```

- Port: `8001`, bound to all interfaces (firewall blocks external; only IIS reaches it via localhost)
- Health: `http://localhost:8001/health` or `https://gg.colorfashiondnf.com/api/health`
- **Auto-start: PENDING** — Task Scheduler job not configured yet

### SQL Server 2008 R2

- Host: `localhost`
- Service name: typically `MSSQLSERVER` (default instance)
- Database: `ggpickup`
- Connection: `Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=ggpickup;UID=sa;PWD=<vault>;`

### IIS

- Manager: `inetmgr`
- Required modules (all installed): URL Rewrite Module 2.1 (x64), Application Request Routing
- ARR proxy: enabled (Server node → Application Request Routing Cache → Server Proxy Settings → Enable proxy ✓)

#### IIS sites

| Site | Bindings | Path |
|---|---|---|
| gg (ID 6) | 80 + 443, host gg.colorfashiondnf.com | `D:\Data\Web\gg\` |
| Dashboard | 1365 + 4365 | `D:\Data\Web\Dashboard\` |
| colorfashiondnf | 80, host www.colorfashiondnf.com | `D:\lekosweb\` |
| shipping (legacy) | 8365 https | `D:\Data\Web\Shipping\` |
| shipping-web (planned) | 80 + 443, host shipping-web.colorfashiondnf.com | `D:\Data\Web\shipping-web\` |
| WebDAV | 808/8080 | `D:\Data\WebDAV\` |

### SSL (win-acme)

- Tool: win-acme v2.2.9
- Cert authority: Let's Encrypt
- **Renewal date: 2026-06-16** (auto)
- Covers: `gg.colorfashiondnf.com`
- Add SAN for `shipping-web.colorfashiondnf.com` before Phase 3 deploy

---

## Installed Python packages on WEBSERVER

```
fastapi, uvicorn, pyodbc, PyJWT, bcrypt, python-multipart
google-auth, google-auth-httplib2, google-api-python-client
pytesseract, pillow, opencv-python, numpy
```

(Pinned via `ggapi/requirements.txt`, but currently installed system-wide on `C:\ai\python\`.)

---

## Configuration secrets

These exist in production. Do NOT commit. Real values live in the team password vault.

| Key | Purpose | Where it lives in prod | Where it should live |
|---|---|---|---|
| `SQL_PASSWORD` | sa login | hardcoded in `main.py` currently | `C:\ai\ggapi\.env` |
| `JWT_SECRET` | token signing | hardcoded in `main.py` currently as `ColorFashion2026_GGPickup_SecretKey_XK92` | `C:\ai\ggapi\.env` |
| Google service account | sheet sync | `C:\ai\ggapi\google-credentials.json` | (file already correct location) |

The first two are migrated to `.env` as part of cleanup. Until then, treat `main.py` as a secret file.

---

## DNS records (GoDaddy, colorfashiondnf.com)

Current state (mixed; cutover pending):

| Type | Name | Value | Notes |
|---|---|---|---|
| A | @ | 76.83.45.123 | Apex |
| A | shipping | 76.83.45.123 | Legacy shipping subdomain |
| CNAME | gg | colorfashiondnf.netlify.app | **Phase 5: flip to A → 76.83.45.123** |
| CNAME | dashboard | colorfashiondnf.netlify.app | **Phase 5** |
| CNAME | shipping-web | colorfashiondnf.netlify.app | **Phase 3.0: flip to A → 76.83.45.123** |
| CNAME | www | colorfashiondnf.com | OK |

Email DNS (IONOS — separate concern, do not touch in cutover): MX, SPF, DMARC, 3 DKIM CNAMEs documented in `CF-Domain-Infrastructure-Reference.md` in the project root.

---

## Pending operational items

- [ ] Task Scheduler auto-start for FastAPI
- [ ] Orbi port forward 443 → 192.168.1.121
- [ ] Hosts file on local PCs: `192.168.1.121 gg.colorfashiondnf.com`
- [ ] Poppler install (PDF scan support for `/scan`)
- [ ] Move JWT secret + SQL password from code to `.env`
- [ ] Add `shipping-web.colorfashiondnf.com` SAN to win-acme cert (before Phase 3)

---

## Operational quick reference

```powershell
# Restart API after code change:
taskkill /F /IM python.exe
cd C:\ai\ggapi
C:\ai\python\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001

# Apply a SQL migration:
sqlcmd -S localhost -U sa -P <pw> -d ggpickup -i ggapi\sql\003_shipping_schema.sql

# Tail API log:
Get-Content C:\ai\ggapi\ggapi.log -Tail 50 -Wait

# Check IIS sites:
appcmd list site

# Trigger sheet sync manually:
curl -X POST -H "Authorization: Bearer <admin-token>" https://gg.colorfashiondnf.com/api/sync
```
