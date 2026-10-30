---
id: TASK-107
title: GUIの読み込み中もクリックを取りこぼさないようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:54'
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
- [ ] #1 読み込み中に別の葉を選ぶと、最後に選んだ葉の詳細が表示される。古い応答で上書きされない
- [ ] #2 葉の詳細の読み込みだけでは、上部バーのボタンが無効にならず、表示がちらつかない
- [ ] #3 書き込み操作は従来どおり1件ずつ実行され、実行中に受け付けない操作は理由が分かる
- [ ] #4 自動テストで連続選択と応答順の入れ替わりを検証する
<!-- AC:END -->
