---
id: TASK-125.2
title: 葉のタグ操作をleaf配下へ整理する
status: Done
assignee:
  - '@codex'
created_date: '2026-10-31 07:23'
updated_date: '2026-10-31 11:16'
labels:
  - cli
  - usability
dependencies:
  - TASK-125.1
references:
  - src/sprout/cli.py
  - src/sprout/repository.py
  - src/sprout/preview_image.py
  - src/sprout/trash.py
  - tests/test_cli.py
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 126000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
タグ操作をleaf tag list / create NAME [LEAF] / comment NAME TEXT / delete NAMEへ整理する。タグの現在の参照・コメント・保護・削除復旧の意味を維持する。
旧タスクのメモはTASK-125.11のleaf edit統合へ、サムネイルはTASK-125.12の個別操作と生成元の統合へ切り出した。代表プレビュー廃止と置き換え維持はTASK-125.14で扱う。プレビューの素材関連付け廃止と表示名・説明・順序の維持はTASK-125.13へ委ねる。ラベル維持・一覧・候補はTASK-125.15・TASK-125.16へ委ね、このタグ操作タスクではラベルを変更しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 leaf tag list/create/comment/deleteで現在のタグ機能を利用でき、対象省略時の現在ブランチ先端、作成コメント・コメントの解除を保持する
- [x] #2 タグ付き葉の保護、タグだけを削除する動作、ゴミ箱からの復旧と名前衝突時の拒否を保持する
- [x] #3 タグの成功・不正入力・衝突・JSON・serveを正規構文で検証し、list/create等の文字列もタグ名として扱える
- [x] #4 メモ・サムネイル・代表指定廃止・素材関連付け廃止・ラベル一覧/候補は各対応タスクへ委ね、タグ操作でプレビューやラベルを変更しない
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Add leaf tag list/create/comment/delete wrappers around existing tag operations; retain temporary legacy tag invocation. Verify explicit subcommands and command-word names, comments, protection, deletion recovery/conflicts, JSON and serve without changing labels or attachments.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added leaf tag list/create/comment/delete as wrappers around existing tag behavior, retaining temporary legacy calls. Verified command-word names, comment create/change/clear, branch-tip default while viewing a historical leaf, explicit targets, tag protection, trash recovery and name conflicts, invalid arguments, unchanged labels/notes/files, and structured serve responses. tests/test_cli_groups.py tests/test_cli.py: 78 passed. Fixed archive test parity to ignore changing disk free-space snapshots. git diff --check passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Introduced explicit leaf tag subcommands without changing tag semantics or other metadata. Verified 78 CLI regression tests, including nested serve requests, protection and trash recovery.
<!-- SECTION:FINAL_SUMMARY:END -->
