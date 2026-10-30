---
id: TASK-114
title: メモ・タグ・ブランチの削除をゴミ箱から戻せるようにする
status: To Do
assignee: []
created_date: '2026-10-30 18:06'
labels:
  - storage
  - v1
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/trash.py
  - gui/src/components/TrashPanel.tsx
  - README.md
priority: medium
type: feature
ordinal: 113000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
メモの削除や上書き、タグとブランチの削除はゴミ箱に残らず、元に戻せない。メモは最大2万文字あり、空にして保存するだけで消える。タグはpruneの保護にも使われる。`trash_entries.kind`のCHECK制約に関わるため、対象の種類はV1で決める。アプリは未運用のため、V1の保存形式を直接変更してよい。形式番号は1のままとし、旧構造からの移行は用意しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 メモの削除と、既存のメモを空にする操作がゴミ箱へ入り、内容と更新日時を復旧できる
- [ ] #2 タグの削除がゴミ箱へ入り、対象のコミットとコメントを含めて復旧できる
- [ ] #3 ブランチの削除がゴミ箱へ入り、枝先とコメント、IDを含めて復旧できる。同名のブランチやタグが既にある場合は理由を示して拒否する
- [ ] #4 対象のコミットが存在しない場合は復旧せず、理由を表示する
- [ ] #5 GUIのゴミ箱に種類が分かる名前で表示され、確認文が実際の動作と一致する
- [ ] #6 自動テストで削除、復旧、競合を検証し、README.mdとgui/README.mdを更新する
<!-- AC:END -->
