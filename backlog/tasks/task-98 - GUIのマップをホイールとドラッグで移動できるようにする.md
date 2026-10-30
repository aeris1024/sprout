---
id: TASK-98
title: GUIのマップをホイールとドラッグで移動できるようにする
status: Done
assignee:
  - '@claude'
created_date: '2026-10-30 17:53'
updated_date: '2026-10-30 21:56'
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
- [x] #1 縦方向にスクロールできない場合、通常のホイールでマップを横に移動できる
- [x] #2 背景のドラッグでマップを移動でき、葉や枝名のクリックと干渉しない
- [x] #3 倍率を変えても、見ていた場所が画面の同じ付近に残る
- [x] #4 いまここへ戻る操作があり、スクロール後に現在位置を表示できる
- [x] #5 自動テストまたは実機確認で移動と倍率変更の動作を検証し、gui/README.mdを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Wheel scrolls the map sideways when it cannot scroll vertically. 2. Dragging the background pans without affecting leaf clicks. 3. Zoom keeps the viewed center. 4. A button returns to the current position. 5. Tests, real-browser check and docs.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Real-input browser run on 58 commits: wheel 6140 to 5540, background drag 5540 to 5240, zoom kept the view center at 1980, return button showed the current leaf, leaf clicks still select.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The map now moves with the wheel and background drag, keeps its place when zooming, and can return to the current position. Verified with SproutMap tests, 174 GUI tests and a scripted real-input browser run.
<!-- SECTION:FINAL_SUMMARY:END -->
