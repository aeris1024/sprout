---
id: TASK-5
title: 他の操作の実行中でも読み取り系コマンドを使えるようにする
status: Done
assignee:
  - '@cursor'
created_date: '2026-07-15 16:15'
updated_date: '2026-07-20 09:28'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
modified_files:
  - src/sprout/repository.py
  - tests/test_repository.py
priority: medium
type: enhancement
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 問題

`Repository.discover`はコマンド実行のたびに中断リカバリ確認のためリポジトリロックを取得する。ロックは非ブロッキングなので、大きなコミットなど長時間の操作が実行中だと、`sprout status`や`sprout log`のような読み取り系コマンドまで「another Sprout operation is already running」で失敗する。

## 修正方針

metaテーブルの`active_operation`はロックなしで読める(SQLiteのWALモードで読み取りは常に可能)。`discover`ではまずロックを取らずに`active_operation`を読み、空文字列ならリカバリ不要としてロック取得をスキップする。値が入っている場合のみロックを取得し、取得後にもう一度値を読み直してから(ロック待ちの間に完了している可能性があるため)`_recover_pending_materialization`を実行する。書き込み系コマンド(track/commit/switchなど)は従来どおり`@locked`で排他される。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 別プロセスがロックを保持していても`status`と`log`が成功する
- [x] #2 中断された操作が残っている場合、次回起動時のリカバリは従来どおり実行される
- [x] #3 リカバリのスキップ条件と実行条件がテストで検証されている
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. `Repository.discover` で、まずロックなしに `active_operation` を読む
2. 空ならリカバリとロック取得をスキップして返す
3. 値がある場合のみロックを取り、ロック後に `_recover_pending_materialization` を実行する（再読込は同メソッド内）
4. ロック保持中でも status/log（discover）が成功すること、および中断リカバリが従来どおり動くことをテストで検証する
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
実装: discover が active_operation が空のときロックをスキップ。値があるときのみロック下で _recover_pending_materialization を実行。
検証: pytest tests/test_repository.py tests/test_cli.py → 44 passed, 2 skipped。
- AC1: test_status_and_log_succeed_while_repository_is_locked
- AC2: test_discovers_and_recovers_interrupted_restore / test_discover_recovers_only_when_active_operation_is_set
- AC3: test_discover_skips_lock_when_no_active_operation / test_discover_recovers_only_when_active_operation_is_set
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Repository.discover が active_operation が空のときはロックなしで返すようにし、長時間の書き込み中でも status/log が使えるようにした。中断操作がある場合のみロック下で従来どおりリカバリする。pytest 全件（44 passed, 2 skipped）で AC1–3 を確認済み。
<!-- SECTION:FINAL_SUMMARY:END -->
