---
id: TASK-1
title: '`--discard`で追跡済みの未コミット変更を一貫して破棄できるようにする'
status: Done
assignee:
  - '@cursor'
created_date: '2026-07-14 21:40'
updated_date: '2026-07-19 19:17'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
modified_files:
  - src/sprout/repository.py
  - src/sprout/cli.py
  - tests/test_repository.py
  - tests/test_cli.py
  - README.md
priority: medium
type: bug
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`restore`と`switch`は、ユーザーが`--discard`を明示しても、コミットされていない追跡済みファイルがあると処理を拒否する。`--discard`を追跡済みファイルのすべての未コミット変更を破棄する指定として統一し、未追跡ファイルは引き続き削除も上書きもしない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `--discard`を指定しない場合、追跡済みファイルに未コミットの追加、変更、削除、または移動があると、`restore`と`switch`は処理を拒否する。
- [x] #2 `--discard`を指定した場合、一度もコミットされていない追跡済みファイルの追加や、未コミットのファイル移動があっても、`restore`と`switch`を実行できる。
- [x] #3 `--discard`の指定にかかわらず、未追跡ファイルを削除も上書きもしない。復元先で未追跡ファイルと衝突する場合は、安全に処理を中止する。
- [x] #4 CLIヘルプとREADMEに、`--discard`が追跡済みファイルのすべての未コミット変更を破棄し、未追跡ファイルには影響しないことが明記されている。
- [x] #5 新たに追跡したファイル、移動したファイル、および復元先で未追跡ファイルと衝突する場合の`--discard`の挙動が自動テストで検証されている。
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. --discard時の未コミット追加ファイル保護による拒否を撤廃し、_materializeの未追跡衝突保護は維持する。
2. 追加・移動・未追跡衝突と非discard拒否のテストを更新する。
3. CLIヘルプとREADMEを新しい意味に合わせる。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
未コミットの新規追跡ファイルと移動を--discardで破棄できるようにし、未追跡パスの衝突検査は維持した。検証: uv run pytest (41 passed, 2 skipped)。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
--discardを追跡済みの全未コミット変更を破棄する動作へ統一し、未追跡ファイル保護、CLIヘルプ、README、回帰テストを更新した。全テスト成功。
<!-- SECTION:FINAL_SUMMARY:END -->
