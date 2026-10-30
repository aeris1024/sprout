---
id: TASK-100
title: GUIの比較で比較元と比較先をマップ上で分かるようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:54'
labels:
  - gui
  - usability
dependencies: []
references:
  - gui/src/components/ComparePanel.tsx
  - gui/src/components/SproutMap.tsx
  - gui/src/App.tsx
  - gui/README.md
priority: medium
type: enhancement
ordinal: 99000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
スナップショットの比較中は、比較元と比較先がマップ上で強調されず、右パネルのIDとメッセージでしか確認できない。マップのクリックで選べるのは比較先だけで、比較元の変更は選択欄に限られる。結果のサイズもバイト数のままで読みにくい。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 比較中は比較元と比較先の葉がマップ上で区別して表示される
- [ ] #2 マップから比較元と比較先の両方を選び直せる。比較元と比較先を入れ替えられる
- [ ] #3 比較結果のサイズが読みやすい単位で表示される
- [ ] #4 比較を閉じると強調が消え、比較は作業ファイルと現在位置を変更しない
- [ ] #5 自動テストで強調、選び直し、入れ替えを検証し、gui/README.mdを更新する
<!-- AC:END -->
