---
id: TASK-99
title: GUIのマップで葉の情報を確認し、目的の葉を探せるようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:54'
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
- [ ] #1 葉にポインタを重ねるかキーボードでフォーカスすると、メッセージの全文と日時を確認できる
- [ ] #2 メモやラベルがある葉をマップ上で見分けられる
- [ ] #3 メッセージ、タグ、ラベルで葉を検索または絞り込み、該当する葉へ移動して選択できる。該当なしの場合も分かる
- [ ] #4 検索や絞り込みは履歴と作業ファイルを変更せず、解除すると元の表示に戻る
- [ ] #5 自動テストで表示と検索の動作を検証し、gui/README.mdを更新する
<!-- AC:END -->
