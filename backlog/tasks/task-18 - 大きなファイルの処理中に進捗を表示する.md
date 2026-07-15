---
id: TASK-18
title: 大きなファイルの処理中に進捗を表示する
status: To Do
assignee: []
created_date: '2026-07-15 16:20'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
priority: low
type: enhancement
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

数GBのファイルをcommit/restoreすると、ハッシュ計算とコピーの間なにも表示されず、固まったように見える。

## 実装方針

1. リポジトリ層にプログレス通知用のコールバック(例: `progress: Callable[[str, int, int], None] | None` で「ファイル名、処理済みバイト、総バイト」を渡す)を追加し、`hash_file`・`_store_object`・`_materialize`のチャンクループから呼び出す。リポジトリ層では直接表示しない(CLI層の責務)。
2. CLI層では`typer.progressbar`(click由来)またはRichを使って表示する。typerは既にclickに依存しているため`typer.progressbar`なら依存追加なしで済む。
3. 出力がリダイレクトされている場合(`sys.stderr.isatty()`がFalse)は表示しない。
4. 閾値(例: 8MB)未満のファイルでは表示しないとノイズが減る。

コールバック未指定時のオーバーヘッドが無視できることを確認する(チャンクごとのNoneチェック程度に留める)。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 大きなファイルのcommitとrestoreで進捗が表示される
- [ ] #2 リダイレクト時や小さいファイルでは進捗表示が出ない
- [ ] #3 コールバック未指定時の動作は従来と同一である
- [ ] #4 進捗コールバックの呼び出しがテストで検証されている
<!-- AC:END -->
