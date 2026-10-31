---
id: TASK-125.6
title: Gitで馴染みのある手打ちaliasを正規CLIへ対応させる
status: To Do
assignee: []
created_date: '2026-10-31 07:24'
labels:
  - cli
  - usability
dependencies:
  - TASK-125.1
  - TASK-125.2
  - TASK-125.3
  - TASK-125.4
  - TASK-125.5
references:
  - src/sprout/cli.py
  - src/sprout/serve.py
  - tests/test_cli.py
  - tests/test_serve.py
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 130000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
合意済みのaliasだけを手打ち用として追加する。Sproutの同じ操作への別名であり、Gitの内部モデルを追加しない。
commit -m TEXT -> leaf create -m TEXT
log [PATH] -> leaf list [PATH]
show LEAF -> leaf show LEAF
tree -> leaf tree
diff ... -> file diff ...
track PATH... -> file track PATH...
untrack PATH... -> file untrack PATH...
mv OLD NEW -> file move OLD NEW
switch NAME -> branch switch NAME
stash push -> bud save
stash list -> bud list
stash pop BUD -> bud restore BUD
stash drop BUD -> bud delete BUD
tag -> leaf tag list
tag NAME [LEAF] -> leaf tag create NAME [LEAF]
通常ヘルプは正規10入口を中心とし、aliasの一覧と対応先も確認できるようにする。add/reset/checkout/rm/stash apply、Git式の省略スタック指定等は追加対象にしない。alias表外の旧トップレベル・旧フラグ構文すべてを恒久互換として残す要件ではない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 列挙した15パターンが正規コマンドへ対応し、commit/log等の既存対応オプションとstash pushのname/keep-files、stash dropの確認指定も転送できる
- [ ] #2 aliasと正規構文で成功時のJSON・終了コード・保存結果、失敗時のエラーcode・確認要件・無変更が一致し、serve経由でも同じように動作する
- [ ] #3 stash popは明示したBUDを復元して成功時に消費する既存bud restoreの動作であり、Gitのapplyや追跡設定の仕様を新設しない
- [ ] #4 引数なしのtagは一覧、tag NAME [LEAF]は作成となり、list/create等の語もタグ名として指定できる
- [ ] #5 通常ヘルプで正規入口を見つけやすく、別途aliasの全対応を確認でき、GitとSproutの動作差を利用者が理解できる
- [ ] #6 正規構文とaliasの対応、および不正な引数・衝突する名前・確認付き操作を自動テストで検証する
<!-- AC:END -->
