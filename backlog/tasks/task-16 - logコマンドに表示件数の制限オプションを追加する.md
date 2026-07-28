---
id: TASK-16
title: logコマンドに表示件数の制限オプションを追加する
status: Done
assignee:
  - '@codex'
created_date: '2026-07-15 16:19'
updated_date: '2026-07-28 18:24'
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
- [x] #1 `log -n 5`で最新5件のみ表示される
- [x] #2 `-n`未指定時は従来どおり全件表示される
- [x] #3 `--oneline`で1コミット1行の要約表示ができる
- [x] #4 オプションの動作がテストで検証されている
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Repository.logへlimitを追加し、最新の一致コミットが指定件数に達した時点で履歴走査を止める。 2. log CLIへ-n/--max-count（1以上）と--onelineを追加する。 3. 通常履歴とパス絞り込みのlimit、未指定時、oneline、無効件数をテストする。 4. READMEを更新し、関連テストと全体テストを実行する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Repository.logにlimitを追加し、一致コミットが指定件数に達した時点で走査を停止するよう実装。CLIへ-n/--max-count（1以上）と--onelineを追加し、READMEを更新した。通常履歴・パス絞り込み・未指定・無効値をテスト。全テスト: 76 passed, 2 skipped。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
logへ-n/--max-countと--onelineを追加し、Repository.logは指定件数に達した時点で走査を停止するようにした。READMEとリポジトリ/CLIテストを更新し、全テスト76件成功・2件スキップで従来動作も確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
