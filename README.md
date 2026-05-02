# ggpickup — Color Fashion operations monorepo

Two web apps + one FastAPI backend for Color Fashion's warehouse operations.

```
ggpickup/
├── .cursor/rules/         ← Cursor AI guardrails (read these first)
├── docs/
│   ├── PROJECT_CONTEXT.md ← Architecture, servers, infra
│   ├── PHASES.md          ← Build sequence (Phases 1–5)
│   └── SUPABASE_CUTOVER.md← Retirement checklist
├── ggapi/                 ← FastAPI (Python) — deployed to C:\ai\ggapi\ on WEBSERVER
├── <existing gg frontend> ← Driver + admin app at gg.colorfashiondnf.com
├── shipping-web/          ← Shipping schedule app at shipping-web.colorfashiondnf.com
└── scripts/               ← One-off migration / cutover scripts
```

## Quick orientation for Cursor

1. Read `.cursor/rules/00-project-overview.mdc` first — it tells you where everything lives.
2. Read `docs/PROJECT_CONTEXT.md` for infrastructure (IPs, IIS sites, SQL Server).
3. Read `docs/PHASES.md` to see what phase is active. **Do not jump phases.**
4. Every change must state which phase it belongs to and which file it modifies.

## Hard rules (the short version)

- **Backend is SQL Server 2008 R2 on IDSERVER (192.168.1.3), database `ggpickup`.** Not Supabase.
- **API runs on WEBSERVER at `localhost:8001` (FastAPI).** IIS reverse-proxies `/api/*`.
- **Two frontends, one backend.** Both apps call the same FastAPI.
- **No build steps.** Vanilla HTML + JS. IIS serves files as-is.
- **Never connect to DYESERVER until Phase 4.** Mock or manual data only before then.
- **Never wire new features to Supabase `cgsmzkafagnmsuzzkfnv`.** It's being retired.
