---
id: TASK-90
title: GUIから追跡ファイルを移動・改名できるようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:34'
updated_date: '2026-10-31 09:29'
labels:
  - gui
dependencies:
  - TASK-83
  - TASK-125.3
references:
  - src/sprout/cli.py
  - gui/src/components/FilePanel.tsx
  - gui/README.md
  - README.md
priority: medium
type: feature
ordinal: 89000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GUIの追跡中ファイルから、file_idを維持して明示的に移動・改名できるようにする。
旧トップレベルmoveにはJSON引数がないが、正規file moveのJSON出力・構造化エラーの整備はTASK-125.3の担当とする。本タスクはその契約を使うGUI操作と連携の検証を担当し、別のmove実装や旧コマンドの恒久互換を重複して追加しない。
移動後の追跡一覧・未保存状態・マップ・上部バーを更新し、拒否時は入力を保持する。素材IDと改名履歴は、プレビューの素材関連付け廃止後も維持する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 TASK-125.3のfile move --jsonが移動前後のパスと共通の構造化エラーを返す契約をGUIから利用し、正常時・拒否時を検証する
- [ ] #2 ファイルパネルの追跡中ファイルから新しいパスを指定して移動・改名できる
- [ ] #3 移動後もfile_idが維持され、未保存の変更と追跡中一覧、マップ、上部バーの状態が更新される
- [ ] #4 移動先の衝突などでCLIに拒否された場合は理由を通知し、入力内容を残し、作業ファイルを変更しない
- [ ] #5 自動テストでCLIのJSON出力、GUIの移動、拒否時の動作を検証し、README.mdとgui/README.mdを更新する
<!-- AC:END -->
