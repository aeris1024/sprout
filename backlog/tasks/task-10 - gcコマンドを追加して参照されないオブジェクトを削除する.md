---
id: TASK-10
title: gcコマンドを追加して参照されないオブジェクトを削除する
status: Done
assignee:
  - '@cursor'
created_date: '2026-07-15 16:17'
updated_date: '2026-07-20 09:41'
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
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

`.sprout/objects`は増える一方で、不要オブジェクトを削除する手段がない(READMEの既知の制限)。また`commit`はオブジェクトを保存してから「file changed while committing」等の検証を行うため、コミットが失敗するとどのコミットからも参照されない孤児オブジェクトが残り、蓄積し続ける。

## 実装方針

`sprout gc`コマンドを追加する。

1. リポジトリロック(`@locked`)の下で実行する。実行中の他操作との競合を防ぐため必須。
2. `SELECT DISTINCT object_hash FROM commit_files`で参照中のハッシュ集合を取得する。
3. `objects/xx/<hash>`を走査し、集合に含まれないファイルを削除する。空になった`xx`ディレクトリも削除する。
4. `tmp/`に残った古い一時ファイル(`object-*`)も削除する。
5. 削除した個数と解放したバイト数を表示する。`--dry-run`オプションで削除対象の一覧表示のみ行えるようにする。

将来「コミット削除」機能が入ると参照集合が変わるだけで同じロジックが使えるため、参照集合の取得は独立した関数にしておくとよい。READMEの「現在の制限」からGC未対応の記述を更新すること。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `sprout gc`がどのコミットからも参照されないオブジェクトを削除する
- [x] #2 参照中のオブジェクトは削除されない
- [x] #3 `--dry-run`で削除せずに対象を確認できる
- [x] #4 実行中は他のSprout操作と排他される
- [x] #5 削除数と解放サイズが表示される
- [x] #6 READMEとコマンド一覧が更新されている
- [x] #7 孤児オブジェクトの削除と参照オブジェクトの保護がテストで検証されている
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. `referenced_object_hashes()` を独立関数として追加（commit_files の DISTINCT）
2. `@locked` の `gc(dry_run=False)` で objects 走査・孤児削除・空ディレクトリ削除・tmp の object-* 削除
3. 削除数と解放バイトを返す結果型を用意し、CLI `sprout gc [--dry-run]` で表示
4. README のコマンド一覧と制限の記述を更新
5. 孤児削除・参照保護・dry-run・ロック排他のテストを追加
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
実装: referenced_object_hashes() と @locked gc(dry_run)。孤児 objects と tmp/object-* を削除し、空 shard も片付ける。CLI は削除数・バイト数を表示し --dry-run で対象一覧。
検証: pytest tests/test_repository.py tests/test_cli.py → 48 passed, 2 skipped。
- AC1/2/7: test_gc_removes_orphans_and_keeps_referenced_objects
- AC3: test_gc_dry_run_lists_targets_without_deleting / test_gc_cli_...
- AC4: test_gc_is_rejected_while_repository_is_locked
- AC5: test_gc_cli_reports_removed_objects_and_supports_dry_run
- AC6: README コマンド一覧と制限の更新
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
sprout gc を追加し、どのコミットからも参照されない objects と残存 object-* 一時ファイルを削除できるようにした。--dry-run 対応、@locked で排他、README 更新済み。pytest 48 passed / 2 skipped で AC1–7 を確認。
<!-- SECTION:FINAL_SUMMARY:END -->
