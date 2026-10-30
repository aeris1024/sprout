---
id: TASK-89
title: GUIで素材の改名・移動をまたぐ履歴を確認できるようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:34'
labels:
  - gui
dependencies:
  - TASK-83
references:
  - src/sprout/cli.py
  - gui/src/components/SnapshotFiles.tsx
  - gui/README.md
priority: medium
type: feature
ordinal: 88000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-83で不変のfile_idと`sprout file-history`が追加されたが、GUIの保存済みファイル一覧は素材IDを表示するだけで、その素材の履歴を見られない。TASK-83の受け入れ条件はCLI・JSONでの確認までで、GUIでの履歴表示は範囲外だった。パス指定の履歴では追えない、改名・移動やブランチをまたぐ素材の履歴をGUIで確認できるようにする。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 葉の詳細の保存済みファイルから、その素材の履歴を開ける。file_idがないファイルでは履歴を開く操作が表示されない
- [ ] #2 履歴に各スナップショットのメッセージと、その時点のパスが表示され、改名・移動の前後のパスを確認できる
- [ ] #3 履歴の項目からマップ上の該当する葉を開ける。別のブランチや削除済みブランチ由来のスナップショットも同じ素材の履歴として表示される
- [ ] #4 履歴の表示は作業ファイル、現在位置、ブランチを変更しない。失敗時は理由を通知する
- [ ] #5 自動テストで改名をまたぐ履歴、葉への移動、失敗時の動作を検証し、gui/README.mdを更新する
<!-- AC:END -->
