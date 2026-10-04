# Vplink Map Changelog

Production releases are recorded here. Preview-only releases are documented internally and are not Production versions. Add an entry for every Production release, and distinguish Code/UI releases from Operations data releases.

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
