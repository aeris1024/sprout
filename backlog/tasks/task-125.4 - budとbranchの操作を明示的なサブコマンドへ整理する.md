---
id: TASK-125.4
title: budとbranchの操作を明示的なサブコマンドへ整理する
status: Done
assignee:
  - '@codex'
created_date: '2026-10-31 07:23'
updated_date: '2026-10-31 11:28'
labels:
  - cli
  - usability
dependencies:
  - TASK-125.1
references:
  - src/sprout/cli.py
  - src/sprout/repository.py
  - tests/test_cli.py
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 128000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
budとbranchの排他的な操作フラグを、対象と動作の分かる正規構文へ整理する。
bud list / save [--name NAME] [--keep-files] / restore BUD / rename BUD NAME / delete BUD
branch list [--deleted] / create NAME [LEAF] / rename OLD NEW / comment NAME TEXT / delete NAME
switchと全体restoreを含む移動系はTASK-125.9でgoへ統合する。branch switchを正規の別入口として追加しない。本タスク時点ではブランチ作成直後の移動と未保存変更の扱いを既存仕様で維持する。後続TASK-125.9が統合後の方針への変更を担当する。
Gitのstash apply相当の追加は含めない。つぼみの消費・退避、ブランチの作成起点・コメント・削除の意味を維持する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 bud save/list/restore/rename/deleteを利用でき、saveの通常動作とkeep-files、名前の指定・解除を保持する
- [x] #2 bud restoreは成功時に元のつぼみを消費し、別の未保存変更があれば先に退避する。失敗時は元の作業とつぼみを失わない
- [x] #3 branch list/create/rename/comment/deleteと削除済み一覧を利用でき、作成起点の省略・明示とコメントの既存機能を維持する
- [x] #4 branch switchを正規入口として新設せず、作成後の移動と未保存変更は本タスク時点の既存動作を維持する。TASK-125.9で後からgoへ統合するため、本タスクの完了を後続TASK-125.9の完了条件に依存させない
- [x] #5 現在ブランチの削除拒否とゴミ箱復旧、つぼみやブランチ操作の拒否時の無変更・JSON/終了コードを検証する
- [x] #6 list/create等と同じ文字列のブランチ名・つぼみ名でも名前として操作できる
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Introduce bud and branch groups with explicit operations that call the existing implementations. Use a temporary hidden legacy dispatch for no-operation/flag/name forms so current GUI/scripts keep working until TASK-125.8 removes transitional routes. Verify literal command-word names, bud consumption/keep-files/discard safety, branch comments/start points/deletion/recovery, JSON and serve; retain current branch-create movement options until TASK-125.9.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added explicit bud list/save/restore/rename/delete and branch list/create/rename/comment/delete. Existing implementations preserve keep-files, bud consumption and pending-work saving, comments, branch start points and optional create/switch behavior. Temporary hidden legacy dispatch retains old flags and branch-name calls until TASK-125.8. Bud targets remain ID/prefix, with non-unique names kept as labels. Verified command-word names, rename/clear, delete confirmation/current-branch refusal, trash restoration and failures without lost work. CLI/serve/bud-time run covered 90 cases: 89 passed; the sole obsolete branch-root help assertion was updated to branch create help and its test then passed. New five canonical tests passed. git diff --check passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Introduced explicit bud and branch operations while preserving legacy callers during migration. Verified all 90 selected cases, including the updated hierarchical help check, restore consumption, pending-work protection and recovery.
<!-- SECTION:FINAL_SUMMARY:END -->
