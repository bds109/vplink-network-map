# VPLINK Online Map — Project Handoff

## 1. Project identity

**Project name:** VPLINK Online Map / Vplink 在线地图项目  
**Parent project:** Germany Project  
**Repository:** `bds109/vplink-network-map`  
**Deployment:** GitHub Pages  
**Business owner:** VPL Automaten Service GmbH  

The map presents and manages the German vending-machine location network. It is intended for internal analysis and public presentation and will later be embedded into the corporate website.

## 2. User working style

The user is not a developer. Codex must:

- inspect the latest code and data before every implementation;
- make the change directly rather than asking the user to edit code manually;
- identify exact file paths and exact change scope;
- avoid ambiguous search instructions;
- keep explanations short and result-oriented;
- validate the result before reporting completion.

## 3. Repository structure and technical stack

The application is a static Leaflet map. Current core files include:

- `index.html` — HTML, CSS, and JavaScript application logic in one file;
- `VPL门店地图信息_0609.csv` — location data;
- Germany border and state GeoJSON/JSON files;
- GitHub Pages deployment from the repository.

External libraries:

- Leaflet 1.9.4;
- Leaflet.markercluster 1.5.3;
- Papa Parse 5.4.1.

## 4. Implemented product behavior

### 4.1 Map and controls

- Responsive full-screen Germany map.
- Default basemap: OpenStreetMap.
- Basemap buttons: OSM, CARTO Light, CARTO Dark, satellite, Amap.
- Satellite mode uses Esri imagery with a label overlay.
- Automatic tile failure fallback is intended as OSM → Light → Amap.
- Basemap switcher is at bottom-left.
- Zoom controls, reset control, and cluster-mode toggle are at bottom-right.
- Location summary card is at top-right.
- Desktop floating title is hidden while a popup is open.

### 4.2 Markers and clustering

- Cluster mode uses blue circular count markers.
- Clicking a cluster zooms in by multiple levels, capped at a suitable maximum.
- A single location in cluster mode must still zoom when clicked.
- Non-cluster mode uses a blue pin marker.
- Cluster and non-cluster modes both use the same popup content.

### 4.3 Popup behavior

- Popup shows store name, city, ID/category information, address, and photos when available.
- Popup uses a translucent glass style.
- Opening a popup pans the map so the popup card is visible, not merely so the marker is centered.
- This behavior was separately fixed for cluster and non-cluster modes.
- Photos support previous/next navigation and full-screen viewing.

### 4.4 Filters and statistics

- State filter reads CSV `State` and maps Chinese state labels to German state names.
- The user-facing left filter remains titled `Categories`.
- The actual values and counts now come from CSV `StoreType`.
- Category filtering also compares against `StoreType`.
- Category statistics use unique `StoreType` values.
- A future custom sort should keep a preferred order while automatically appending unknown/new values alphabetically.

## 5. Photo architecture

### 5.1 Storage

Cloudflare R2 bucket is used for map photos.

Current public base URL:

```text
https://pub-3575d79a89e1428486f35743798eab42.r2.dev/
```

A custom stable domain such as `img.vplink-automaten.de` was discussed as the production target but has not yet been confirmed as completed. Do not change the base URL until the domain is configured and tested.

### 5.2 Naming and association

The map uses the CSV `ID` field directly.

```text
120-01.jpg
120-02.jpg
120-03.jpg
```

Rules:

- all map-ready photos can be stored in one R2 directory;
- the number before the hyphen must equal the current CSV `ID`;
- the sequence is two digits and begins at `01`;
- sequence numbers must be continuous;
- `01` is the default popup image;
- if an operational ID changes, the R2 filenames must be renamed to the new ID.

No additional PhotoID, mapping table, image-count column, cover-image column, or URL columns are required.

### 5.3 Loading behavior

- The map does not load all photos at page startup.
- `01` is rendered as the initial popup source.
- When the user navigates/open the viewer, JavaScript probes sequential images using `new Image()`.
- It stops at the first missing number.
- The discovered list is cached by store ID for the current page session.
- A missing `01` hides the complete photo area.
- The previous/next controls loop through only discovered images.

The earlier `fetch(..., {method:'HEAD'})` approach was rejected because R2 public access/CORS behavior did not reliably identify valid images.

## 6. Data principles

- CSV is the operational source of truth.
- CSV updates may add locations and change location IDs.
- Do not create an independent permanent photo identifier.
- Confirm the current CSV headers before editing code.
- Keep current data and configuration files in GitHub.

## 7. Known code quality risks

The single-file implementation has accumulated repeated manual edits. Codex should carefully check for:

- duplicate CSS blocks such as repeated `html, body` and `#map` rules;
- orphan CSS declarations outside a selector;
- duplicate constants;
- unmatched braces/parentheses;
- malformed markup such as missing spaces in tags;
- duplicated element IDs in multiple popups;
- cache-busting queries that defeat intended browser/CDN caching.

Do not refactor broadly without a dedicated task and regression checks. Stabilize first.

## 8. Current next tasks

Recommended sequence:

1. Implement preferred Category/StoreType ordering with safe fallback for new values.
2. Review and clean obvious duplicate/orphan CSS without changing appearance.
3. Add lightweight syntax/runtime checks suitable for a static site.
4. Confirm OSM → Light → Amap fallback works for layer groups and tile layers.
5. Configure and migrate R2 URLs to a stable custom image domain when ready.
6. Produce the operations SOP for image selection, compression, naming, upload, and ID-change handling.
7. Later, evaluate embedding requirements for the official website.

## 9. Acceptance philosophy

Do not expand scope. Each task should result in a small, reviewable diff. Preserve the current look and working interactions unless the user explicitly requests a redesign.