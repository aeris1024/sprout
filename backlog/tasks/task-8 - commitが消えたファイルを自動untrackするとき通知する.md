---
id: TASK-8
title: commitが消えたファイルを自動untrackするとき通知する
status: Done
assignee:
  - '@codex'
created_date: '2026-07-15 16:16'
updated_date: '2026-07-28 18:43'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
priority: low
type: enhancement
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 問題

`Repository.commit`は追跡中だが作業フォルダに存在しないファイルを`missing`として集め、コミット完了時に黙って`tracked_paths`から削除する。挙動自体は妥当(削除がコミットに記録される)だが、ユーザーには何も通知されないため、意図せず消えたファイルの追跡が外れたことに気づけない。

## 修正方針

`commit`の戻り値を拡張するか(例: `(commit_id, missing_paths)`のタプル、または結果dataclass)、`missing`リストを取得する手段を追加し、`cli.py`の`commit_command`で`deleted  <path>`のような行を出力する。リポジトリ層でechoしない(表示はCLI層の責務)。既存の呼び出し箇所とテストの修正も忘れないこと。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 コミット時に追跡が外れたファイルのパスがCLIに表示される
- [x] #2 消えたファイルがない場合の出力は従来と変わらない
- [x] #3 通知の表示がテストで検証されている
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. commit_idとremoved_pathsを持つCommitResult dataclassを追加し、Repository.commitの戻り値にする。 2. 既存呼び出し箇所をCommitResultへ移行し、CLIでdeleted行をコミット要約の前に表示する。 3. 削除あり・なしのRepository/CLIテストを追加し、全体テストを実行する。 4. 受け入れ条件を確認してBacklogを完了し、TASK-8単独でコミットする。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Repository.commitをCommitResult(commit_id, removed_paths)へ移行し、CLIがremoved_pathsをdeleted行として表示するようにした。削除なしの従来出力も検証。全テスト: 79 passed, 2 skipped。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Repository.commitを構造化されたCommitResultへ変更し、削除により自動解除された追跡パスをCLIでdeletedとして通知するようにした。削除なしの出力互換性を含め、全テスト79件成功・2件スキップで検証した。
<!-- SECTION:FINAL_SUMMARY:END -->
