---
id: TASK-105
title: GUIの画像プレビューを大きく表示できるようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:54'
labels:
  - gui
  - usability
dependencies: []
references:
  - gui/src/components/PreviewImage.tsx
  - gui/src/components/PreviewPanel.tsx
  - gui/README.md
priority: low
type: enhancement
ordinal: 104000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
静止画像のプレビューは右パネルの幅に収まる大きさでしか表示できず、1200×1600の画像が249×333で表示され、クリックしても拡大できない。細部の確認には取り出しが必要になる。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 パネル内の画像から、ウィンドウの大半を使う表示へ切り替えられる
- [ ] #2 拡大表示は等倍まで確認でき、Escや閉じるボタンで元へ戻れる
- [ ] #3 複数の画像プレビューを拡大表示のまま前後に切り替えられる
- [ ] #4 表示上限や未選択画像を読み込まない既存の規則を維持する
- [ ] #5 自動テストで開閉と切り替えを検証し、gui/README.mdを更新する
<!-- AC:END -->
