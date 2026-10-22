# Map → Gallery catalog synchronization

The `Gallery catalog sync` GitHub workflow updates only the existing Gallery D1 `stores` catalog. It never calls the Gallery application, uploads media, changes accounts, deploys Workers, or changes DNS. No package installation or local Gallery checkout is needed.

## Source and import contract

- Authoritative input: main branch root `VPL门店地图信息.csv`, not Preview or a dated archive.
- `read-map-catalog.py` is an exact copy of Gallery's reader. `catalog.mjs` is the unchanged pure `fields`/`values`/`planCatalog`/`catalogOperations` section of Gallery's `scripts/import-catalog.mjs` (GALLERY-PROD-003 baseline). Runtime/local-storage imports and CLI are deliberately excluded. When updating either upstream importer, review and synchronize these copies explicitly; tests do not fetch another repository.
- Require ID uniqueness, valid nonblank rows, coordinates, current `index.html` state mapping, Category and both explicit brand columns. Empty rows are ignored; brand membership and photo ownership are never inferred.
- Before any D1 access, downloaded GitHub main CSV, checked-out CSV and published `https://map.vplink-automaten.de/` CSV must be byte-identical (SHA-256). Poll up to 12 times, 30 seconds apart, then fail without writing. Recheck main revision and source immediately before an actual write. A concurrent main change stops the run; rerun on current main.
- Reuse the existing planner and operations. Add/update by ID. Missing production stores become `map_present=0`; they are not deleted. The existing Gallery contract combines `catalog_active` and `map_present` for upload eligibility; historical photo records and store IDs stay intact. Returning stores become present/active again.
- Block source/ID conflicts, more than **5** newly missing stores, or more than **10%** of currently present production stores. There is no workflow input bypass. A legitimate larger removal requires separate review and an approved threshold/code change.
- Compile planned operations into **one atomic SQLite INSERT … SELECT … ON CONFLICT** statement. A full stores-snapshot comparison in that statement prevents overwriting a concurrent catalog edit. No DELETE/REPLACE, migration, or write to another table. D1 timeouts are treated as uncertain outcomes: never blindly resend the old write. A complete rerun re-reads and re-plans, making retries safe and idempotent.

## Operation

Workflow: `.github/workflows/gallery-catalog-sync.yml`

1. Automatic trigger: main push changing only the path selector `VPL门店地图信息.csv` (other files can coexist in that push, but Preview/archive changes alone do not trigger it).
2. Daily reconciliation: **06:23 UTC**, subject to GitHub scheduling delays. This is also a recovery path for missed push events. GitHub may disable schedules in inactive public repositories; maintainers must monitor Actions.
3. Manual: Actions → Gallery catalog sync → Run workflow → main. No force/delete parameters.
4. Runs share one concurrency group and never cancel an in-flight write. Each run checks out latest main, not stale event data.
5. Required repository Secret: **`CLOUDFLARE_API_TOKEN`**. Use a dedicated Cloudflare token with only the existing account's D1 read/write capability; no Worker/R2/DNS/token-administration permissions. If Cloudflare only supports account-level D1 scope, it is not a single-database-scoped credential. GitHub cannot reveal a saved Secret or prove its permission scope; the actual run establishes D1 usability, not token least privilege.

## Evidence and failure alerts

Each run produces a job summary and a 30-day `gallery-catalog-sync-<run>-<attempt>` artifact containing `result.json`: commit, source hash, timestamps, planned IDs/changed fields/counts, before/after store/photo counts, outcome, and separate Cloudflare control-call ledger. No credentials, full database rows, customer data or photo contents are included. Tests use local SQLite only; Gallery HTTP request count remains zero.

Failure keeps Actions red, writes an error annotation, and creates/comments on the open `[Gallery sync] Production catalog synchronization failed` GitHub issue. This requires `issues: write`; all other repository access is read-only. GitHub's email/mobile delivery depends on the maintainer's notification subscriptions; no external notification service is configured. If alert creation itself fails, the run still remains red. Review and close the alert after a successful retry; success does not silently close an unresolved issue.

After resolving a source publication mismatch, validation issue, token problem or concurrent catalog edit, use workflow_dispatch on **main**. Do not roll back the approved Map release merely to match Gallery. Preserve artifacts before their retention expires if needed for audit.

## Local validation

From the Map repository root:

```sh
node --test scripts/gallery-sync/sync.test.mjs
node --check scripts/gallery-sync/sync.mjs
```

Requires Node 22+ and Python 3 with standard-library SQLite. Tests cover add/change/missing/restore, idempotence, source mismatch/wait/network failure, invalid input/source conflicts, major removals, concurrent changes, SQL rollback/retry, and photo/customer preservation. They make no network requests. Do not run `sync.mjs` locally merely as a test: it is the production control-plane entry point when a token is present.

GALLERY-PROD-003 live acceptance is a **no-diff run**, expected stores **120**, photos **5**, writes **0**. Mutation behavior is tested only in isolated SQLite using the real production schema/snapshot; never inject test stores or photos into production.
