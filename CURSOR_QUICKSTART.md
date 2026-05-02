# Cursor quickstart — GG Pickup

Short orientation for agents and humans opening this repo in Cursor.

## What this repo is

Static **driver + admin** web app for greige pickup requests: `index.html` (login), `app.html` (main UI). No bundler; vanilla JS plus Supabase from CDN in `supabase-client.js`. Deployed on **Netlify**; data in **Supabase**.

## Open in Cursor

1. **File → Open Folder** and choose the repo root (the folder that contains `index.html`, `app.html`, `README.md`).
2. Optional: add a `.cursor/rules` or project instructions if your team uses them; this repo ships without them.

## Run locally

From the repo root:

```bash
python3 -m http.server 8000
```

Open `http://localhost:8000` — you get `index.html` by default.

**Netlify Functions** (sync from Google Doc, config, cron) only run when deployed to Netlify with env vars set, or via Netlify CLI with linked project + env. A plain static server does not execute `netlify/functions`.

## Dependencies

`package.json` exists for **Netlify function** dependencies (`googleapis`, `@netlify/functions`). Install before working on functions:

```bash
npm install
```

## Files to know first

| Path | Role |
|------|------|
| `index.html` | Login / driver picker (test mode) |
| `app.html` | List, detail, camera, admin sync |
| `supabase-client.js` | Supabase client, session, test auth helpers |
| `netlify.toml` | Publish root, functions dir, CSP headers |
| `netlify/functions/*.mjs` | Doc sync + server-side config |
| `lib/google-doc-sync.js` | Shared sync logic used by functions |
| `README.md` | Full stack notes, DB tables, env vars for sync |

## Secrets

Never commit Supabase **service role** keys or Google **private keys**. Client uses the **anon** key only. Server functions need `SUPABASE_SERVICE_ROLE_KEY` and Google service account vars on Netlify — see `README.md`.

## If your copy differs

If you maintain a longer quickstart on your machine, paste it into this file and commit so cloud agents and teammates see the same version.
