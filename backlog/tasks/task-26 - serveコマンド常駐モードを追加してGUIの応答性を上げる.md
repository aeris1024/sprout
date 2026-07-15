---
id: TASK-26
title: serveコマンド(常駐モード)を追加してGUIの応答性を上げる
status: To Do
assignee: []
created_date: '2026-07-15 16:38'
labels: []
dependencies:
  - TASK-19
references:
  - src/sprout/cli.py
  - src/sprout/repository.py
priority: low
type: feature
ordinal: 27000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

GUIは操作のたびに`sprout <cmd> --json`をサブプロセス起動する構成だが、毎回Pythonインタプリタの起動・リポジトリdiscover・リカバリ確認のコストがかかる。操作が増えると体感が悪くなるため、1プロセスで要求を受け続ける常駐モードを用意する。

## 実装方針

1. `sprout serve`コマンドを追加する。標準入力から1行1リクエストのJSON(JSON Lines)を読み、標準出力へ1行1レスポンスのJSONを返す。プロトコルはJSON-RPC 2.0のサブセットか、`{"id": 1, "command": "status", "args": {...}}` / `{"id": 1, "ok": true, "result": {...}}`程度の自前形式でよい(実装時に決定し、READMEに仕様を記載する)。
2. 対応コマンドは読み書き両方(status, log, show, tree, commit, switch, restore, track, untrack, thumbnail等)。内部では既存の`Repository`メソッドを直接呼ぶ。CLIの`--json`変換ロジック(TASK-19)を関数として切り出し、serveと通常CLIで共有する。
3. 排他制御: 書き込み系は既存の`@locked`がそのまま働くため追加実装は不要。常駐中も他プロセスのCLI実行と安全に共存できる。
4. リクエストごとに例外を捕捉し、`SproutError`は`{"ok": false, "error": "..."}`で返す。プロセスは落とさない。
5. EOFまたは`{"command": "quit"}`で終了する。起動時に`{"ready": true, "version": "..."}`を1行出力するとGUI側の起動確認が楽になる。
6. GUI(TASK-23の基盤)側は、将来このモードへ差し替えられるようCLI呼び出し部を抽象化してあるはず。serveへの切り替えは別途GUI側の作業として行う。

## 注意

discover時のリカバリ確認は起動時に1回だけ行われる。常駐中に別プロセスが中断した操作のリカバリは、書き込み操作のロック取得時には問題にならないが、必要なら書き込み系実行前に`active_operation`を確認する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `sprout serve`が標準入出力のJSONで要求を受け付け応答する
- [ ] #2 読み取り系・書き込み系の主要コマンドがserve経由で実行できる
- [ ] #3 エラー時もプロセスが落ちず、エラーレスポンスが返る
- [ ] #4 常駐中に別プロセスのCLI実行と安全に共存できる(ロックが機能する)
- [ ] #5 プロトコル仕様がドキュメント化されている
- [ ] #6 リクエスト・レスポンスの往復がテストで検証されている
<!-- AC:END -->
