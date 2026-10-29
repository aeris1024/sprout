---
id: TASK-13
title: restoreで特定のファイルだけを復元できるようにする
status: Done
assignee:
  - '@cursor'
created_date: '2026-07-15 16:18'
updated_date: '2026-07-20 09:52'
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
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

「このファイルだけ昔の版に戻したい」は頻出のユースケースだが、現状の`restore`はスナップショット全体の復元しかできない。

## 実装方針

`sprout restore COMMIT [PATH...]`のようにパス引数を追加する(typerの可変長引数)。

1. パスは`_relative_file`(`must_exist=False`)で正規化し、対象コミットのmanifestに存在するか検証する。存在しなければ`SproutError`。ディレクトリ指定はmanifest内の前方一致(`prefix/`)で展開する。
2. 復元対象を「現在の作業ツリー相当のmanifest + 指定パスだけ対象コミットの状態に置き換えたもの」として構築し、既存の`_materialize`に渡す。こうするとステージング・バックアップ・リカバリの仕組みをそのまま再利用できる。
3. 部分復元では追跡集合(`tracked_paths`)とHEADブランチを変更しない点に注意。`_materialize`は現状`tracked_paths`を全置換するため、部分復元時は指定パスのみ追跡へ追加する形へ`_finalize_materialization`を調整する必要がある。
4. 安全性の判定(`_has_unsaved_changes` / `--discard`)は、指定パスに限定して判定する。指定外のファイルに未保存変更があっても部分復元は妨げない方が使いやすい。ただし復元によって上書きされる指定パス自体に未保存変更があれば従来どおり`--discard`を要求する。
5. 未追跡ファイルとの衝突は従来どおり中止する。

READMEに部分復元の説明を追記する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `restore COMMIT PATH`で指定ファイルのみが復元され、他のファイルは変更されない
- [x] #2 ディレクトリ指定でその配下の該当ファイルがまとめて復元される
- [x] #3 指定パスがコミットに存在しない場合は明確なエラーになる
- [x] #4 指定パスに未保存変更がある場合は`--discard`が要求される
- [x] #5 HEADブランチと指定外の追跡状態は変化しない
- [x] #6 READMEに部分復元の使い方が追記されている
- [x] #7 部分復元・衝突・discard要求がテストで検証されている
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. `restore COMMIT [PATH...]` でパス解決（正確一致 / ディレクトリ前方一致）を追加
2. `_materialize(..., partial=True)` で選択パスのみ書き戻し、追跡は追加のみ、HEAD は変更しない
3. `_has_unsaved_changes(paths=...)` で選択パス限定の discard 判定（他パスの未保存は無視）
4. CLI / README を更新し、部分復元・衝突・discard のテストを追加
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
実装: restore にパス引数、_materialize(partial=True) で選択パスのみ書き戻し・追跡は INSERT OR IGNORE、discard 判定は選択パス限定。
検証: pytest → 56 passed, 2 skipped。
- AC1/5: test_partial_restore_updates_only_selected_paths
- AC2: test_partial_restore_expands_directory_prefix
- AC3: test_partial_restore_rejects_missing_commit_path
- AC4: test_partial_restore_requires_discard_only_for_selected_paths
- AC6: README 更新
- AC7: 上記 + collision / CLI
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
sprout restore COMMIT [PATH...] で部分復元できるようにした。選択パスのみ書き戻し、HEAD/他追跡は維持、対象パスの未保存変更時のみ --discard を要求。pytest 56 passed / 2 skipped で AC1–7 を確認。
<!-- SECTION:FINAL_SUMMARY:END -->
