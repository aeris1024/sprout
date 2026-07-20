---
id: TASK-31
title: 特定ファイルの変更履歴をlogで辿れるようにする
status: To Do
assignee: []
created_date: '2026-07-20 10:18'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/cli.py
priority: medium
type: feature
ordinal: 32000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

大きなバイナリを扱う運用では、「このファイルがいつ変わったか」だけを知りたいことが多い。現状の `log` はブランチ先端から親を辿るだけで、パス単位の履歴を見られない。

## ゴール

指定したパスについて、そのファイル内容が変わったコミットだけを時系列で表示できるようにする。スキーマ変更は行わない。

## 範囲

- 対象は追跡パス（またはコミット内に存在するパス）の履歴表示
- 既存の `log` にオプションを足すか、専用の見方を追加するかは実装時に決めてよい
- 内容が変わっていないコミットは出さない（または明示的に区別する）
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 指定パスの内容が変わったコミットが一覧できる
- [ ] #2 内容が同一のコミットは結果に出ない、または変化なしとして区別できる
- [ ] #3 存在しないパスや未登場のパスでは明確なエラーまたは空結果になる
- [ ] #4 READMEに使い方が追記されている
- [ ] #5 パス履歴の取得がテストで検証されている
<!-- AC:END -->
