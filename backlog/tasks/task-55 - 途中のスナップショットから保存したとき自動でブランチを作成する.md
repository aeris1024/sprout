---
id: TASK-55
title: 途中のスナップショットから保存したとき自動でブランチを作成する
status: To Do
assignee: []
created_date: '2026-10-27 15:03'
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
- [ ] #1 現在位置が現在ブランチの先端ならcommitは従来どおりそのブランチへ追加される
- [ ] #2 現在位置が先端以外ならcommitは現在位置を親とし、新しく自動作成したブランチへ追加され、そのブランチへ切り替わる
- [ ] #3 自動ブランチ名は既存のブランチ名と衝突せず、規則がREADMEに記載され、既存のbranch --renameで変更できる
- [ ] #4 commitの人向け出力とJSON出力で、ブランチを自動作成したことと作成したブランチ名が分かる
- [ ] #5 保存する変更がない場合はブランチを作らずに従来どおりnothing to commitとなる
- [ ] #6 自動作成からcommit完了までが途中で失敗した場合、ブランチだけが残るなどの中途半端な状態にならない
- [ ] #7 先端・途中・変更なし・名前衝突・失敗時の各場合がテストされる
<!-- AC:END -->
