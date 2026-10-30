---
id: TASK-112
title: つぼみの名前とブランチの作成・削除日時を保存する
status: Done
assignee:
  - '@claude'
created_date: '2026-10-30 18:06'
updated_date: '2026-10-30 20:34'
labels:
  - storage
  - v1
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - gui/src/components/BudPanel.tsx
  - gui/src/components/BranchPanel.tsx
  - README.md
priority: medium
type: enhancement
ordinal: 111000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
つぼみにはメッセージ欄がなく、複数あると変更ファイルでしか見分けられない。ブランチには作成日時も削除日時もない。これらは記録を始める前のデータを後から取り戻せないため、V1のうちに追加する。アプリは未運用のため、V1の保存形式を直接変更してよい。形式番号は1のままとし、旧構造からの移行は用意しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 つぼみに任意の名前を保存でき、CLIの保存時と保存後の編集で設定・変更できる。自動退避のつぼみは未設定でよい
- [x] #2 つぼみの名前がCLI、JSON、GUIのマップと詳細に表示され、GUIから編集できる
- [x] #3 ブランチの作成日時と削除日時が保存され、CLI、JSON、GUIのブランチ詳細で確認できる
- [x] #4 つぼみの復元とブランチ名の変更で、名前と作成日時の扱いが文書化されている
- [x] #5 自動テストで保存、編集、削除、ゴミ箱からの復旧を検証し、README.mdとgui/README.mdを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add buds.name, branches.created_at and branches.deleted_at. 2. CLI: bud --save --name and bud --rename. 3. Expose in JSON and GUI (bud detail edit, map label, branch detail dates). 4. Tests and docs.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added branch --deleted and deleted_branches in tree JSON so deletion times are visible. Names are one line, 256 characters; automatic buds stay unnamed; a restored bud ends with its name.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Buds can be named via bud --save --name, bud --rename and the GUI; branches record created_at and deleted_at, exposed through CLI, JSON and GUI. Verified with tests/test_bud_names_branch_times.py, BudPanel and SproutMap component tests, 549 pytest passes and 140 GUI tests.
<!-- SECTION:FINAL_SUMMARY:END -->
