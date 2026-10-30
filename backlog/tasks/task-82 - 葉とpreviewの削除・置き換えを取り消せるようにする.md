---
id: TASK-82
title: 葉とpreviewの削除・置き換えを取り消せるようにする
status: Done
assignee:
  - '@codex'
created_date: '2026-10-29T19:07:00Z'
updated_date: '2026-10-30 15:27'
labels: []
dependencies:
  - TASK-80
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - gui/src/App.tsx
  - gui/src/components/CommitPanel.tsx
  - gui/src/components/PreviewPanel.tsx
  - tests/test_delete_commit.py
  - tests/test_previews.py
  - tests/test_v1_storage.py
priority: high
type: feature
ordinal: 81000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
現在はdelete-commitで葉のファイル一覧・添付・メモ・ラベルを削除し、子の親やブランチ先端・現在位置・つぼみ起点も付け替える。previewの削除や置き換え前の内容も操作から戻せず、gcで実体を回収すると復旧できない。制作中の誤操作から回復できるよう、葉とpreviewの削除をゴミ箱から復元し、previewの置き換え前の版へ戻せる機能を追加する。対象は単一の葉の削除、previewの削除・置き換えとし、全操作共通Undo、ブランチ・タグ・メモ・ラベル単体の編集履歴は本件に含めない。非互換構造の扱いはTASK-80に従う。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 削除した単一の葉とpreviewを復旧可能な項目として一覧・識別でき、再起動後も取り消しできる。通常の履歴・添付一覧とは区別する
- [x] #2 葉の削除を取り消す際、保存ファイル・添付・メモ・ラベルと、削除時に変化した親子関係・ブランチ先端・現在位置・つぼみ起点を復旧できる。作業ファイルは無断で変更しない
- [x] #3 削除後の追加操作と参照変更を検査し、後から進めた履歴や同名の別対象を上書きしない。安全に取り消せない場合は理由を示し、部分的な復旧を確定しない
- [x] #4 previewの削除取り消しと置き換え前の版への復帰で、対象の添付ID・内容・元ファイル名・media_type・サイズ・表示順・日時を定義した規則で復旧する。他の添付と順序を壊さない
- [x] #5 復旧可能な項目が必要とするオブジェクトはgcで回収しない。完全削除・保持期限・容量表示・pruneやarchiveでの扱いを明文化し、完全削除前に対象と回収可能容量を確認できる
- [x] #6 CLI・JSON・GUIから対象の確認、復旧、完全削除を行える。破壊的操作には影響と取り消せる範囲を示し、失敗時は構造化エラーを表示する
- [x] #7 ルート/中間/現在位置/枝先の葉、添付削除・複数回の置き換え、再起動、後続操作との競合、gc保護と完全削除、失敗・中断時の整合性を自動テストで検証し、READMEを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Implement approved schema V5 recovery policy: persist original rows, expected post-operation state and protected object references atomically with commit/preview deletion and replacement. Restore only when affected rows/references and preview context still match, atomically reject conflicts and never change working files. Keep exact attachment IDs, order and timestamps; undo replacements newest first. Retain records indefinitely until restoration or explicit permanent deletion, with durable creation-order sequence. Protect objects from gc and prune, inspect shared/protected/reclaimable bytes before purge, and keep trash outside static archives. Expose list/show/restore/purge with dry runs through CLI/JSON and GUI; document compatibility, backup, retention and recovery limits. Verify graph/reference restoration, later-operation conflicts, preview chains, gc/purge, interruption/failure/reopen, schema compatibility and all regression checks.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
User approved retention, conflict, preview-chain, gc/purge and archive/prune policies. Proceed with schema V5 and atomic row patches, validating recorded post-operation state before restoration.

Implemented V5 trash_entries and trash_objects with atomic original/expected row patches, durable creation order and content verification before restore. Preserved frozen V4 schema fixture. All affected metadata/reference rows are checked before restore; FK/identity/order conflicts roll back the entire operation. Added gc protection, accurate shared/reclaimable capacity, explicit purge and archive/prune policy. GUI supports inspection, confirmation, restore, purge and structured refusal without losing items. Added 22 backend recovery tests and 3 GUI flows covering roots/middle/current/tips, buds, reused branches, later commits, per-preview identity/order/timestamps and replacement chains, shared gc protection, purge, archive/prune, trigger failures, interruption rollback/reopen and clock rollback/VACUUM order. Final validation: Python full suite 482 passed, 19 skipped (186.60s); GUI full suite 107 passed; TypeScript noEmit, Vite production build and git diff --check passed. Prune CLI confirmation/JSON regression also passed after final wording check. An earlier transient Windows progress-file replacement access error passed archive rerun and the clean full run.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Add persistent trash for deleted commits, deleted previews and replaced preview versions, with atomic conflict-checked recovery and no working-file changes. Protect recovery objects from gc; provide capacity-aware explicit purge through CLI/JSON/GUI. Introduce schema V5 and document retention, compatibility and backup limits. Verified 482 Python tests, 107 GUI tests, type checks and production build (19 platform skips).
<!-- SECTION:FINAL_SUMMARY:END -->
