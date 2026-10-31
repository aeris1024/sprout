---
id: TASK-125.14
title: 代表プレビュー指定を廃止し表示順と置き換え機能を維持する
status: Done
assignee:
  - '@codex'
created_date: '2026-10-31 07:49'
updated_date: '2026-10-31 11:16'
labels:
  - cli
  - gui
  - usability
dependencies: []
references:
  - src/sprout/cli.py
  - src/sprout/repository.py
  - src/sprout/archive.py
  - src/sprout/trash.py
  - gui/src/components/PreviewPanel.tsx
  - gui/src/App.tsx
  - tests/test_preview_metadata.py
  - tests/test_previews.py
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 138000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ユーザーが確定したプレビュー整理方針を実装する。代表プレビューの独立した指定・解除・表示を廃止し、重要な添付は既存の表示順で先頭へ移動できるようにする。サムネイルとプレビューは別機能として維持する。
プレビューの置き換えは残す。同じ一覧項目のまま中身だけを差し替える操作として、添付ID・表示位置・作成日時・表示名・説明を維持し、置き換え前の内容はゴミ箱に保持する。素材関連付けも廃止すると確定したため、関連付け廃止はTASK-125.13へ委ね、このタスクの完了条件として素材関連付けの恒久維持を要求しない。
対象にはGUIの代表チェック・代表バッジ、CLIの代表指定オプション、JSON・アーカイブ・ゴミ箱復旧・テスト・文書の整合を含める。既存is_primaryの保存上の扱いも整理するが、添付原本・表示順や他のメタ情報を巻き添えに消さない。V1方針を維持し、バージョン番号の引き上げや保存形式の旧版互換処理をこのタスク登録で追加決定しない。今回の依頼はBacklog反映だけであり、実装は未着手。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 GUIとCLIで代表プレビューを指定・解除する操作と代表表示を廃止し、JSON・アーカイブ・ヘルプ・文書も代表という概念に依存しない
- [x] #2 プレビューの順序を保存・復元でき、先頭へ移すことで重要な添付を上に置ける。順番の変更でサムネイルや添付内容を変更しない
- [x] #3 追加・削除・取り出し・表示と置き換えを維持し、置き換えではID・位置・作成日時・表示名・説明を維持する
- [x] #4 置き換え前の内容をゴミ箱から従来の競合条件で復旧でき、代表指定が復旧によって再び有効な機能として現れない
- [x] #5 既存の代表指定を含むデータ・復旧記録の扱いを整理し、プレビュー原本・順序・他のメタ情報を失わず、V1方針と整合する
- [x] #6 代表指定廃止と順序・置き換え・復旧・失敗時の無変更をCLI/GUI/serve/アーカイブの関連テストで検証する
- [x] #7 素材関連付け廃止はTASK-125.13、ラベル維持・一覧・候補はTASK-125.15/125.16へ委ねる。廃止予定の素材関連付けを代表指定廃止後の恒久維持条件にせず、ラベルを変更しない
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Retain V1 physical storage layout while retiring primary preview as a functional/public concept. 2. Remove primary options, JSON fields, GUI controls, archive presentation and restoration semantics; preserve existing preview files, order and other metadata. 3. Verify replacement/restoration/ordering and stale stored primary markers with backend, CLI, serve and GUI regressions. 4. Update documents/sample generation and finalize after objective checks.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Removed primary preview controls/options, public metadata field and archive badge. V1 physical is_primary column/index remain inert, with no schema change, migration or compatibility mechanism. Raw recovery rows retain their existing shape for exact conflict checks; public trash change descriptions omit the retired field, and recovered markers have no functional representation. File associations remain unchanged for TASK-125.13. Verification: preview metadata/previews/trash/archive/cache tests 74 passed; sample repository and serve tests 9 passed; full GUI suite 236 passed; TypeScript and Vite build succeeded. A regression injects a stored V1 primary marker and checks old flag rejection without changes, JSON/serve omission, persisted reordering, replacement identity/metadata and delete/replace recovery. git diff check succeeded with cr-at-eol for existing README CRLF.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Removed primary preview as a user-facing and API concept while preserving saved order, replacement identity, original files, other metadata and exact recovery conflict checks. Verified 83 relevant backend tests, 236 GUI tests, typecheck and production build. V1 physical layout remains unchanged; material association removal belongs to TASK-125.13.
<!-- SECTION:FINAL_SUMMARY:END -->
