---
id: TASK-114
title: メモ・タグ・ブランチの削除をゴミ箱から戻せるようにする
status: Done
assignee:
  - '@claude'
created_date: '2026-10-30 18:06'
updated_date: '2026-10-30 20:55'
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
- [x] #1 メモの削除と、既存のメモを空にする操作がゴミ箱へ入り、内容と更新日時を復旧できる
- [x] #2 タグの削除がゴミ箱へ入り、対象のコミットとコメントを含めて復旧できる
- [x] #3 ブランチの削除がゴミ箱へ入り、枝先とコメント、IDを含めて復旧できる。同名のブランチやタグが既にある場合は理由を示して拒否する
- [x] #4 対象のコミットが存在しない場合は復旧せず、理由を表示する
- [x] #5 GUIのゴミ箱に種類が分かる名前で表示され、確認文が実際の動作と一致する
- [x] #6 自動テストで削除、復旧、競合を検証し、README.mdとgui/README.mdを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add note_delete, tag_delete and branch_delete kinds and tags to recovery keys. 2. set_note on delete, delete_tag and delete_branch record recovery items. 3. Restore checks names and target snapshots first and reports clear reasons. 4. GUI labels and confirmation text. 5. Tests and docs.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Restore pre-checks the target snapshot, a newer note and name collisions so the reason is readable. Overwriting a note with other text is not recorded, per the acceptance criteria. Sample generator purges everything except the deleted leaf.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Deleted notes, tags and branches now go to the trash and return with their content, target and ID; conflicts are refused with clear reasons. Verified with tests/test_trash_annotations.py, TrashPanel tests, the full pytest suite (one follow-up fix to two exact-output CLI tests and the sample, rerun) and 143 GUI tests.
<!-- SECTION:FINAL_SUMMARY:END -->
