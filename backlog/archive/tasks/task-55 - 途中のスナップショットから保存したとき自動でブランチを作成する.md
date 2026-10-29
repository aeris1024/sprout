---
id: TASK-55
title: 途中のスナップショットから保存したとき自動でブランチを作成する
status: Done
assignee:
  - '@claude'
created_date: '2026-10-27 15:03'
updated_date: '2026-10-27 15:49'
labels:
  - cli
  - gui-redesign
dependencies:
  - TASK-52
references:
  - src/sprout/repository.py
documentation:
  - backlog/docs/doc-1 - GUI刷新設計-芽のマップ.md
priority: medium
type: feature
ordinal: 55000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## 背景

GUI刷新（doc-1、TASK-51）では、ブランチ先端以外のスナップショットへ移って変更し保存したとき、その芽から新しい枝が伸びて葉が付くようにする。現在のcommitは常に現在ブランチの先端を親にするため、途中のスナップショットを基にした変更が先端の上に積まれてしまう。

## ゴール

現在位置がブランチ先端以外のときにcommitすると、現在位置を起点とする新しいブランチを自動作成して切り替え、そこへコミットする。ブランチ名は自動で付け、後から変更できる。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 現在位置が現在ブランチの先端ならcommitは従来どおりそのブランチへ追加される
- [x] #2 現在位置が先端以外ならcommitは現在位置を親とし、新しく自動作成したブランチへ追加され、そのブランチへ切り替わる
- [x] #3 自動ブランチ名は既存のブランチ名と衝突せず、規則がREADMEに記載され、既存のbranch --renameで変更できる
- [x] #4 commitの人向け出力とJSON出力で、ブランチを自動作成したことと作成したブランチ名が分かる
- [x] #5 保存する変更がない場合はブランチを作らずに従来どおりnothing to commitとなる
- [x] #6 自動作成からcommit完了までが途中で失敗した場合、ブランチだけが残るなどの中途半端な状態にならない
- [x] #7 先端・途中・変更なし・名前衝突・失敗時の各場合がテストされる
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 実装と検証（2026-10-28）
- commitの親を記録した現在位置にし、変更なし判定も現在位置と比べる。現在位置が現在ブランチの先端と異なれば、branch-YYYYMMDD-HHMMSS（ローカル時刻、ブランチ名・タグ名と重なれば-2以降）を作成してhead_branchを切り替え、コミットをそこへ追加する。ブランチ作成・コミット挿入・先端と現在位置の更新は1つのBEGIN IMMEDIATEトランザクションで行い、失敗時は何も残らない。
- CommitResultにbranchとcreated_branchを追加し、commit --jsonにcreated_branch、人向け出力にCreated branch行を追加。
- 検証: pytest 250 passed, 19 skipped（先端・途中・変更なし・名前衝突・DB失敗時のテストを追加）。git diff --check成功。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
現在位置がブランチ先端以外のときのcommitで、現在位置を起点とする新しいブランチ（branch-YYYYMMDD-HHMMSS）を自動作成して切り替え、そこへコミットするようにした。先端では従来どおり。変更がなければブランチを作らない。ブランチ作成とコミットは1トランザクションで、失敗時に中途半端な状態を残さない。commitの出力とJSON、READMEを更新し、全250テスト成功で確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
