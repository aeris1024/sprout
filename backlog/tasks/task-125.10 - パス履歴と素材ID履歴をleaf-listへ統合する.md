---
id: TASK-125.10
title: パス履歴と素材ID履歴をleaf listへ統合する
status: Done
assignee:
  - '@codex'
created_date: '2026-10-31 07:33'
updated_date: '2026-10-31 15:59'
labels:
  - cli
  - usability
dependencies:
  - TASK-125.1
  - TASK-125.3
references:
  - src/sprout/cli.py
  - src/sprout/repository.py
  - tests/test_cli.py
  - tests/test_serve.py
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 134000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
現在のlogとfile-historyを別グループへ配置し直すだけでなく、履歴検索の正規入口をleaf listへ統合する。leaf list [PATH]が現在のlog、leaf list --file-id FILE_IDが現在のfile-historyに対応する。file historyを正規の別入口として追加しない。手打ちaliasのlogも同じ履歴検索を呼び出す。
パス指定は現在のブランチのそのパスの内容変更履歴、素材ID指定は全ブランチにある同じ素材の各保存記録であり、内容が変わらない記録や改名を含む。この範囲と抽出条件の差を隠さず明示する。leaf treeは全体構造の表示として維持する。ラベルは維持すると確定した。既存の--labelによる履歴絞り込みを保ち、TASK-125.15のプロジェクト全体ラベル一覧と区別する。高度なAND/OR検索の追加は含めない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 leaf listの引数なし・PATH指定と--file-id FILE_IDで現在のlog/file-historyの用途を提供し、独立したfile history正規コマンドを不要にする
- [x] #2 PATH指定は現在ブランチの内容変更履歴を保ち、素材ID指定は全ブランチの各保存記録・改名・パス・更新日時を欠落なく返す
- [x] #3 履歴範囲と記録の抽出条件をヘルプと出力で判別でき、PATHと素材ID等の無効な指定組み合わせは無変更で拒否する
- [x] #4 現在のlogの件数・oneline・JSON・ラベル完全一致の絞り込みを維持し、素材IDモードでのオプション対応範囲を明示して検証する。プロジェクト全体ラベル一覧とは検索対象を混同しない
- [x] #5 旧JSON利用箇所への影響を整理し、モードごとのデータ項目を維持するか変更が必要な契約を明示する。alias logとserveでも同じ検索結果を得られる
- [x] #6 素材IDの不正形式・未出現パス・空の履歴・複数ブランチ・改名・内容不変の記録を検証し、V1形式を変更しない
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Expose leaf list PATH or --file-id FILE_ID and route temporary log alias to the same callback. Preserve existing branch/path content-change JSON and all-branch file identity saved-record JSON. In file-ID mode support max-count/oneline summaries, reject PATH and label combinations explicitly, and explain scope in help/text. Test renames, branches, unchanged saves, labels, empty/bad IDs and paths, option failures, alias/serve parity and V1; update docs.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added canonical leaf list and extended the existing log callback with --file-id. Current-branch/path mode preserves id/note/labels JSON and exact label search; file-ID mode preserves existing commit_id/path/file_id/object_hash/size/mtime_ns/created_at/message JSON records across all branches, including unchanged saves, renames and deleted-branch history. File-ID mode supports count/oneline/JSON and explicitly rejects PATH or label combinations. Text and help explain scope. Legacy file-history stays temporary until125.8; no standalone file history canonical command was added. Verification before requested pause: tests/test_leaf_list.py + test_file_identity.py + test_cli_groups.py + test_serve.py:30passed26.05s; existing test_cli.py log/annotation regressions:3passed3.78s. No source changes after passing checks. New9tests cover scope, labels, unchanged/renamed/allbranch records, aliases/serve/JSON parity, empty histories, bad IDs/option combinations and unchanged repository/worktree/V1. git diff --check passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Unified path and immutable-file history under leaf list, preserving their distinct search scopes and JSON shapes. Added count/summary support for file-ID records, explicit invalid-option rejection, alias/serve parity and documentation. Verified33focused tests; V1 unchanged.
<!-- SECTION:FINAL_SUMMARY:END -->
