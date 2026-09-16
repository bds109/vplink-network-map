# Operations Release Reports

Every VPLINK Map production data update or production code release must have a release report in this directory before the task is closed.

## Data-source rule

Operations accepts the user-supplied original XLSX workbook as the source. Export only the `VPL门店地图信息` worksheet (the store-list sheet) to the dated CSV archive and stable operational CSV; do not publish a separately supplied CSV. Preserve the required headers and normalize coordinate values to the worksheet’s displayed precision before validation.

## Reports required for every actual production update

1. **Local release report** — release commit, validation, rollback source, and anomalies.
2. **Operations data-update report** — date, update scope, added/removed/changed locations, current point totals, and operational next step only. It contains no code, hash, console, or other technical detail.

## Required report content

- release date, type, input and published files;
- production commit and exact rollback source;
- old/new data metrics and material changes (for CSV releases);
- validation performed, production evidence, and any uncovered areas;
- anomalies, impact, and escalation owner.

## Weekly-report handoff

After each production release, Operations must add a concise, factual entry to:

`/Users/steve/Documents/PI Agent/云普周报/inputs/VPLINK_MAP_RELEASES.md`

The weekly-report task uses that file as the current source for VPLINK Map status. It must report business-relevant release outcomes and operational data changes, not routine implementation defects unless specifically requested.
