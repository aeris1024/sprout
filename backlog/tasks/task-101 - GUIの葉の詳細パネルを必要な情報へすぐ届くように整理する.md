---
id: TASK-101
title: GUIの葉の詳細パネルを必要な情報へすぐ届くように整理する
status: To Do
assignee: []
created_date: '2026-10-30 17:54'
labels:
  - gui
  - usability
dependencies: []
references:
  - gui/src/components/CommitPanel.tsx
  - gui/src/App.css
  - gui/README.md
priority: medium
type: enhancement
ordinal: 100000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
葉の詳細パネルは縦に長く、サンプルで高さ2,388pxあり、メモは2,023pxの位置にある。よく使うメモやラベルへ大きくスクロールする必要がある。幅は320px固定で、ファイル名やメッセージが読みにくい。幅700pxの画面ではマップの高さが198pxまで狭くなる。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 メモ・ラベル・タグ、プレビュー、保存済みファイルへ大きくスクロールせずに移動できる
- [ ] #2 移動や枝の作成など主要な操作が、詳細の先頭付近から使える
- [ ] #3 パネルの幅を変更でき、再起動後も維持される。マップが操作不能な幅にならない
- [ ] #4 狭いウィンドウでもマップとパネルの両方を実用的な大きさで操作できる
- [ ] #5 自動テストで既存の操作が引き続き使えることを検証し、gui/README.mdを更新する
<!-- AC:END -->
