---
id: TASK-117
title: GUIの比較結果で長いパスの全体を確認できるようにする
status: To Do
assignee: []
created_date: '2026-10-30 21:29'
labels:
  - gui
dependencies: []
references:
  - gui/src/components/ComparePanel.tsx
  - gui/src/App.css
priority: low
type: enhancement
ordinal: 116000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
スナップショットの比較結果では、長いパスが省略表示されるが、ファイルパネルと違って全体を確認する手段がない。TASK-95でファイルパネルの行を修正した際に見つかった。改名の行は元のパスと新しいパスを並べて表示するため、さらに省略されやすい。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 比較結果の行で省略されたパスの全体を、ポインタを重ねるかキーボードで確認できる
- [ ] #2 改名の行では元のパスと新しいパスの両方を確認できる
- [ ] #3 長いパスでも比較パネルに横スクロールが出ず、サイズの表示が隠れない
- [ ] #4 自動テストで全体の確認方法と改名の行を検証する
<!-- AC:END -->
