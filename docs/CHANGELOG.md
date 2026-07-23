# Changelog

## Purpose

Track repository-level map changes that affect implementation, validation flow, or release safety.

## Current Status

- 2026-07-18: cleaned redundant CSS and repeated popup/photo helper logic in `index.html` without changing approved map behavior.
- 2026-07-18: added a backup-first, local test-environment smoke-check workflow before any production release.
- 2026-07-18: added a fixed GitHub Pages preview path at `/preview/` and a generator script for preview publication.
- 2026-07-23: added a branch-scoped Shiny title preview for the top map heading with a darker base color and slower high-contrast sweep.

## Notes

- Latest cleanup was validated in a separate local test environment before any production publication step.
