---
id: TASK-26
title: serveコマンド(常駐モード)を追加してGUIの応答性を上げる
status: Done
assignee:
  - '@claude'
created_date: '2026-07-15 16:38'
updated_date: '2026-10-27 15:57'
labels: []
dependencies:
  - TASK-19
  - TASK-54
  - TASK-55
references:
  - src/sprout/cli.py
  - src/sprout/repository.py
priority: medium
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
- [x] #1 `sprout serve`が標準入出力のJSONで要求を受け付け応答する
- [x] #2 読み取り系・書き込み系の主要コマンドがserve経由で実行できる
- [x] #3 エラー時もプロセスが落ちず、エラーレスポンスが返る
- [x] #4 常駐中に別プロセスのCLI実行と安全に共存できる(ロックが機能する)
- [x] #5 プロトコル仕様がドキュメント化されている
- [x] #6 リクエスト・レスポンスの往復がテストで検証されている
- [x] #7 TASK-52〜55で追加・変更した現在位置、つぼみ、go、自動ブランチ作成付きcommitもserve経由で実行でき、通常CLIと同じJSONを返す
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
TASK-51のGUI刷新設計（doc-1）で、新GUI実装（TASK-57）の前提として本タスクを先に行うと決定した。優先度をMediumへ上げ、新しいCLI操作もserveで扱えるようTASK-54・55への依存を追加した。

既存の`sprout move`（追跡ファイルの移動）と名前が重なるため、スナップショット間を移動する新コマンドの名前をgoに決定した（2026-10-28 ユーザー決定）。

sprout serveを追加（src/sprout/serve.py）。要求{id,args,cwd?}を同一プロセス内でTyperアプリとして実行し、--jsonの出力を通常CLIと同じJSONで返す。エラーはcode/message/detailsで返しプロセスは継続。quitかEOFで終了。tests/test_serve.pyで往復・新コマンド（go/bud/自動ブランチcommit/現在位置）・エラー・cwd・別プロセスCLIとの共存とrepository_lockedを検証。pytest 262 passed, 19 skipped。GUIのserve切り替えはTASK-57で行う。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
JSON Linesで要求を受け付ける常駐モードsprout serveを追加し、通常CLIと同じJSONを1プロセスで返せるようにした。エラー時も継続し、リポジトリロックで別プロセスと共存する。READMEにプロトコルを記載し、全262テスト成功で確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
