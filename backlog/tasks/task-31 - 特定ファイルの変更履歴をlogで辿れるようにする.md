---
id: TASK-31
title: 特定ファイルの変更履歴をlogで辿れるようにする
status: Done
assignee:
  - '@cursor'
created_date: '2026-07-20 10:18'
updated_date: '2026-07-20 10:27'
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
- [x] #1 指定パスの内容が変わったコミットが一覧できる
- [x] #2 内容が同一のコミットは結果に出ない、または変化なしとして区別できる
- [x] #3 存在しないパスや未登場のパスでは明確なエラーまたは空結果になる
- [x] #4 READMEに使い方が追記されている
- [x] #5 パス履歴の取得がテストで検証されている
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Extend Repository.log with optional PATH; walk current branch parents and keep commits where the path object_hash differs from the parent (add/modify/delete). 2. Add optional PATH arg to CLI log; print a clear message when empty. 3. Document usage in README. 4. Add repository and CLI tests for change filtering and missing paths.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verified with pytest: test_log_path_filters_to_commits_that_change_content, test_log_path_includes_deletion_commits, test_log_path_cli_filters_history (plus full repository/cli suites).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added optional PATH to sprout log so only commits that change that file content are listed. Unseen paths print a clear empty message. Verified with repository and CLI tests; README updated.
<!-- SECTION:FINAL_SUMMARY:END -->
