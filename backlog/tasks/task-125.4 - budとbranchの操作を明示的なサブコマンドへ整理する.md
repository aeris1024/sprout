---
id: TASK-125.4
title: budとbranchの操作を明示的なサブコマンドへ整理する
status: To Do
assignee: []
created_date: '2026-10-31 07:23'
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
複数の排他的フラグで操作を選ぶ現状を、対象と動作の分かる正規構文へ整理する。
bud -> bud list、--save -> bud save [--name NAME] [--keep-files]、--restore -> bud restore BUD、--rename -> bud rename BUD NAME、--drop -> bud delete BUD。
branch -> branch list [--deleted]、NAME [START_POINT] -> branch create NAME [LEAF]、switch NAME -> branch switch NAME、--rename -> branch rename OLD NEW、--set-comment -> branch comment NAME TEXT、--delete -> branch delete NAME。
作成コメント、作成後の切り替え、未保存変更を退避して切り替える既存機能も保持する。goとの挙動統合やGitのstash apply相当の追加は含めない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 bud save/list/restore/rename/deleteを利用でき、saveの通常動作とkeep-files、名前の指定・解除を保持する
- [ ] #2 bud restoreは成功時に元のつぼみを消費し、別の未保存変更があれば先に退避する。失敗時は元の作業とつぼみを失わない
- [ ] #3 branch list/create/switch/rename/comment/deleteと削除済み一覧を利用でき、作成起点の省略・明示、コメント、switchとkeep-changesの既存機能を保持する
- [ ] #4 branch switchで指定したブランチを選べ、同じ先端を持つ複数ブランチや空のブランチも既存どおり扱う。goのブランチ選択や自動退避の仕様へ置き換えない
- [ ] #5 現在ブランチの削除拒否、削除のゴミ箱復旧、discard時の保存、拒否時の無変更とJSON/終了コードを新構文で検証する
- [ ] #6 list/create等と同じ文字列のブランチ名・つぼみ名でも名前として操作できる
<!-- AC:END -->
