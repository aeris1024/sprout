---
id: TASK-33
title: リポジトリの容量と重複排除効果を確認できるようにする
status: Done
assignee:
  - '@cursor'
created_date: '2026-07-20 10:18'
updated_date: '2026-07-20 10:36'
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
- [x] #1 objectsの合計サイズと件数を表示できる
- [x] #2 コミット数など基本的なリポジトリ統計を表示できる
- [x] #3 可能なら重複排除による節約量が分かる
- [x] #4 実行しても作業ツリーや追跡状態は変わらない
- [x] #5 READMEに使い方が追記されている
- [x] #6 統計表示がテストで検証されている
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add read-only Repository.stats with commits/branches/tracked counts, on-disk object count/size, logical size (sum of commit_files sizes), unique size (per distinct hash), and dedup savings. 2. Add sprout stats CLI. 3. README. 4. Tests for dedup savings and non-mutation.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verified with pytest stats dedup/savings tests and CLI output; working tree unchanged.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added read-only sprout stats for object size/counts, commit/branch/tracked counts, and dedup savings (logical vs unique). Verified with repository and CLI tests; README updated.
<!-- SECTION:FINAL_SUMMARY:END -->
