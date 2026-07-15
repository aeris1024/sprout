---
id: TASK-8
title: commitが消えたファイルを自動untrackするとき通知する
status: To Do
assignee: []
created_date: '2026-07-15 16:16'
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
- [ ] #1 コミット時に追跡が外れたファイルのパスがCLIに表示される
- [ ] #2 消えたファイルがない場合の出力は従来と変わらない
- [ ] #3 通知の表示がテストで検証されている
<!-- AC:END -->
