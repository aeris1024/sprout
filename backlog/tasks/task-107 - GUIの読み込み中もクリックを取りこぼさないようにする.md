---
id: TASK-107
title: GUIの読み込み中もクリックを取りこぼさないようにする
status: Done
assignee:
  - '@codex'
created_date: '2026-10-30 17:54'
updated_date: '2026-10-31 11:18'
labels:
  - gui
  - usability
dependencies: []
references:
  - gui/src/App.tsx
priority: medium
type: enhancement
ordinal: 106000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
葉を選ぶたびに全体が操作中の状態になり、上部のボタンがほぼ無効になる（7個中6個を確認）。読み込み中に別の葉を押しても黙って無視され、続けて2つ押すと1つ目が選ばれたままになる。詳細の読み込みは変更を伴わないため、書き込み操作と同じ扱いにする必要がない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 読み込み中に別の葉を選ぶと、最後に選んだ葉の詳細が表示される。古い応答で上書きされない
- [x] #2 葉の詳細の読み込みだけでは、上部バーのボタンが無効にならず、表示がちらつかない
- [x] #3 書き込み操作は従来どおり1件ずつ実行され、実行中に受け付けない操作は理由が分かる
- [x] #4 自動テストで連続選択と応答順の入れ替わりを検証する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Separate read-only leaf detail requests from the single-writer busy state. Track request identity and invalidate responses on newer selection, project/panel change or a write. Verify out-of-order successes and failures, usable toolbar, closed/project contexts, and existing write serialization with GUI tests and type/build checks.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Leaf detail reads no longer use the single-writer operation lock. Request identity discards stale success/error responses after leaf, project, panel or operation changes; pending reads restart when appropriate. Loading details can be closed; busy leaf clicks explain the refusal. Seven new tests cover ordering, toolbar state, close/file/project contexts and refresh; existing write regressions stay green. Validation: all245 GUI tests, TypeScript and Vite build passed; git diff --check clean.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Keep leaf selection responsive while reading details and show only the latest wanted response. Maintain single-writer behavior and explain blocked selection. Verified245 GUI tests, type checking and build.
<!-- SECTION:FINAL_SUMMARY:END -->
