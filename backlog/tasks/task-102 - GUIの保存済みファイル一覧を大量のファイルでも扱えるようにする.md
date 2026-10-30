---
id: TASK-102
title: GUIの保存済みファイル一覧を大量のファイルでも扱えるようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:54'
labels:
  - gui
  - usability
dependencies: []
references:
  - gui/src/components/SnapshotFiles.tsx
  - gui/src/components/FilePanel.tsx
  - gui/README.md
priority: medium
type: enhancement
ordinal: 101000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
葉の詳細の保存済みファイルは、240ファイルのプロジェクトで検索やツリー表示がなく、パネルの中にさらにスクロール領域ができる。フォルダの選択欄が先頭に平坦に並び、全行に素材IDが表示され、実行ボタンは一覧の下にある。ファイルパネルの追跡中・未追跡の一覧にも検索がない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 保存済みファイルと、ファイルパネルの追跡中・未追跡の一覧をパス名で絞り込める
- [ ] #2 フォルダ単位で展開・選択でき、フォルダの選択欄が長く並ばない
- [ ] #3 素材IDは常に全行へ表示せず、必要なときに確認できる
- [ ] #4 一覧のスクロール位置に関係なく、選択件数と取り出し・戻す操作を使える
- [ ] #5 自動テストで絞り込みとフォルダ選択を検証し、gui/README.mdを更新する
<!-- AC:END -->
