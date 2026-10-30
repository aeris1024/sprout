---
id: TASK-99
title: GUIのマップで葉の情報を確認し、目的の葉を探せるようにする
status: Done
assignee:
  - '@claude'
created_date: '2026-10-30 17:54'
updated_date: '2026-10-30 22:03'
labels:
  - gui
  - usability
dependencies: []
references:
  - gui/src/components/SproutMap.tsx
  - gui/src/lib/sproutMap.ts
  - gui/README.md
priority: medium
type: enhancement
ordinal: 98000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
マップの葉のメッセージは短く省略され、ポインタを重ねても全文が表示されない。日時やメモ・ラベルの有無もマップからは分からない。検索や絞り込みもないため、コミット数が増えると目的の葉を1枚ずつ開いて探すことになる。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 葉にポインタを重ねるかキーボードでフォーカスすると、メッセージの全文と日時を確認できる
- [x] #2 メモやラベルがある葉をマップ上で見分けられる
- [x] #3 メッセージ、タグ、ラベルで葉を検索または絞り込み、該当する葉へ移動して選択できる。該当なしの場合も分かる
- [x] #4 検索や絞り込みは履歴と作業ファイルを変更せず、解除すると元の表示に戻る
- [x] #5 自動テストで表示と検索の動作を検証し、gui/README.mdを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Show the full message and time on hover and focus. 2. Mark leaves with notes or labels. 3. Search by message, tag and label with dimming, counts, Enter and arrows to select. 4. Tests, real-browser check and docs.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Real-browser run on 58 commits: searching 第12版 found 1 and dimmed 57, Enter selected and scrolled to it, Esc restored the map, hovering showed the full message and time. Search also matches case and composition insensitively.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Leaves show their full message and time on hover and focus, note and label marks appear on the map, and search by message, tag and label dims others and moves to matches. Verified with SproutMap tests, 181 GUI tests, 604 pytest passes and a scripted browser run.
<!-- SECTION:FINAL_SUMMARY:END -->
