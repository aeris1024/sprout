---
id: TASK-125.4
title: budとbranchの操作を明示的なサブコマンドへ整理する
status: To Do
assignee: []
created_date: '2026-10-31 07:23'
updated_date: '2026-10-31 07:36'
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
switchと全体restoreを含む移動系はTASK-125.9でgoへ統合する。branch switchを正規の別入口として追加しない。作成直後の移動や未保存変更の扱いはgo統合タスクで確認した方針にそろえる。
Gitのstash apply相当の追加は含めない。つぼみの消費・退避、ブランチの作成起点・コメント・削除の意味を維持する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 bud save/list/restore/rename/deleteを利用でき、saveの通常動作とkeep-files、名前の指定・解除を保持する
- [ ] #2 bud restoreは成功時に元のつぼみを消費し、別の未保存変更があれば先に退避する。失敗時は元の作業とつぼみを失わない
- [ ] #3 branch list/create/rename/comment/deleteと削除済み一覧を利用でき、作成起点の省略・明示とコメントの既存機能を維持する
- [ ] #4 branch switchを正規入口として追加せず、作成後の移動はTASK-125.9で確認したgoの方針と失敗時の整合にそろえる
- [ ] #5 現在ブランチの削除拒否とゴミ箱復旧、つぼみやブランチ操作の拒否時の無変更・JSON/終了コードを検証する
- [ ] #6 list/create等と同じ文字列のブランチ名・つぼみ名でも名前として操作できる
<!-- AC:END -->
