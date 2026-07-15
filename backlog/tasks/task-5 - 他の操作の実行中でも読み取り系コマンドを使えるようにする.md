---
id: TASK-5
title: 他の操作の実行中でも読み取り系コマンドを使えるようにする
status: To Do
assignee: []
created_date: '2026-07-15 16:15'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
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
- [ ] #1 別プロセスがロックを保持していても`status`と`log`が成功する
- [ ] #2 中断された操作が残っている場合、次回起動時のリカバリは従来どおり実行される
- [ ] #3 リカバリのスキップ条件と実行条件がテストで検証されている
<!-- AC:END -->
