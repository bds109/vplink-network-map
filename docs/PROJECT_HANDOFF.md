# VPLINK Online Map — Project Handoff

## 1. Project identity

**Project name:** VPLINK Online Map  
**Repository:** `bds109/vplink-network-map`  
**Business hierarchy:** Germany Project → VPLINK Online Map  
**Current deployment:** GitHub Pages  
**Primary purpose:** Display VPLINK vending-machine locations across Germany with operational filters, state overlays, clustering, store information, and location photos. The page will ultimately be embedded into the VPLINK website.

This is an operating business tool, not a demo-only map. Future work must prioritize maintainability, low operational workload, desktop/mobile usability, and safe updates by Codex.

## 2. Current repository architecture

The application is intentionally simple:

- `index.html` contains the current HTML, CSS, and JavaScript.
- The location CSV is stored and updated in GitHub.
- Germany border and state overlays are stored as GeoJSON/JSON files in GitHub.
- GitHub Pages serves the public map.
- Cloudflare R2 stores location photos.

Do not introduce frameworks, databases, servers, APIs, RAG systems, or other infrastructure unless Steve explicitly approves a requirement that cannot be met with the current structure.

## 3. Current map behavior

### Base layers

The map currently supports these manually selectable layers:

1. OSM — default.
2. Carto Light.
3. Carto Dark.
4. Esri satellite imagery with a separate label overlay.
5. Amap — mainly retained as a China-access fallback.

Automatic failure sequence:

`OSM → Carto Light → Amap`

Refreshing the page returns the default choice to OSM.

### Controls and layout

- Filter panel: upper-left.
- Statistics summary: upper-right.
- Map-style buttons: lower-left.
- Zoom, reset, and cluster-mode controls: lower-right.
- Mobile layout has separate positioning constraints and must be checked after every control/layout change.

### Clustering

- Leaflet.markercluster is used.
- Cluster click zooms further into the map.
- A cluster containing one location must still allow zoom behavior.
- The user can toggle between cluster and individual-marker modes.
- Popup positioning must work in both modes.

### Popup

The popup currently displays business/location fields and an optional photo carousel.

Key approved behavior:

- The popup card itself must be visually centered in the map viewport.
- Do not center only the marker.
- Do not solve positioning by adding an unnecessary scroll area inside the popup.
- Enlarged photo view supports previous/next navigation.

## 4. CSV and business data rules

The current CSV is the operational source of truth and is periodically replaced or updated in GitHub.

Operational filename used by the live map:

`VPL门店地图信息.csv`

Important fields include:

- `ID` — location identifier and photo association key.
- `StoreName`
- `State`
- `City`
- `Category`
- `StoreType`
- `Address`
- `Latitude`
- `Longitude`

### Category-filter decision

The visible filter section remains named **Categories**, but its values and counts are sourced from:

`StoreType`

Not from:

`Category`

All filtering and category-count logic must therefore consistently use `store.StoreType` / `item.store.StoreType`.

If a custom category order is added later, use this behavior:

1. Configured known values appear in the approved custom order.
2. Any new/unrecognized `StoreType` values are still shown automatically.
3. New values are appended using a deterministic fallback such as locale-aware alphabetical sorting.
4. Missing values must not crash rendering.

## 5. Photo system

### Storage

Cloudflare R2 bucket was created for map photos.

Current public development base URL:

`https://pub-3575d79a89e1428486f35743798eab42.r2.dev`

A future production improvement may bind a stable custom subdomain, but do not change the current URL without a migration plan and verification.

### Naming and association

Photos are associated directly with CSV `ID`.

Naming format:

`<ID>-<two-digit-order>.jpg`

Example for location 120:

- `120-01.jpg`
- `120-02.jpg`
- `120-03.jpg`

All files may live in the same R2 object namespace; separate per-location folders are not required.

### Discovery behavior

The CSV does not need image URL, image count, cover image, or photo ID columns.

On popup/photo interaction, code checks sequential images:

1. Try `ID-01.jpg`.
2. Continue with `ID-02.jpg`, `ID-03.jpg`, and so on.
3. Stop at the first missing image.
4. Display only successfully discovered images.
5. Cache the discovered list in memory by store ID so repeat visits do not perform the same checks again.

The current implementation uses browser image loading checks rather than `HEAD` requests because R2 public access/CORS behavior made `HEAD` unreliable.

A store with no `ID-01.jpg` must hide the entire image/carousel area rather than showing a broken image.

## 6. Photo operations model

The internal team maintains original photos separately by region and store. The intended low-workload operational process is:

1. Team uploads original location photos to the internal shared-photo library.
2. Operations selects the photos to publish and determines display order.
3. Photos are resized/compressed for web use.
4. Files are renamed according to `ID-01.jpg`, `ID-02.jpg`, etc.
5. Files are uploaded to Cloudflare R2.
6. No photo URLs or counts are entered into the CSV.
7. The map discovers the photos from the existing CSV `ID`.

If a provisional location ID later changes to a formal ID, operations must rename the related R2 objects to the new ID when the CSV is updated. No additional photo-ID mapping layer is used.

## 7. Decisions that must not be silently reversed

- OSM remains the default map layer.
- Keep the current static architecture.
- CSV remains the location-data source of truth.
- Do not add `PhotoID`, `image_count`, `cover_image`, or photo-URL columns solely for the map-photo feature.
- Use location `ID` for photo association.
- Use `StoreType` for the visible Categories filter.
- New filter enumeration values must remain visible without code changes.
- Photos are discovered lazily and cached; do not scan every location at initial map load.
- Popup centering refers to the popup card, not the marker.

## 8. Known code-quality risks

The project has historically been edited through manual copy/paste. Common regressions included:

- Duplicate constant declarations.
- Missing or extra braces.
- JavaScript strings broken by accidental line breaks.
- Old and new photo logic coexisting.
- Changes applied to cluster mode but not individual-marker mode.
- Mobile positioning overridden by desktop CSS.

Codex should cleanly implement and verify changes in the repository instead of giving Steve fragmented manual edits.

## 9. Next recommended engineering work

Priority order:

1. Review and stabilize current `index.html` without changing approved UX.
2. Add deterministic custom `StoreType` ordering with automatic fallback for new values, if Steve confirms the desired order.
3. Bind the R2 bucket to a stable production image domain and migrate the single base URL through one configuration constant.
4. Extract repeated constants/configuration into a clearly labeled section while keeping the static architecture.
5. Add lightweight browser smoke tests for:
   - initial map load;
   - CSV parsing;
   - category filtering via `StoreType`;
   - cluster toggle;
   - popup centering in both marker modes;
   - photo discovery for zero, one, and multiple photos;
   - layer switching and fallback;
   - mobile control positioning.
6. Produce the operations SOP after the final photo-domain configuration is fixed.

## 10. Definition of done for future changes

A Codex task is not complete until:

- The current repository was read before editing.
- The requested behavior works.
- Existing approved features still work.
- Desktop and mobile were checked when relevant.
- Cluster and non-cluster modes were checked when relevant.
- Browser console has no new syntax/runtime errors.
- Repository documentation was updated if the decision or operational rule changed.
