---
id: TASK-125.6
title: Gitで馴染みのある手打ちaliasを正規CLIへ対応させる
status: To Do
assignee: []
created_date: '2026-10-31 07:24'
updated_date: '2026-10-31 08:59'
labels:
  - cli
  - usability
dependencies:
  - TASK-125.1
  - TASK-125.2
  - TASK-125.3
  - TASK-125.4
  - TASK-125.5
  - TASK-125.9
  - TASK-125.10
  - TASK-125.11
  - TASK-125.12
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
log [PATH] / --file-id FILE_ID -> leaf listの統合後の履歴検索
show LEAF -> leaf show LEAF
tree -> leaf tree
diff ... -> file diff ...
track PATH... -> file track PATH...
untrack PATH... -> file untrack PATH...
mv OLD NEW -> file move OLD NEW
switch NAME -> TASK-125.9で確定したgoの明示的ブランチ指定
stash push -> bud save
stash list -> bud list
stash pop BUD -> bud restore BUD
stash drop BUD -> bud delete BUD
tag -> leaf tag list
tag NAME [LEAF] -> leaf tag create NAME [LEAF]
通常ヘルプは正規10入口を中心とし、aliasの一覧と対応先も確認できるようにする。add/reset/checkout/rm/stash apply、Git式の省略スタック指定等は追加対象にしない。alias表外の旧トップレベル・旧フラグ構文すべてを恒久互換として残す要件ではない。
追補: 名前の配置変更だけでなく4系統の操作統合が完了した正規構文にaliasを対応させる。追加のpreview/ラベルaliasや旧互換はこのタスクでは新設しない。ラベル機能の維持・一覧・候補表示はTASK-125.15・TASK-125.16で確定済み。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 列挙した15パターンが統合後の正規処理へ対応し、logの素材ID検索、commitの既存オプション、stash pushのname/keep-files、dropの確認指定も利用できる
- [ ] #2 aliasと対応する統合後の正規処理で結果・JSON・終了コード・安全確認が一致する。switchは指定したブランチを選び、旧switchとの動作差は移動統合で確認した方針に従う
- [ ] #3 stash popは明示したBUDを復元して成功時に消費する既存bud restoreの動作であり、Gitのapplyや追跡設定の仕様を新設しない
- [ ] #4 引数なしのtagは一覧、tag NAME [LEAF]は作成となり、list/create等の語もタグ名として指定できる
- [ ] #5 通常ヘルプで正規入口を見つけやすく、別途aliasの全対応を確認でき、GitとSproutの動作差を利用者が理解できる
- [ ] #6 正規構文とaliasの対応、および不正な引数・衝突する名前・確認付き操作を自動テストで検証する
<!-- AC:END -->
