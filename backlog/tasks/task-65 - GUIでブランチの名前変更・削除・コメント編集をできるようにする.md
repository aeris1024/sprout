---
id: TASK-65
title: GUIでブランチの名前変更・削除・コメント編集をできるようにする
status: To Do
assignee: []
created_date: '2026-10-28 16:58'
labels: []
dependencies:
  - TASK-63
references:
  - gui/src/App.tsx
  - gui/src/components/SproutMap.tsx
  - src/sprout/cli.py
priority: medium
type: feature
ordinal: 65000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ブランチの名前変更・削除・コメント変更はCLIで行えるが、GUIにはブランチを選ぶ入口も操作もなく、ブランチのコメントも表示されない。

芽のマップや上部バーからブランチを選び、ブランチの情報確認と名前変更・削除・コメント編集を行えるようにする。ブランチはIDで識別し、CLIには現在の名前を渡す。

対象外: ブランチの切り替え専用UI、削除済みブランチの復活。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 芽のマップの枝名と上部バーの現在ブランチから、ブランチの詳細（名前・コメント・枝先のスナップショット・現在のブランチか）を開ける
- [ ] #2 ブランチの名前を変更でき、空・空白を含む・既存のブランチやタグと重複する名前はエラーとして通知され入力内容が失われない
- [ ] #3 ブランチのコメントを表示・変更・空にできる
- [ ] #4 現在ではないブランチを確認のうえ削除でき、確認画面でスナップショットは削除済みブランチ由来として残ることが説明される。現在のブランチは削除できない
- [ ] #5 操作後にマップ・上部バー・詳細の表示がブランチIDに基づいて更新され、名前変更後も同じ枝として表示される
- [ ] #6 GUIの自動テストで各操作とエラー時の表示を検証し、gui/READMEを更新する
<!-- AC:END -->
