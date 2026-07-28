---
id: TASK-18
title: 大きなファイルの処理中に進捗を表示する
status: Done
assignee:
  - '@codex'
created_date: '2026-07-15 16:20'
updated_date: '2026-07-28 19:59'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
modified_files:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - tests/test_repository.py
  - tests/test_cli.py
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
- [x] #1 大きなファイルのcommitとrestoreで進捗が表示される
- [x] #2 リダイレクト時や小さいファイルでは進捗表示が出ない
- [x] #3 コールバック未指定時の動作は従来と同一である
- [x] #4 進捗コールバックの呼び出しがテストで検証されている
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. リポジトリへ任意のバイト進捗コールバックを追加し、作業ツリーのハッシュ、圧縮保存、オブジェクト伸長で通知する。 2. CLIに8MB閾値・stderr TTY限定のプログレス表示を追加し、commit/status/diff/restore/switchへ適用する。 3. コールバック通知、非TTY、小さいファイル、コールバック未指定時の互換動作をテストする。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
進捗はstderrがTTYの場合のみ有効化し、8MiB以上のファイルを1MiBチャンク単位で表示する。リポジトリ層は表示に依存せず任意コールバックへ通知する。検証: uv run pytest（90 passed, 2 skipped）。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
commit、status、diff、restore、switchの大容量ファイル処理に進捗表示を追加した。圧縮保存、作業ツリーのハッシュ、オブジェクトの検証・伸長からバイト進捗を通知し、非TTYと8MiB未満では表示しない。通知内容と表示条件を自動テストで確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
