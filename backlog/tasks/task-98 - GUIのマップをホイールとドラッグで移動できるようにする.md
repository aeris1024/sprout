---
id: TASK-98
title: GUIのマップをホイールとドラッグで移動できるようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:53'
labels:
  - gui
  - usability
dependencies: []
references:
  - gui/src/components/SproutMap.tsx
  - gui/README.md
priority: medium
type: enhancement
ordinal: 97000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
芽のマップは横に長いが、通常のホイールでは動かず（Shift+ホイールのみ）、ドラッグでも移動できない。倍率を変えると現在位置へ飛び、見ていた場所を見失う（scrollLeftが200から4485へ移動することを確認）。いまここへ戻る操作もない。58コミットのプロジェクトではマップの幅が8,674pxになり、スクロールバーでの移動が主な手段になっている。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 縦方向にスクロールできない場合、通常のホイールでマップを横に移動できる
- [ ] #2 背景のドラッグでマップを移動でき、葉や枝名のクリックと干渉しない
- [ ] #3 倍率を変えても、見ていた場所が画面の同じ付近に残る
- [ ] #4 いまここへ戻る操作があり、スクロール後に現在位置を表示できる
- [ ] #5 自動テストまたは実機確認で移動と倍率変更の動作を検証し、gui/README.mdを更新する
<!-- AC:END -->
