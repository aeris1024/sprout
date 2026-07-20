---
id: TASK-33
title: リポジトリの容量と重複排除効果を確認できるようにする
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
ordinal: 34000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

大きなバイナリを繰り返しコミットすると `.sprout/objects` が肥大しやすい。現状はディスク使用量や重複排除でどれだけ節約できているかを知る手段がない。

## ゴール

リポジトリの保存量を要約表示するコマンド（例: `du` / `stats`）を追加する。スキーマ変更は行わない。

## 見せたい情報（例）

- objects の合計サイズとファイル数
- コミット数、追跡ファイル数など基本件数
- 可能なら「コミット上の論理合計」と「実オブジェクト合計」の差（重複排除の効果）

読み取り専用で、作業ツリーは変更しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 objectsの合計サイズと件数を表示できる
- [ ] #2 コミット数など基本的なリポジトリ統計を表示できる
- [ ] #3 可能なら重複排除による節約量が分かる
- [ ] #4 実行しても作業ツリーや追跡状態は変わらない
- [ ] #5 READMEに使い方が追記されている
- [ ] #6 統計表示がテストで検証されている
<!-- AC:END -->
