# GG Pickup

Driver app for Color Fashion greige goods pickups. Mobile-first, static frontend with a local API backend.

**Live:** https://gg.colorfashiondnf.com

## Stack

- Static HTML/JS (no build)
- Hosted static files (IIS + optional Netlify mirror)
- Local FastAPI backend exposed via same-origin `/api/*`

## Files

| File | Purpose |
|---|---|
| `index.html` | Login page |
| `app.html` | Main driver app (list, detail, mark picked up) |
| `api.js` | Shared local API client + session helper |
| `netlify.toml` | Netlify config + security headers |

## Testing-mode auth (current)

The app currently runs in **shared-password test mode**. The login page shows
a tap-to-sign-in driver picker. A yellow banner marks test mode.

Before production:

1. Replace shared test credentials with per-driver credentials.
2. Remove the hard-coded test-mode driver list from `index.html`.
3. Remove `.test-banner` markup from `index.html` and `app.html`.
4. Rotate seeded admin credentials.

## Deploying

Netlify auto-deploys on push to `main` (if enabled for this repo).

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

- Client auth token is stored in `localStorage` keys `gg_token` and `gg_user`.
- Camera upload uses `<input type="file" capture="environment">` on mobile and file picker fallback on desktop.
- Geolocation is optional for mark-picked-up flow.
