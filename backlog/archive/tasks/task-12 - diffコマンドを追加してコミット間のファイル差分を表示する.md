---
id: TASK-12
title: diffコマンドを追加してコミット間のファイル差分を表示する
status: Done
assignee:
  - '@cursor'
created_date: '2026-07-15 16:17'
updated_date: '2026-07-20 10:03'
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
  - README.md
priority: medium
type: feature
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

restoreやswitchの前に「何が変わるか」を確認する手段がない。内容差分(バイナリ差分)は不要で、ファイルレベルの added / modified / deleted 一覧があれば十分実用になる。

## 実装方針

`sprout diff [COMMIT_A] [COMMIT_B]`コマンドを追加する。

1. 引数の解決は既存の`resolve_commit`(完全ID、プレフィックス、ブランチ名)を再利用する。
2. 比較ロジック: `manifest(a)`と`manifest(b)`を取得し、パス集合の差と`(object_hash, size)`の不一致で added / modified / deleted を分類する。`status()`と同様のシンプルな辞書比較で実装できる。
3. 引数の省略時挙動:
   - 引数2つ: コミットAからコミットBへの差分。
   - 引数1つ: 指定コミットと作業ツリーの差分(作業ツリー側は追跡ファイルをハッシュしてsignatureを作る)。
   - 引数なし: HEADコミットと作業ツリーの差分(`status`と同等だが同じ出力形式)。
4. 出力形式は`status`に合わせ`added <path>`等の行形式。サイズ変化(`1234 -> 5678`)を添えると親切。

リポジトリ層に`diff_manifests(a, b) -> list[StatusEntry]`のような純粋関数を作り、CLI層で表示する構成にするとテストしやすい。READMEのコマンド一覧に追記する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 2つのコミット指定でファイルレベルの差分(added/modified/deleted)が表示される
- [x] #2 コミット指定1つで作業ツリーとの差分が表示される
- [x] #3 ブランチ名・IDプレフィックスでコミットを指定できる
- [x] #4 READMEのコマンド一覧に`diff`が追記されている
- [x] #5 差分の分類がテストで検証されている
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. `diff_manifests` で path / (hash,size) 比較し added/modified/deleted を返す
2. `Repository.diff` で 0/1/2 引数（HEAD↔作業ツリー、コミット↔作業ツリー、コミット間）を解決
3. CLI `sprout diff` で status 風の行出力（サイズ変化付き）
4. README 更新と分類テストを追加
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
実装: diff_manifests / Repository.diff / sprout diff。0・1・2引数に対応しサイズ変化を表示。
検証: pytest → 62 passed, 2 skipped。
- AC1/5: test_diff_classifies_added_modified_deleted_between_commits
- AC2/3: test_diff_against_working_tree_and_commit_refs / CLI
- AC4: README 更新
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
sprout diff を追加し、コミット間および作業ツリーとのファイルレベル差分（added/modified/deleted）を表示できるようにした。pytest 62 passed / 2 skipped で AC1–5 を確認。
<!-- SECTION:FINAL_SUMMARY:END -->
