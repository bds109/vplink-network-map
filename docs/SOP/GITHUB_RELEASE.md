# GitHub Release

## Purpose

Define the safe release process for any map code change so production is updated only after backup and test verification.

## Steps

1. Read the current repository, including `README.md`, `docs/PROJECT_HANDOFF.md`, `index.html`, the operational CSV, and relevant GeoJSON files.
2. Record the current production state as the rollback backup before publishing any code change.
3. Implement the requested code change in the repository with the smallest complete diff.
4. Produce a separate test environment for validation before updating production.
5. Verify the requested change in the test environment.
6. Re-check existing approved behavior that could regress, especially desktop/mobile layout, cluster and non-cluster marker modes, popup positioning, filters, photos, and map layers.
7. Check the browser console for syntax errors and runtime failures in the test environment.
8. Publish to the production GitHub Pages environment only after test verification is confirmed.
9. Record what changed, how it was tested, and the release commit ID.

## Notes

- Do not publish untested code directly to production.
- Backup comes before production release, not after.
- The test environment can be local or staging, but it must be separate from the live production page.
- If the test result is not clearly verified, stop before production release.
