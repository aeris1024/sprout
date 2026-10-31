---
id: TASK-119
title: GUIで操作の実行中に葉を押してもパネルを閉じないようにする
status: Done
assignee:
  - '@codex'
created_date: '2026-10-30 21:29'
updated_date: '2026-10-31 11:11'
labels:
  - gui
dependencies: []
references:
  - gui/src/App.tsx
priority: low
type: bug
ordinal: 118000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
葉のクリック処理は、操作の実行中かどうかを確かめる前にゴミ箱パネルと保守パネルを閉じる。そのため実行中の葉のクリックは、選択は無視されるのに、表示中のパネルだけが閉じる。TASK-107は読み込み中の選択を扱うが、書き込み操作の実行中にパネルが閉じる問題は対象にしていない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 書き込み操作の実行中に葉を押しても、表示中のゴミ箱パネルと保守パネルは閉じない
- [x] #2 操作の実行中でないときは、従来どおり葉を押すとパネルを閉じて葉の詳細を表示する
- [x] #3 自動テストで実行中と実行中でないときの両方を検証する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Guard leaf selection before panel changes; test busy trash and maintenance plus idle selection; verify GUI checks and finalize.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Moved the operation guard before trash and maintenance state changes. App regression tests hold actual purge/gc writes pending, verify leaf clicks neither close the panel nor send show, and verify idle selection after completion. Validation: App.test.tsx 120 passed; TypeScript passed; git diff --check clean.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Preserve trash and maintenance panels when a leaf is clicked during writes. Verified busy and idle behavior with two new App regressions; all 120 App tests and TypeScript pass.
<!-- SECTION:FINAL_SUMMARY:END -->
