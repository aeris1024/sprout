---
id: TASK-44
title: GUI向けCLI JSON契約と構造化エラーを追加する
status: Done
assignee:
  - '@codex'
created_date: '2026-08-08 19:59'
updated_date: '2026-08-08 20:08'
labels: []
dependencies:
  - TASK-19
  - TASK-21
  - TASK-22
  - TASK-28
  - TASK-43
references:
  - src/sprout/cli.py
  - src/sprout/errors.py
  - tests/test_cli.py
  - README.md
priority: medium
type: enhancement
ordinal: 44000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Tauri GUIが人間向け表示を解析せずSprout CLIを安定して呼び出せるようにする。GUIで使用する読み取り・更新コマンドにコマンド単位の--json成功出力を用意し、JSONモードの失敗はstderrへcode・message・detailsを持つJSONを1つ出力して非0で終了する。既存の人間向け出力と、バイナリをstdoutへ出すcatは変更しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 GUIで使用するinit、status、track、untrack、commit、log、tree、show、thumbnail、note、label、branch、switch、restoreがコマンド単位の--json成功出力を持つ
- [x] #2 JSON成功時のstdoutには有効なJSONが1つだけ出力され、人間向け装飾や進捗表示が混ざらない
- [x] #3 JSONモードの期待される失敗はstderrへcode、message、detailsを持つJSONを1つ出力し、非0終了する
- [x] #4 --jsonを指定しない既存の人間向け出力と終了動作が維持される
- [x] #5 READMEに対象コマンド、成功スキーマ、エラースキーマ、互換方針が記載される
- [x] #6 成功・失敗・日本語値を含むJSON契約がCLIテストで検証される
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. SproutErrorへ安定したcode/detailsを追加し、mainで--json指定時の期待される例外とCLI使用エラーを共通JSONへ変換する。 2. GUI対象コマンドへ成功時の--jsonスキーマを追加し、JSONモードでは人間向け表示・警告・進捗を抑止する。 3. 既存の通常表示を保つ回帰テスト、成功・失敗・日本語の契約テスト、READMEの契約説明を追加して全体検証する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
SproutErrorにcode/detailsを追加し、repository_lockedとuncommitted_changesをGUI判定可能にした。GUI対象コマンドへ成功JSONを追加し、JSON時の進捗・警告を抑止した。READMEとCLI契約テストを更新し、CLIテスト43件が成功した。

最終検証: uv run pytest -p no:cacheprovider で133 passed, 2 skipped。python -m compileall -q srcとgit diff --checkも成功した。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Tauri GUI向けに14コマンドの成功JSONと共通エラーJSON契約を追加した。ロック中・未コミット変更・引数・リポジトリ操作のエラーを機械判定可能にし、通常表示は維持した。READMEへスキーマと互換方針を記載し、全テスト133件成功・2件スキップで検証した。
<!-- SECTION:FINAL_SUMMARY:END -->
