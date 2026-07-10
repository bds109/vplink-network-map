# AGENTS.md — VPLINK Online Map

## Project position

This repository is the **VPLINK Online Map** subproject under the user's broader **Germany Project**. It is not an independent business domain. The map supports VPL Automaten Service GmbH's Germany vending-machine network presentation, internal analysis, and future embedding into the company website.

## Collaboration model

- ChatGPT acts as product architect, reviewer, and knowledge owner.
- Codex acts as the implementation executor inside this repository.
- Before changing code, inspect the latest repository files. Never rely on old snippets or assumptions.
- The user does not code. Do not ask the user to locate functions, decide between ambiguous matches, or perform fragmented edits.
- Give exact file paths and unique locations. Prefer completing the change directly in a branch and opening a PR.
- Preserve working behavior unless the task explicitly requests a change.
- After every change, verify syntax and the affected desktop/mobile flows.

## Current architecture

- Static GitHub Pages site.
- Main implementation: `index.html`.
- Data source: `VPL门店地图信息_0609.csv`.
- Boundary/config data is stored in repository JSON/GeoJSON files.
- Mapping stack: Leaflet + Leaflet.markercluster + Papa Parse.
- Production code and data are updated in GitHub.
- The map will later be embedded into the corporate website.

## Frozen product rules

### Map behavior

- Default basemap remains **OpenStreetMap**.
- Manual basemap choices: OSM, CARTO Light, CARTO Dark, satellite with labels, Amap.
- Automatic tile fallback: **OSM → Light → Amap**.
- Zoom and reset/cluster controls remain at bottom-right.
- Basemap switcher remains bottom-left, including mobile-safe placement.
- Desktop title and location summary must not overlap.
- Popup card, not only its marker, must be brought fully into view when opened.
- Both cluster mode and non-cluster mode must preserve popup centering.

### Filtering and statistics

- State filtering reads the CSV `State` field and maps Chinese state names to German names.
- The left-side section remains labeled **Categories**.
- Category filtering and category counts read the CSV `StoreType` field, not `Category`.
- Popup can show `StoreType` under the user-facing Category label.
- New `StoreType` values must remain visible even when custom ordering is introduced.

### Photo system

- CSV keeps the stable existing `ID` field. Do not add PhotoID, image count, cover image, or image URL maintenance fields unless the user reverses this decision.
- Cloudflare R2 is the photo source.
- Current public base URL: `https://pub-3575d79a89e1428486f35743798eab42.r2.dev/`.
- File naming convention: `{ID}-{two-digit sequence}.jpg`, for example `120-01.jpg`, `120-02.jpg`.
- Photos are loaded lazily only when the popup/photo interaction requires them.
- The browser probes images sequentially from `01` upward and stops at the first missing number.
- Missing-photo locations must not display a broken image area.
- Photo lookup results are cached per store during the page session.
- Popup and full-screen viewer must loop only through photos that actually exist.
- Do not scan all location photos at initial map load.

## Data rules

- Treat the CSV as the operational source of truth.
- Location IDs may change between planned and installed stages. The image filenames must be renamed to the latest CSV ID when this happens.
- Do not create a second permanent image identifier or mapping table.
- Preserve exact CSV header names and confirm them from the current file before coding.

## Coding rules

- Avoid duplicate declarations and duplicate CSS blocks when editing the single-file application.
- Do not leave unmatched braces, parentheses, or dangling CSS declarations.
- Do not use `HEAD` requests for R2 image existence checks; the working implementation uses browser image loading (`new Image()`).
- Do not hard-code a fixed number of photos per location.
- New custom ordering logic must include an alphabetical fallback for values absent from the preferred order list.
- Keep changes minimal and scoped to the requested behavior.

## Required verification

For every functional change:

1. Confirm JavaScript parses without console syntax errors.
2. Confirm the map and CSV load.
3. Test cluster and non-cluster popup behavior.
4. Test desktop and mobile layout for the affected controls.
5. For photo changes, test a location with multiple photos and a location with no photos.
6. For filter changes, verify counts and filtered markers agree.

## Documentation maintenance

Update `docs/PROJECT_HANDOFF.md` and `docs/DECISIONS.md` when a durable product or engineering rule changes. Do not overwrite approved decisions silently.