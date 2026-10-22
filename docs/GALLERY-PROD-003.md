# GALLERY-PROD-003 — Map → Gallery automatic catalog sync

Approved scope: synchronize the existing Gallery D1 stores catalog after the main production CSV is actually published. No changes to Map pages/CSV, Gallery UI/accounts/photos, Worker deployments, DNS or other services.

Implementation and operation: [`scripts/gallery-sync/README.md`](../scripts/gallery-sync/README.md).

Workflow: [Gallery catalog sync](https://github.com/bds109/vplink-network-map/actions/workflows/gallery-catalog-sync.yml).

- main production CSV push, manual dispatch, and daily 06:23 UTC reconciliation.
- Exact GitHub/checkout/published CSV hash gate; strict validation; reused Gallery importer; atomic incremental upsert with concurrency protection; missing stores retained for history; major-removal blocking.
- Dedicated `CLOUDFLARE_API_TOKEN` repository Secret; credentials never included in source, logs or artifacts. Saved Secret presence does not independently establish its least-privilege scope.
- Red Actions status, summary/artifact and persistent GitHub Issue on failure; fresh-state safe rerun via manual dispatch.
- Local acceptance: 8 isolated tests passed. Additional offline rehearsal using the actual production schema and snapshot passed with all non-store tables unchanged, FK0/integrity ok.
- Live acceptance target: a no-diff manual run with stores120/photos5 and zero writes; do not inject production test mutations. Run-specific evidence and final review are maintained outside this public repository in `GALLERY-PROD-003-REVIEW`.
- Gallery application HTTP test ledger remains 400/400; this task makes no Gallery application requests. Cloudflare control-plane calls are recorded separately.

Wait for ChatGPT final review after execution; this automation does not authorize any unrelated release.
