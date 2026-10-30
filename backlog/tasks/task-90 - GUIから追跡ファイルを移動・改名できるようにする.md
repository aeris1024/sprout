---
id: TASK-90
title: GUIから追跡ファイルを移動・改名できるようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:34'
labels:
  - gui
dependencies:
  - TASK-83
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
TASK-83により`sprout move`は素材のfile_idを維持する操作になったが、GUIには移動・改名の手段がない。GUIを使っていて外部で改名すると別の素材として扱われ、素材の履歴がつながらない。GUIから明示的に移動・改名できるようにする。なお`sprout move`は現在`--json`に対応しておらず、GUIは全コマンドに`--json`を付けて実行するため、そのままでは呼び出せない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `sprout move --json`が移動前後のパスを構造化して返し、失敗時は他のコマンドと同じ形式のJSONエラーを返す
- [ ] #2 ファイルパネルの追跡中ファイルから新しいパスを指定して移動・改名できる
- [ ] #3 移動後もfile_idが維持され、未保存の変更と追跡中一覧、マップ、上部バーの状態が更新される
- [ ] #4 移動先の衝突などでCLIに拒否された場合は理由を通知し、入力内容を残し、作業ファイルを変更しない
- [ ] #5 自動テストでCLIのJSON出力、GUIの移動、拒否時の動作を検証し、README.mdとgui/README.mdを更新する
<!-- AC:END -->
