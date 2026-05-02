# Cursor Quick Start

How to drive this workspace from Cursor AI.

## First-time setup

1. Unzip this bundle into your projects folder. The root folder `ggpickup/` is your repo.
2. Open the `ggpickup/` folder in Cursor (File → Open Folder).
3. Cursor will automatically load all `.cursor/rules/*.mdc` files. Confirm they're active:
   - Cmd/Ctrl + Shift + P → "Cursor: Show Active Rules"
   - You should see: `00-project-overview`, `10-ggapi`, `20-shipping-web`, `30-sql-server-2008`, `40-supabase-retired`
4. Open `docs/PHASES.md` — this is your source of truth for what to build next.

## How to prompt Cursor effectively

Cursor knows the rules. You don't need to repeat them. Prompts should name the **phase** and the **task**:

Good:
> Do Phase 1.3 — build `D:\Data\Web\gg\app.html` (the Mockup 1 pickup list). Use the real schema from `docs/PROJECT_CONTEXT.md`. Include the test-mode banner.

> Implement `GET /api/pickups/today` per `routers/pickups.py` stub. SQL Server 2008 R2. Return the grouped shape documented in the docstring.

> Phase 3.1 — apply `ggapi/sql/003_shipping_schema.sql` via SSMS. Give me the exact commands to run.

Bad:
> Add a button somewhere.
> Build the app.
> Connect to Supabase and pull data.  ← rules will reject this

## Useful Cursor commands

- `Cmd/Ctrl + L` — inline chat on the current file (scoped rules apply automatically)
- `Cmd/Ctrl + K` — inline edit
- `Cmd/Ctrl + I` — composer (multi-file edits)
- `@docs/PHASES.md` in any prompt pulls that file into context
- `@codebase` scans the whole repo (expensive — use sparingly)

## Sync to the server

Cursor edits files locally. To deploy:

**Frontend (both apps)**
```powershell
# From your dev machine, copy to WEBSERVER's IIS folders
# Pickup app:
robocopy .\<existing gg frontend>\       \\WEBSERVER\D$\Data\Web\gg\           /E /MIR
# Shipping app:
robocopy .\shipping-web\                 \\WEBSERVER\D$\Data\Web\shipping-web\ /E /MIR
```

**Backend (FastAPI)**
```powershell
robocopy .\ggapi\ \\WEBSERVER\C$\ai\ggapi\ /E /XD __pycache__ .venv /XF .env
# Then on WEBSERVER, restart the scheduled task:
# schtasks /End  /TN "GG Pickup API"
# schtasks /Run  /TN "GG Pickup API"
```

## Push to GitHub

```bash
git add .
git commit -m "Phase N.M: <short description>"
git push origin main
```

The repo is `mildz79-code/ggpickup`. The Netlify integration is being retired in Phase 5 — pushes no longer auto-deploy. Deployment is manual via robocopy (above).

## If Cursor goes off the rails

- If it proposes Supabase code → point at `.cursor/rules/40-supabase-retired.mdc`
- If it uses `OFFSET/FETCH` or `IIF` → point at `.cursor/rules/30-sql-server-2008.mdc`
- If it wants to add React/Vite/npm → point at `.cursor/rules/20-shipping-web.mdc`
- If it's working outside the active phase → point at `docs/PHASES.md` and say "stick to Phase N"
