# Run explorer (web)

A read-only browser for split run logs: a landing page drawn from the study, the study view
(every run, every episode) and the episode view (requests, monitor scores, steps). Agent
reasoning stays sealed for study runs until `SCORES_FROZEN` exists; the API enforces this.

Start the API (from the repository root), then the web app:

```bash
.venv/bin/uvicorn --factory perceived_oversight.explorer:app_from_env --port 8765
```

```bash
cd explorer/web && npm install && npm run dev
```

Open http://localhost:5173. Checks: `npm run build` and `npm run lint`.

## Hosted copy (static snapshot)

The hosted copy has no server. It reads JSON exported from the split logs through the same API
code, so sealed reasoning stays sealed; spend is left out. The snapshot is never committed.

```bash
.venv/bin/python scripts/export_explorer.py
```

```bash
cd explorer/web && npm run build:static && npx vercel deploy dist --prod --project oversight-explorer
```

Pages carry a noindex tag and header. A new run shows up after it is split, exported and deployed.
