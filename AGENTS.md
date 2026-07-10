# VPLINK Online Map — Codex Working Rules

## Project position

This repository is the **VPLINK Online Map** subproject under the broader **Germany Project**. It is not a standalone business program and must not expand into unrelated Germany Project work.

## Collaboration model

- Steve defines the business goal and approves visible results.
- GPT acts as architect, product reviewer, and knowledge owner.
- Codex is the implementation executor for code, tests, repository maintenance, and documentation updates.
- Do not ask Steve to locate functions, infer code positions, or manually merge fragmented edits when Codex can implement and verify the change directly.

## Mandatory workflow

1. Read the current repository before proposing changes. Never work from remembered or pasted old code when newer repository code exists.
2. Inspect `index.html`, the current CSV, GeoJSON/configuration files, and the documentation in `docs/` before implementation.
3. Keep the existing static GitHub Pages architecture unless a confirmed requirement makes a change necessary.
4. Make the smallest complete change that solves the requested problem. Do not redesign unrelated UI or architecture.
5. Test desktop and mobile behavior when the change affects layout, popup positioning, controls, filtering, clustering, images, or map layers.
6. Check the browser console for syntax errors and failed runtime logic before declaring completion.
7. Preserve all existing working behavior unless the task explicitly changes it.
8. After an approved functional change, update the relevant document in `docs/` so the repository remains the source of truth.

## Current technical baseline

- Static HTML/CSS/JavaScript application.
- Leaflet 1.9.4.
- Leaflet.markercluster 1.5.3.
- Papa Parse 5.4.1.
- GitHub Pages deployment from this repository.
- Main data file is the repository CSV referenced by `index.html`.
- Germany border/state overlays are repository GeoJSON files.
- Default map layer is OpenStreetMap.
- Manual map styles include OSM, Carto Light, Carto Dark, Esri satellite with label overlay, and Amap.
- Automatic tile fallback is OSM → Carto Light → Amap.
- Cluster and non-cluster marker modes must both remain functional.

## Image system baseline

- Cloudflare R2 public base URL currently used by the code:
  `https://pub-3575d79a89e1428486f35743798eab42.r2.dev`
- Images are associated by the CSV `ID` field.
- Naming format is `<ID>-<two-digit sequence>.jpg`, for example:
  - `120-01.jpg`
  - `120-02.jpg`
  - `120-03.jpg`
- The CSV must not require image URLs, image count, cover-image index, or a separate photo ID.
- Photos are discovered only when the popup is used, not during initial map load.
- Discovery checks sequential images and stops at the first missing image.
- The discovered image list is cached in memory per store ID.
- A location with no first image must not show a broken image area.

## Data and filtering rules

- `ID` is the location identifier used for image association.
- The left panel title remains **Categories**.
- The category filter and category count read the CSV `StoreType` field.
- Popup wording may still present this value as Category if that is the approved UI wording.
- New `StoreType` values must never disappear or cause errors.
- If custom ordering is introduced, known values may use a configured priority list, while unknown/new values must be appended automatically using a deterministic fallback sort.

## UX rules already approved

- Desktop and mobile layouts are both required.
- Filter panel uses the existing glass-style visual language.
- Statistics card is in the upper-right area.
- Map style switcher is in the lower-left area and must not conflict with mobile browser chrome or right-side controls.
- Zoom, reset, and cluster controls are in the lower-right area.
- Popup must be centered as a popup card, not merely by centering the marker.
- Popup and enlarged-photo navigation must work for variable photo counts.
- Do not introduce popup scrolling merely to compensate for incorrect popup positioning.

## Safety rules for edits

- Avoid duplicate `const`, unmatched braces, malformed string concatenation, and line-break damage inside JavaScript strings.
- Do not use broad search instructions in user-facing guidance. When manual action is unavoidable, provide one unique search target and the complete replacement block.
- Do not claim a fix is complete until syntax and core interactions are verified.
