---
id: TASK-102
title: GUIの保存済みファイル一覧を大量のファイルでも扱えるようにする
status: Done
assignee:
  - '@codex'
created_date: '2026-10-30 17:54'
updated_date: '2026-11-01 05:11'
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
- [x] #1 保存済みファイルと、ファイルパネルの追跡中・未追跡の一覧をパス名で絞り込める
- [x] #2 フォルダ単位で展開・選択でき、フォルダの選択欄が長く並ばない
- [x] #3 素材IDは常に全行へ表示せず、必要なときに確認できる
- [x] #4 一覧のスクロール位置に関係なく、選択件数と取り出し・戻す操作を使える
- [x] #5 自動テストで絞り込みとフォルダ選択を検証し、gui/README.mdを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 保存済み一覧を検索可能な折りたたみフォルダツリーにし、検索中の選択範囲と非表示の選択保持を明示する。 2. 素材IDを必要時に開く詳細へ移し、選択件数と実行操作をスクロール中も使える位置へ固定する。 3. 追跡中・未追跡の一覧にもパス検索を加える。 4. 絞り込み・フォルダ選択・大量ファイルのブラウザー検証と全GUIテスト、README更新を行う。
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
保存済みファイルを検索・折りたたみツリー・フォルダ選択へ変更。検索外の選択保持を表示し、素材IDは詳細へ、操作欄は下端固定へ移動。追跡中と未追跡にも検索を追加。GUI274テストとビルド成功。Playwrightで240件・280pxパネルの上端/中間/下端でも操作欄が表示され横はみ出しがないことを検証。
<!-- SECTION:FINAL_SUMMARY:END -->
