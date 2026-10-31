---
id: TASK-125.9
title: 移動系をgoへ統合して全体移動と部分復元の役割を分ける
status: Done
assignee:
  - '@codex'
created_date: '2026-10-31 07:33'
updated_date: '2026-10-31 16:07'
labels:
  - cli
  - usability
dependencies:
  - TASK-125.1
  - TASK-125.3
  - TASK-125.4
references:
  - src/sprout/cli.py
  - src/sprout/repository.py
  - gui/src/App.tsx
  - tests/test_cli.py
  - tests/test_serve.py
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 133000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
名前・配置の変更だけではなく、現在のgo、switch、パスなしrestoreという全体移動の重複を解消する。正規の全体移動をトップレベルgoへ集約し、ファイル指定の復元はfile restoreへ分離する。branch switchとleaf restoreを正規の別入口として増設しない。手打ち用switchはgoの明示的なブランチ指定へのaliasとする。
未保存変更は安全な既定動作としてつぼみへ退避する。現在のgoを単純に別名化すると、同じ先端を共有する複数ブランチ、指定ブランチの選択、空のブランチ、全体restoreのブランチを保つ動作等が失われるため、差分を整理してから統合する。従来の変更時拒否・明示破棄・ブランチを保った全体復元を統合先でどう扱うかと具体的オプション名は、実装前にユーザーと確認する。今回のタスク登録で未確認の挙動変更を確定しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 goを全体移動の正規入口、file restore LEAF PATH...を部分復元の入口として整理し、branch switchとleaf restoreの重複した正規入口を残さない
- [x] #2 未保存変更は既定でつぼみに退避し、移動失敗時に作業ファイル・現在位置・ブランチ・つぼみを部分的に変更しない
- [x] #3 ブランチを明示して移動したときは同じ先端を共有する別ブランチがあっても指定したブランチを選べ、空ブランチ・途中の葉への移動の扱いを明文化して検証する
- [x] #4 現在のgo/switch/全体restoreの動作差と、拒否・discard・ブランチを保つ復元の統合方針を実装前にユーザーと確認し、機能の消失や既定のデータ破棄を黙って導入しない
- [x] #5 file restoreは選択外の作業ファイル・現在位置・ブランチ先端を変更しない。branch createの作成後移動も同じ移動方針と失敗時の整合を保つ
- [x] #6 正規CLI、switch alias、serve、GUIの移動操作で決定した方針が一致し、V1保存形式を変更しない
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Implement the user-approved go policies with explicit branch/empty-branch navigation, keep-branch mode, mutually exclusive reject/discard and preserved default buds. Share navigation policy with canonical branch creation when --switch is requested; retain no-move creation default and legacy repository APIs until migration cleanup. Make switch delegate to explicit go mode, update nullable GUI result type, and verify selection, dirty handling, rollback, partial restore independence and CLI/serve contracts.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
User approved go consolidation: go TARGET preserves unsaved changes as a bud by default; a live branch name selects that branch explicitly even when tips coincide. go --branch NAME also supports empty branches; switch NAME aliases this explicit mode. go LEAF --keep-branch preserves current branch and tip while changing worktree/current position. --reject-changes refuses dirty worktrees; --discard keeps discarded changes in trash; those flags are mutually exclusive. branch create movement defaults to bud preservation. Intermediate-leaf saves create a new branch. All failures must leave files, position, branches and buds unchanged. Partial restoration requires file restore LEAF PATH...

Implemented the approved navigation contract recorded above: exact live branch names select that branch even with shared tips; explicit --branch supports empty branches and null current_commit; --keep-branch preserves branch/tip. Default dirty handling saves a bud, --reject-changes refuses, --discard retains recovery in trash; exclusive options validate before mutation. Canonical branch create retains its no-movement default and prior omitted-start-point guard; --switch shares these policies. switch now delegates to explicit go and returns the same JSON. Legacy Repository.switch/restore APIs remain until caller cleanup. GoResult GUI type accepts null and TypeScript check passed. Documented policies in README. Broad CLI/serve/grow/file run: 103 passed plus two obsolete switch expectations; after updating those expectations, rerun of those two and four existing repository go tests: 6 passed. All 105 selected cases plus four repository cases covered; new go/grow tests include injected rollback in all three policies, empty branch, shared tips, labels, conflicts and partial restore independence. git diff --check passed; V1 unchanged.

Review follow-up: grow_branch now catches BaseException so KeyboardInterrupt also removes a newly inserted unused branch after materialization rollback. Added injected OSError/KeyboardInterrupt cases for bud/reject/discard policies; final tests/test_go_cli_groups.py tests/test_grow_branch.py: 25 passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Unified whole-project navigation under go with explicit branches, keep-branch and safe dirty-work policies, including consistent switch and branch-create movement. Verified selected CLI/serve/repository rollback tests and GUI TypeScript; updated README and nullable empty-branch result type.
<!-- SECTION:FINAL_SUMMARY:END -->
