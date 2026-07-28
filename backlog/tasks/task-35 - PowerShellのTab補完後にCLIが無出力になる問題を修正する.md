---
id: TASK-35
title: PowerShellのTab補完後にCLIが無出力になる問題を修正する
status: Done
assignee:
  - '@codex'
created_date: '2026-07-28 20:57'
updated_date: '2026-07-28 21:03'
labels: []
dependencies: []
references:
  - src/sprout/cli.py
  - tests/test_cli.py
modified_files:
  - src/sprout/cli.py
  - tests/test_cli.py
priority: high
type: bug
ordinal: 36000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
PowerShellでSproutのTab補完候補を表示した後、補完用環境変数が残留し、以後のstatus、log、helpなどが補完モードで無出力終了する問題を修正する。通常操作を継続でき、補完処理が中断されてもシェル状態を汚染しないようにする。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 PowerShellでTab補完を実行した後も通常のsproutコマンドが出力される
- [x] #2 補完処理が途中で中断または候補列挙を打ち切られても補完用環境変数が残留しない
- [x] #3 残留した補完用環境変数がある状態でも明示的な通常コマンドを実行できる
- [x] #4 補完候補の動的生成と既存のbash・zsh補完が維持される
- [x] #5 原因となる環境変数残留と復旧動作を自動テストで検証する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Typer生成のPowerShell補完スクリプトを安全なtry/finally形式へ補正し、環境変数を必ず復元する。 2. 明示的な通常コマンド実行時に残留した補完環境を無効化する防御を起動処理へ追加する。 3. 補完スクリプト、残留環境からの復旧、既存補完動作のテストを追加する。 4. 関連テストと全テストを実行して検証する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
PowerShell補完スクリプトをtry/finallyで保護し、補完前の環境変数を復元または削除するようにした。明示的な通常コマンドでは残留した補完モードを起動前に解除する。検証: 実際のTabExpansion2で候補4件、補完環境変数3件すべて残留なし。残留状態からstatusが終了コード0で復旧。全テスト97 passed, 2 skipped。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
PowerShellのTab補完後にSproutが無出力になる問題を修正した。補完環境の確実な後始末と通常コマンド側の自己復旧を追加し、実際のPowerShell補完と全テストで検証した。
<!-- SECTION:FINAL_SUMMARY:END -->
