---
id: TASK-86
title: 現行の保存構造をV1として整理する
status: Done
assignee:
  - '@codex'
created_date: '2026-10-30 16:21'
updated_date: '2026-10-30 16:28'
labels: []
dependencies: []
type: enhancement
ordinal: 85000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ユーザー指定に従い現行の機能と保存構造を新しい初期形式V1とする。開発中の形式履歴、旧形式SQL固定資料、移行・互換性説明を除去し、現行形式とデータ整合性の検査に整理する。既存の利用者DBを変換する処理は追加しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 新規DBとゴミ箱記録が現行構造のVersion 1として保存・再オープンできる
- [x] #2 旧形式の固定SQLと互換性・移行説明を除去し現在の保存構造の説明に統一する
- [x] #3 不正構造や未知の番号の非変更拒否を維持し関連テストが成功する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Reset DB and trash record version numbers to 1, preserve current schema/features and integrity validation, remove historical fixtures and compatibility/migration prose, simplify validation guidance and update tests, verify and integrate through the normal branch workflow.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reset the current complete DB schema and trash record version to 1 without rolling back any features. Removed four historical schema SQL fixtures and their frozen/legacy tests, compatibility/migration/backup-reinitialization prose, and historical-format hints in validation errors. Kept current structure/encoding/reference/recovery validation and nonmutating rejection of invalid data. Renamed storage tests and pending-recovery validator to describe current validation. Verified full Python run: 510 passed, 19 skipped; after final test/name cleanup, storage-validation and restore-safety suite: 115 passed, 17 skipped, including persisted DB/trash version 1 and restore roundtrip. GUI App tests: 66 passed; diff check and scan for historical format/compatibility prose passed. Existing user databases were not mutated.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Treat the current complete storage structure as initial V1, with trash records also at version 1. Remove historical schema fixtures, compatibility/migration documentation and legacy-only tests while preserving integrity validation. Verified full Python regression run, final storage/recovery checks and 66 GUI tests.
<!-- SECTION:FINAL_SUMMARY:END -->
