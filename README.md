# VPLINK Online Map

VPLINK Germany vending-machine network map, maintained as a subproject of the broader Germany Project.

## Project documentation

- [Codex working rules](AGENTS.md)
- [Full project handoff](docs/PROJECT_HANDOFF.md)

## Current stack

- Static HTML/CSS/JavaScript
- Leaflet + Leaflet.markercluster
- Papa Parse
- GitHub Pages
- CSV and GeoJSON files maintained in this repository
- Cloudflare R2 for location photos

## Current operational data file

- The live map reads `VPL门店地图信息.csv`.
- When location data is updated, replace or update this file without changing `index.html`.
- Dated CSV files may remain in the repository as archive snapshots.

## Working model

Future code changes should be implemented and verified in Codex using the current repository as the source of truth. Read `AGENTS.md` and `docs/PROJECT_HANDOFF.md` before making changes.
