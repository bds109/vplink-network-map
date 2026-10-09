# Vplink Map Changelog

Production releases are recorded here. Preview-only releases are documented internally and are not Production versions. Add an entry for every Production release, and distinguish Code/UI releases from Operations data releases.

## 2026-10-09 — Accepted Preview Code/UI promotion

**Release type:** Code/UI

**Production commit:** `4799b41b039c778aa758aab9aa0dd11e584da691`

**Accepted Preview baseline:** `0d15a629fcb9a54009bacf2cb4ae6225339861c8`

### Changes

- Promoted the approved four-page Preview UI: Desktop full-width map beneath a frosted-glass Results/Detail panel, with selected markers kept visible outside the panel; retained Mobile map-first layout.
- Added persistent Desktop location results and selected-store Detail, explicit Search this area / bbox / Show all, filter and URL state sharing, and Directions.
- Promoted mobile Search viewport recovery and fixed page-scoped Geekbar/Dojo filters.
- Added exact CSV `ID` Search priority and `ID: <ID>` result labels while retaining name, City, ZIP and Address search.

### Data status

Code/UI only. Neither the Production runtime CSV nor Preview data was updated; both retain SHA-256 `b18f1262605d7002cd3352f096b135672191fa65492d70da644863bfe0198bb8`. The separate Operations XLSX candidate is not part of this release.

### Validation and limitations

Generated Production pages matched the accepted Preview after normalizing only title, noindex, Preview badge and CSV URL. The CSV validator and JavaScript syntax checks passed; local Chrome checks covered the four Production routes, Desktop/Mobile ID and text Search, brand scope, Detail/Popup, 768/769 transitions, glass layout, individual markers and Area/bbox. Online availability and interaction checks are recorded separately in the release evidence after publication. External-resource reliability, physical devices and Safari are not established by local checks. A pre-existing Mobile immediate-selection startup race remains unchanged.

## 2026-10-04 — Search, filtering and mobile UX

**Release type:** Code/UI

**Production commit:** `2943b2bead0619afde7d1591679f8a9c26f24739`

### Changes

- Added Search v1 for store/location name, City, ZIP and Address. Accent normalization lets `Munchen` match `München`; Search respects the fixed Geekbar and Dojo page scopes.
- Added `Showing X of Y locations` and mobile `Filters (N)`.
- Selecting a Search result replaces conflicting selections within the same filter dimension instead of appending them; compatible selections in other dimensions remain selected.
- Made mobile Search / Filters a compact single-row floating control. Search expands in place and suggestions float over the map without reducing its height.
- Added state mappings `柏林州 → Berlin` and `萨克森州 → Sachsen`.

### Data status

Not a data release. The runtime CSV `VPL门店地图信息.csv` was unchanged (SHA-256: `b18f1262605d7002cd3352f096b135672191fa65492d70da644863bfe0198bb8`).

### Validation and limitations

Production parity preflight and focused local verification passed. All four Production URLs returned HTTP 200 in the online smoke check. Full online browser regression, physical-device testing and Safari testing were not repeated.
