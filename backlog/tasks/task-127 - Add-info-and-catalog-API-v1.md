---
id: TASK-127
title: Add info and catalog API v1
status: Done
assignee:
  - '@codex'
created_date: '2026-11-02 06:27'
updated_date: '2026-11-02 06:38'
labels: []
dependencies: []
ordinal: 142000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the Atelier Shelf API v1 contract in Sprout only; preserve export JSON and storage schema.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Info and catalog satisfy the JSON, text and error contract
- [x] #2 Catalog reads tagged variants and current metadata in one transaction
- [x] #3 Automated and existing test counts are recorded separately
- [x] #4 Real sprout.exe verifies JPEG PNG WebP and export with reproducible fixtures
- [x] #5 Documentation includes examples recovery behavior executable path and limitations
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Add snapshot queries and CLI commands; test contracts concurrency errors and invariants; add real executable verification; run Python and GUI regressions; document evidence and integrate into develop.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented snapshot queries and CLI commands. Windows JSON streams explicitly use UTF-8. Focused API checks pass, including concurrent WAL updates and recovery behavior. Real exe integration verifies three image formats and existing export shape. GUI Vitest: 284 passed; pnpm launcher metadata fetch failed, so installed Vitest was invoked directly.

Final verification: existing Python 759 passed / 0 failed / 20 skipped; final API 21 passed / 0 failed / 0 skipped; GUI 284 passed / 0 failed / 0 skipped. Full Python run contained 20 initial API cases and reported 779 passed / 20 skipped. Real executable script: 30 successful commands and 5 expected rejection cases. Evidence: docs/validation/info-catalog-api-v1.md, info-catalog-api-v1.json, info-catalog-test-results.json.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added info/catalog API v1 with a single SQLite snapshot, deterministic ordering, current annotations and UTF-8 JSON. Preserved existing export JSON and schema. Verified API contracts, concurrent updates, recovery, actual Windows executable exports, Python regressions and GUI tests. Sprout API accepted; Atelier Shelf GUI integration remains pending.
<!-- SECTION:FINAL_SUMMARY:END -->
