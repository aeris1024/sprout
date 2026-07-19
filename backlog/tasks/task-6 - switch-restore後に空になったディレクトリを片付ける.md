---
id: TASK-6
title: switch/restore後に空になったディレクトリを片付ける
status: Done
assignee:
  - '@cursor'
created_date: '2026-07-15 16:15'
updated_date: '2026-07-19 19:17'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
modified_files:
  - src/sprout/repository.py
  - tests/test_repository.py
priority: low
type: bug
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 問題

`_materialize`は復元対象に含まれないファイルをbackupディレクトリへ退避するが、ファイルが消えて空になったディレクトリは作業フォルダに残り続ける。ブランチ切り替えを繰り返すと空ディレクトリが蓄積する。

## 修正方針

`_materialize`の成功後(`_finalize_materialization`の後)に、退避・削除したパス(`current - set(target)`のファイルがあった親ディレクトリ)から`self.root`方向へ遡り、空のディレクトリを`os.rmdir`で削除する。注意点:

- `.sprout`(CONTROL_DIR)と`self.root`自体は削除しない。
- 未追跡ファイルが残っているディレクトリは空でないため`os.rmdir`が失敗する。これは正常系なので握りつぶす(空のときだけ消える挙動が正しい)。
- ロールバック(`_rollback_materialization`)側は既に`destination.parent.mkdir(parents=True)`で復元先ディレクトリを再作成するため変更不要。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ブランチ切り替えでファイルが無くなったディレクトリが空であれば削除される
- [x] #2 未追跡ファイルが残るディレクトリは削除されない
- [x] #3 プロジェクトルートと`.sprout`は削除されない
- [x] #4 空ディレクトリの削除がテストで検証されている
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. materializeで対象から除かれる追跡パスの親ディレクトリを収集する。
2. 正常完了後に深い順で空ディレクトリだけを削除し、rootと.sproutを保護する。
3. 空・非空ディレクトリのテストを追加する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
materialize成功後、除去した追跡パスの親を深い順にrmdirし、非空ディレクトリ、root、.sproutを維持する実装とテストを追加した。検証: uv run pytest (41 passed, 2 skipped)。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
switch/restore後に不要となった空ディレクトリを安全に削除し、未追跡ファイルを含むディレクトリと管理領域を保持するテストを追加した。全テスト成功。
<!-- SECTION:FINAL_SUMMARY:END -->
