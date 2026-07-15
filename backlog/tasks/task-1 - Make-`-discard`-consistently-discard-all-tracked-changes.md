---
id: TASK-1
title: '`--discard`で追跡済みの未コミット変更を一貫して破棄できるようにする'
status: To Do
assignee: []
created_date: '2026-07-14 21:40'
updated_date: '2026-07-14 21:48'
labels: []
dependencies: []
references:
  - src/sprout/repository.py
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
- [ ] #1 `--discard`を指定しない場合、追跡済みファイルに未コミットの追加、変更、削除、または移動があると、`restore`と`switch`は処理を拒否する。
- [ ] #2 `--discard`を指定した場合、一度もコミットされていない追跡済みファイルの追加や、未コミットのファイル移動があっても、`restore`と`switch`を実行できる。
- [ ] #3 `--discard`の指定にかかわらず、未追跡ファイルを削除も上書きもしない。復元先で未追跡ファイルと衝突する場合は、安全に処理を中止する。
- [ ] #4 CLIヘルプとREADMEに、`--discard`が追跡済みファイルのすべての未コミット変更を破棄し、未追跡ファイルには影響しないことが明記されている。
- [ ] #5 新たに追跡したファイル、移動したファイル、および復元先で未追跡ファイルと衝突する場合の`--discard`の挙動が自動テストで検証されている。
<!-- AC:END -->
