---
id: TASK-16
title: logコマンドに表示件数の制限オプションを追加する
status: To Do
assignee: []
created_date: '2026-07-15 16:19'
labels: []
dependencies: []
references:
  - src/sprout/cli.py
  - src/sprout/repository.py
priority: low
type: enhancement
ordinal: 16000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

`sprout log`は常に全履歴を表示する。履歴が長くなると一覧性が悪い。

## 実装方針

`cli.py`の`log_command`に`-n/--max-count`オプション(int、既定はNone=全件)を追加する。リポジトリ層の`log()`に`limit`引数を追加し、親を遡るループを`limit`件で打ち切る(全件取得してからスライスしない。ループを止めるだけでよい)。あわせて1行表示の`--oneline`(`<ID先頭12桁> <メッセージ>`)を追加すると一覧性がさらに上がる。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `log -n 5`で最新5件のみ表示される
- [ ] #2 `-n`未指定時は従来どおり全件表示される
- [ ] #3 `--oneline`で1コミット1行の要約表示ができる
- [ ] #4 オプションの動作がテストで検証されている
<!-- AC:END -->
