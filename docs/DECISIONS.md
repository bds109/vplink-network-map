# Approved Decisions

This file records durable decisions. Codex must not reverse them without explicit user approval.

## Project and workflow

- The repository is the VPLINK Online Map subproject under Germany Project.
- GitHub is the source for code, CSV, and map configuration/data files.
- Future coding work should continue in Codex using repository branches and reviewable diffs.
- ChatGPT remains responsible for product architecture and review; Codex executes.

## Basemaps

- OpenStreetMap remains the default basemap.
- Available manual options: OSM, CARTO Light, CARTO Dark, satellite with labels, Amap.
- Automatic failure order: OSM → Light → Amap.
- The earlier separate terrain option was dropped.

## Layout

- Basemap switcher: bottom-left.
- Zoom, reset, and cluster toggle: bottom-right.
- Location summary: top-right.
- Desktop title must not overlap summary.
- Mobile controls must not cover the summary or browser UI.

## Popup

- Keep glass/translucent appearance.
- Popup card must be fully visible after opening.
- Centering logic applies in both cluster and non-cluster modes.
- Do not solve popup visibility by adding an unnecessary internal scrollbar.

## Filters

- Left filter heading remains `Categories`.
- Category list, counts, filtering, and unique-category statistic read `StoreType`.
- New StoreType values must appear automatically.
- When custom ordering is implemented, unknown values are appended safely, preferably alphabetically.

## Photos

- Use CSV `ID` as the image association key.
- Do not add PhotoID.
- Do not add image count, cover image, or image URL maintenance columns.
- R2 naming format is `{ID}-{NN}.jpg`, beginning at `01`.
- All photos can remain in one R2 directory.
- Sequence numbers must be continuous; lookup stops at the first missing sequence.
- Load photos lazily, not at initial map load.
- Cache discovered photo lists in the browser session.
- Hide the entire photo region when `01` does not exist.
- Use image-load probing, not HTTP HEAD requests.

## Data lifecycle

- CSV is the source of truth.
- Planned IDs can later change to final installed IDs.
- When an ID changes, update CSV normally and rename the related R2 image files.
- Avoid a second mapping layer that creates operational reconciliation work.