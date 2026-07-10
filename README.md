# VPLINK Online Map

VPLINK Germany vending-machine network map, maintained as a subproject of the broader **Germany Project**.

## Runtime

- Static GitHub Pages site
- Leaflet + Leaflet.markercluster
- Papa Parse CSV loading
- Cloudflare R2 location photos

## Primary files

- `index.html` — map UI and behavior
- `VPL门店地图信息_0609.csv` — operational location data
- repository GeoJSON/JSON files — Germany border and state layers
- `AGENTS.md` — mandatory Codex implementation rules
- `docs/PROJECT_HANDOFF.md` — full product and engineering context
- `docs/DECISIONS.md` — approved durable decisions
- `docs/PHOTO_OPERATIONS_SOP.md` — operations workflow for map photos

## Codex workflow

Before changing code, read `AGENTS.md`, inspect the latest repository files, and keep each change small and reviewable. Do not ask the user to perform manual code edits when the repository change can be completed directly.