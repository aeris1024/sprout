---
id: TASK-125.11
title: メッセージとメモの編集をleaf editへ統合する
status: Done
assignee:
  - '@codex'
created_date: '2026-10-31 07:33'
updated_date: '2026-10-31 11:23'
labels:
  - cli
  - usability
dependencies:
  - TASK-125.1
references:
  - src/sprout/cli.py
  - src/sprout/repository.py
  - src/sprout/trash.py
  - gui/src/App.tsx
  - tests/test_cli.py
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 135000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
現在のmessageとnoteを別々の入口へ移すだけでなく、保存済み葉の説明を変更する正規入口をleaf edit LEAFへ統合する。メッセージは--message TEXT、メモの設定・変更・削除も同じeditから明示的に操作する。メモの確認はleaf showへ集約し、leaf note show/set/deleteを独立した正規入口として増設しない。
ラベルは維持すると確定した。このタスクはmessage/noteの統合を担当し、ラベルの付与/解除・全体一覧の具体的なCLI配置はTASK-125.15に委ねる。ラベルを廃止したり、メッセージやメモへ置き換えたりしない。メモ削除の具体的フラグ名等は着手時に整える。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 leaf edit LEAF --message TEXTでメッセージを、同じleaf editでメモの設定・変更・明示的な削除を操作でき、leaf showで現在のメモを確認できる
- [x] #2 別のleaf note正規入口を残さず、未指定のフィールドを変更しない。メッセージとメモを同時指定する場合は全体が成功するか全体を拒否する
- [x] #3 既存のメッセージ・メモの長さや正規化、空メッセージ拒否、メモ削除のゴミ箱保存と復旧の挙動を保持する
- [x] #4 保存ファイル・葉ID・親子関係を変更せず、入力検証・保存が失敗した場合に片方だけを書き換えない
- [x] #5 ラベル機能と既存付与情報・検索を維持し、ラベルのCLI配置と全体一覧はTASK-125.15へ委ねる。メッセージ/メモ編集でラベルを変更しない
- [x] #6 新構文の成功・不正入力・同時更新・明示削除・JSON・serveを検証し、V1形式を変更しない
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Add one locked repository edit transaction for optional message and note changes; reuse existing normalization, note trash recovery, and limits. Expose leaf edit LEAF --message/--note/--clear-note and preserve omitted fields. Test validation/storage failures, atomic simultaneous updates, note deletion recovery, labels/history/V1 invariants and CLI/serve behavior.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added locked edit_leaf transaction with shared note-writing helper, preserving old setters and omission semantics. leaf edit accepts --message/-m, --note and mutually-exclusive --clear-note; JSON includes current message and annotations. Tests verify validation failure, SQLite trigger failure after message update, and recovery-record failure all roll back both fields and trash; also note recovery, exact limits, labels/snapshot/position/V1 invariants. leaf_edit + trash_annotations + CLI + serve:98 passed in53.09s; diffcheck clean.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Unified message/note changes under leaf edit with atomic updates and note deletion recovery; leaf show remains the read entry. Verified98 tests including injected storage/recovery failures and unchanged labels/snapshots/V1.
<!-- SECTION:FINAL_SUMMARY:END -->
