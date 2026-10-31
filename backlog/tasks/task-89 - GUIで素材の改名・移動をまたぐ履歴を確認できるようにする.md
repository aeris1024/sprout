---
id: TASK-89
title: GUIで素材の改名・移動をまたぐ履歴を確認できるようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:34'
updated_date: '2026-10-31 09:29'
labels:
  - gui
dependencies:
  - TASK-83
  - TASK-125.10
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
GUIの保存済みファイルから、同じ不変file_idの履歴を確認できるようにする。TASK-83の素材IDと履歴が基盤で、CLI再編後の正規入口はTASK-125.10のleaf list --file-id FILE_IDである。廃止する独立file-history/file history入口を前提にしない。
全ブランチの同一素材の保存記録を対象とし、内容不変の記録・各時点のパス・改名/移動もCLIの素材IDモードに従う。パス指定の変更履歴とは範囲を区別する。ここで開くのは選択した葉の詳細であり、goによる作業フォルダの移動ではない。
TASK-102が素材IDを通常表示から隠しても、内部のfile_idと素材履歴への操作は維持する。プレビューの素材関連付け廃止とは別機能。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 葉の詳細の保存済みファイルから、その素材の履歴を開ける。file_idがないファイルでは履歴を開く操作が表示されない
- [ ] #2 履歴に各スナップショットのメッセージと、その時点のパスが表示され、改名・移動の前後のパスを確認できる
- [ ] #3 履歴の項目からマップ上の該当する葉を開ける。別のブランチや削除済みブランチ由来のスナップショットも同じ素材の履歴として表示される
- [ ] #4 履歴の表示は作業ファイル、現在位置、ブランチを変更しない。失敗時は理由を通知する
- [ ] #5 自動テストで正規leaf listの素材ID呼び出し、改名/ブランチをまたぐ履歴、葉の詳細選択、失敗時を検証し、GUI READMEを更新する
<!-- AC:END -->
