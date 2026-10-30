---
id: TASK-111
title: 削除したコミットの連番を再利用せずゴミ箱から復旧できるようにする
status: Done
assignee:
  - '@claude'
created_date: '2026-10-30 18:06'
updated_date: '2026-10-30 18:29'
labels:
  - storage
  - v1
dependencies: []
references:
  - src/sprout/repository.py
  - src/sprout/trash.py
  - README.md
priority: high
type: bug
ordinal: 110000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`commits.seq`は現在の最大値+1で決まるため、最新の葉を削除して別の枝で保存すると同じ番号が再利用される。別の枝の先端を削除してから`main`で保存すると、ゴミ箱からの復旧が「UNIQUE constraint failed: commits.seq」で失敗し続けることを確認した。`seq`は作成順の根拠なので、再利用すると順序の意味も崩れる。アプリは未運用のため、V1の保存形式を直接変更してよい。形式番号は1のままとし、旧構造からの移行は用意しない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 コミットを削除しても、その連番は以後のコミットで再利用されない。つぼみとゴミ箱項目の連番も同じ規則に従う
- [x] #2 削除後に別のコミットを作っても、他に競合がなければ葉をゴミ箱から復旧でき、元の順序に戻る
- [x] #3 復旧の競合で表示する理由に、SQLiteの制約エラーをそのまま出さない
- [x] #4 連番の管理情報の破損を起動時の検査または`doctor`で検出する
- [x] #5 pruneと葉の削除を含む自動テストで番号の非再利用と復旧を検証し、README.mdを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add id_sequences table and allocate commit, bud and trash seq from it so numbers are never reused. 2. doctor reports a counter below MAX(seq). 3. restore_trash reports friendly conflict reasons. 4. Regression tests; README.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added id_sequences; commits, buds and trash entries allocate from it. Missing counter rejected on open, counter behind MAX(seq) reported by doctor as invalid_sequence.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Creation numbers now come from id_sequences and are never reused, so trash recovery of a deleted leaf succeeds and restores original order. Verified with tests/test_sequences.py (delete, prune, bud, trash, doctor, conflict wording) and the full pytest suite.
<!-- SECTION:FINAL_SUMMARY:END -->
