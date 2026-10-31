---
id: TASK-105
title: GUIの画像プレビューを大きく表示できるようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:54'
updated_date: '2026-10-31 09:30'
labels:
  - gui
  - usability
dependencies:
  - TASK-125.13
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

等倍の意味: 現行の画像表示APIは原本上限とは別に表示用画像を長辺2048px以内へ縮小する。ここでの等倍は取得した表示用画像の1ピクセルを画面の1ピクセルで示すこととし、原本が既に縮小されている場合は原本等倍と表示せず、その寸法と縮小済みであることを明示する。原本のデコード上限を超える取得や、新たな原本フル解像度経路をこのタスクの暗黙の要件にしない。
TASK-125.13の葉全体のプレビュー一覧の順序で切り替え、代表指定・素材関連付けを表示条件にしない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 パネル内の画像から、ウィンドウの大半を使う表示へ切り替えられる
- [ ] #2 拡大表示は取得した表示用画像の画素に対して等倍まで確認できる。原本から縮小済みの場合は元の寸法と縮小済みを明示し、Escや閉じるボタンで元へ戻れる
- [ ] #3 複数の画像プレビューを拡大表示のまま前後に切り替えられる
- [ ] #4 表示上限や未選択画像を読み込まない既存の規則を維持する
- [ ] #5 自動テストで開閉と切り替えを検証し、gui/README.mdを更新する
<!-- AC:END -->
