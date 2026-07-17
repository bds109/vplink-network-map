# CSV Update

## Purpose

Define the simplest safe process for updating map data without changing code.

## Steps

1. Prepare the new CSV using the approved repository field structure.
2. Replace the repository file `VPL门店地图信息.csv` with the new content.
3. If needed, keep an additional dated archive copy such as `VPL门店地图信息_20260717.csv`.
4. Commit and push the updated CSV.
5. Verify the live map still loads and the filters/popup data render correctly.

## Notes

- `index.html` should continue reading `VPL门店地图信息.csv`.
- Do not change the code only because the data date changed.
- Keep required fields such as `ID`, `StoreName`, `State`, `City`, `StoreType`, `Address`, `Latitude`, and `Longitude`.
