# Moonshot Competitive Intelligence Dashboard — Frontend

Plain React + Vite SPA. No router library, no state-management library, no
CSS framework — `App.jsx` switches screens via `useState`, one CSS file with
variables covers the whole design system.

## Structure

- `src/App.jsx` — screen router (`overview` | `comparison` | `drilldown`), fetches the summary once
- `src/api/client.js` — the only fetch layer, one function per endpoint
- `src/components/` — one component per screen: `Overview`, `BrandComparison`, `ProductDrilldown`
- `src/styles.css` — CSS variables + a handful of reusable classes

## Running

```bash
npm install
npm run dev
```

Proxies `/api` to `http://localhost:8000` (see `vite.config.js`) — run the
backend alongside it.
