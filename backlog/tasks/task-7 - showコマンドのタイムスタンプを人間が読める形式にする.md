---
id: TASK-7
title: showコマンドのタイムスタンプを人間が読める形式にする
status: To Do
assignee: []
created_date: '2026-07-15 16:15'
labels: []
dependencies: []
references:
  - src/sprout/cli.py
priority: low
type: enhancement
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 問題

`sprout show`はファイル一覧に`mtime_ns`を生のナノ秒整数(例: 1700000000123456700)で表示しており、人間には読めない。

## 修正方針

`cli.py`の`show`コマンドで、`item.mtime_ns`を`datetime.fromtimestamp(item.mtime_ns / 1e9)`(ローカルタイム)または`datetime.fromtimestamp(item.mtime_ns // 10**9, tz=timezone.utc)`で変換し、`2026-07-16 01:00:00`のような形式で表示する。コミット自体の`created_at`(ISO 8601のUTC)との表記揺れに注意し、どちらのタイムゾーンで表示するか統一する。DBに保存する`mtime_ns`自体は復元精度に必要なので変更しない。表示のみの修正。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `sprout show`のファイル行に日時が読める形式で表示される
- [ ] #2 DBおよび復元時のタイムスタンプ精度(ナノ秒)は変わらない
- [ ] #3 CLIテストで表示形式が検証されている
<!-- AC:END -->
