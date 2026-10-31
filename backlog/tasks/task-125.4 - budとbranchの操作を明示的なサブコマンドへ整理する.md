---
id: TASK-125.4
title: budとbranchの操作を明示的なサブコマンドへ整理する
status: To Do
assignee: []
created_date: '2026-10-31 07:23'
updated_date: '2026-10-31 09:33'
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
- [ ] #1 bud save/list/restore/rename/deleteを利用でき、saveの通常動作とkeep-files、名前の指定・解除を保持する
- [ ] #2 bud restoreは成功時に元のつぼみを消費し、別の未保存変更があれば先に退避する。失敗時は元の作業とつぼみを失わない
- [ ] #3 branch list/create/rename/comment/deleteと削除済み一覧を利用でき、作成起点の省略・明示とコメントの既存機能を維持する
- [ ] #4 branch switchを正規入口として新設せず、作成後の移動と未保存変更は本タスク時点の既存動作を維持する。TASK-125.9で後からgoへ統合するため、本タスクの完了を後続TASK-125.9の完了条件に依存させない
- [ ] #5 現在ブランチの削除拒否とゴミ箱復旧、つぼみやブランチ操作の拒否時の無変更・JSON/終了コードを検証する
- [ ] #6 list/create等と同じ文字列のブランチ名・つぼみ名でも名前として操作できる
<!-- AC:END -->
