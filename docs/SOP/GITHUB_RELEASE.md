# GitHub Release

## Purpose

Define the safe release process for any map code change so production is updated only after backup and test verification.

## Steps

1. Read the current repository, including `README.md`, `docs/PROJECT_HANDOFF.md`, `index.html`, the operational CSV, and relevant GeoJSON files.
2. Record the current production state as the rollback backup before publishing any code change.
3. Implement the requested code change in the repository with the smallest complete diff.
4. Regenerate the GitHub preview page with `scripts/build_preview.py`.
5. Publish the preview page at `https://map.vplink-automaten.de/preview/`.
6. Verify the requested change in the preview environment.
7. Re-check existing approved behavior that could regress, especially desktop/mobile layout, cluster and non-cluster marker modes, popup positioning, filters, photos, and map layers.
8. Check the browser console for syntax errors and runtime failures in the preview environment.
9. Publish to the production GitHub Pages root only after preview verification is confirmed.
10. Record what changed, how it was tested, and the release commit ID.

## Notes

- Do not publish untested code directly to production.
- Backup comes before production release, not after.
- Preferred test environment: the fixed GitHub Pages preview path at `/preview/`.
- If the test result is not clearly verified, stop before production release.
