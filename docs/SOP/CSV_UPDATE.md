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

## Original-file provenance (GALLERY-DEV-06 Production rollout, 2026-10-23)

After validation/replacement and before an explicitly approved data release:

```sh
node scripts/gallery-sync/source.mjs '/absolute/path/to/the-actual-original-upload.csv'
```

The helper does **not** modify the CSV, contact D1 or publish anything. Original and runtime CSV bytes may differ, but an association must be verified, not merely declared by filename or hashes. The existing CSV paths remain `identity-v1` (identical bytes) and `csv-normalize-v1` (replay the repository's deterministic Python CSV normalizer and require its output to match the final CSV exactly). The latter handles UTF-8 BOM, CRLF/LF and CSV quoting/serialization while preserving every parsed cell, header, row and order; it does not approve arbitrary business-data edits.

### XLSX worksheet provenance (`xlsx-sheet-v1`)

For an approved original XLSX, explicitly supply the worksheet; there is no first-sheet/default-sheet fallback:

```sh
python3 scripts/gallery-sync/xlsx-sheet.py 'approved worksheet' < '/actual/original-upload.xlsx' > '/private/candidate.csv'
# Only after byte-for-byte comparison with the approved candidate and authorized replacement:
node scripts/gallery-sync/source.mjs '/actual/original-upload.xlsx' 'approved worksheet'
node scripts/gallery-sync/register-source.mjs '.pi/map-data-sources/<UUID>.json' '/actual/original-upload.xlsx'
```

`xlsx-sheet-v1` uses only Python's standard library. It preserves explicit worksheet rows, column order, cell text and blank cells/rows; numeric Latitude/Longitude are Decimal-rounded to eight decimal places (half-even), with trailing zeroes trimmed, matching the approved export contract. Output is UTF-8 without BOM, LF, minimal CSV quoting. Formulas, error/unsupported cell types, missing/ambiguous worksheets, malformed workbooks and output mismatches are rejected. No business edits or schema migration are permitted to make a hash match. The private proof includes the explicit `worksheet` and the SHA-256 of `xlsx-sheet.py` in `normalizerSha256`; its binding appends the worksheet to the existing six-element binding. Both CSV proof methods retain their original binding bytes. Registration replays the actual workbook against the runtime CSV; hashes/JSON alone are insufficient. The public marker still has exactly three opaque fields and contains no original name, workbook fingerprint, worksheet or proof. Gallery's admin-only validator must support the new method before this release; customers/public routes remain denied. Source registration remains a separately authorized write to the existing `map_sync_history`, never a sync success.

For a formatting-only CSV conversion, prepare/validate a candidate outside the live runtime file first:

```sh
python3 scripts/gallery-sync/normalize-source.py < '/actual/original-upload.csv' > '/private/candidate.csv'
```

After the separately approved candidate replacement, run the provenance helper on the actual original upload as above. It records **both** `originalSha256` and final `csvSha256`, method, normalizer-code fingerprint and an integrity binding over original basename/input fingerprint/output fingerprint/data-version UUID. The binding is an audit digest, not an authentication signature; registration requires the authorized publisher to replay against both actual files.

The helper writes an **opaque public** `map-data-source.json` (final CSV SHA-256 + independent data-version UUID, no original filename/input fingerprint), and a mode-0600 **private** `.pi/map-data-sources/<UUID>.json` containing the basename, separate fingerprints and verified association proof. Never commit, place under the static site, or upload that private file to GitHub/Hub. It refuses to overwrite existing public metadata: preserve the old release record and deliberately remove only that metadata before preparing the next version. Never use the runtime CSV as a stand-in for a lost original upload.

As part of a separately approved data release, register the private record in the **existing** Gallery D1, using its existing dedicated D1 control-plane credential (never print it):

```sh
node scripts/gallery-sync/register-source.mjs '.pi/map-data-sources/<UUID>.json' '/actual/original-upload.csv'
```

This command is a D1 metadata write and requires publication authorization; it was **not run online in GALLERY-DEV-06**. It requires the actual original file (including the recorded basename), validates both file fingerprints, replays the approved conversion and checks the current CSV/public marker, then records an immutable, publication-unverified `result='source'` row in `map_sync_history`. Self-declared mapping JSON/hashes without those files are rejected. D1 keeps `original_sha256` separately from final `source_sha256`, with `source_proof` binding them to the filename and data version. It does not touch stores or claim publication/sync success. An identical registration is idempotent; a conflicting filename/hash for the same version is rejected. Register before the approved CSV + opaque-marker push, so Actions can resolve the original filename privately. For a data-only release, only those two public data files and approved docs belong in the release commit. An explicitly approved protocol release may include its minimal protocol implementation and tests in the same focused commit.

The helper cannot know a future publication time. After the release is actually served, existing Gallery Actions verifies checkout/GitHub main/Production CSV **and** metadata, finds the exact data-release commit's successful GitHub Pages build, and records its `updated_at` receipt time plus release commit in D1 and the run artifact. The original filename is read only from the private registered row, stays in D1, and is omitted from Actions console/summary/artifacts. Unregistered named versions cannot sync. It does not substitute the upload/preparation/commit time. Missing/skipped/expired build receipts block confirmation for a named release; investigate and rerun, never invent a timestamp. Read-only verification on 2026-10-23 confirmed the real current data-release commit has an accessible successful build receipt; evidence is in `GALLERY-DEV-06-REVIEW/pages-receipt-verification.json`. That check used existing `gh` authentication, not a new Actions run or a production data write. `page_build` supplies a retry after Pages finishes, in addition to CSV/metadata push, daily reconciliation and manual dispatch.

New formal releases must have a matching public marker **and private registration**. Missing either is `SOURCE_REGISTRATION_MISSING` / 「来源登记缺失」, not an ordinary pending version or a filename that was somehow already recorded; synchronization stops before business writes. A bad association is also rejected. The sole historical exception is the explicitly pinned pre-provenance Production CSV fingerprint in `LEGACY_SOURCE_SHA256` (same constant in Map and Gallery), before any successful modern-version sync. Only that baseline can retain filename/time **unrecorded**. Any other no-marker bytes, or removal of the marker after modern publication—even on return to the baseline bytes—is anomalous. This is a one-time grandfathered source, not a wildcard for future releases. A present but mismatched/malformed provenance file is an error, not a reason to silently fall back to legacy. Old source names are never backfilled. The administrator-only Gallery page independently compares current published bytes/opaque version with private registration and successful history, so a new version without a completed sync is not shown as synchronized. Private source rows are excluded from the 20 synchronization-attempt rows. Customers, the public static marker, Actions logs and repository history must not receive the original filenames or internal synchronization history.

The GALLERY-DEV-06 Production rollout was explicitly approved on 2026-10-23. The existing Gallery D1 received only `0006_map_sync_history.sql`; original Worker/UI version `f5318ca7-8820-4be0-baeb-70234eab9bbe` is deployed with original accounts, secrets, bindings and domain retained. The reviewed workflow/scripts are released together with this provenance procedure. No current Production source name is backfilled and no provenance marker is created for the unchanged legacy CSV. Future data releases still require their own explicit approval and verified private registration.
