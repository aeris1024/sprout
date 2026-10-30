---
id: TASK-119
title: GUIで操作の実行中に葉を押してもパネルを閉じないようにする
status: To Do
assignee: []
created_date: '2026-10-30 21:29'
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
- [ ] #1 書き込み操作の実行中に葉を押しても、表示中のゴミ箱パネルと保守パネルは閉じない
- [ ] #2 操作の実行中でないときは、従来どおり葉を押すとパネルを閉じて葉の詳細を表示する
- [ ] #3 自動テストで実行中と実行中でないときの両方を検証する
<!-- AC:END -->
