---
id: TASK-92
title: GUIで移動せずに未保存の変更をつぼみとして残せるようにする
status: To Do
assignee: []
created_date: '2026-10-30 17:35'
labels:
  - gui
dependencies: []
references:
  - src/sprout/cli.py
  - gui/src/App.tsx
  - gui/README.md
priority: low
type: feature
ordinal: 91000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GUIでは「ここへ移動」時の自動退避と、つぼみの復元・破棄はできるが、`sprout bud --save`に相当する、移動せずに未保存の変更をつぼみとして残す操作がない。別の葉へ移動しなくても、今の変更を保存せずに取っておけるようにする。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 未保存の変更があるときだけ、つぼみとして残す操作を実行できる
- [ ] #2 実行後は作成されたつぼみがマップに表示され、未保存の変更と上部バーの状態がCLIの結果と一致する
- [ ] #3 失敗時は理由を通知し、作業ファイルとつぼみを変更しない
- [ ] #4 自動テストで実行、変更がない場合、失敗時の動作を検証し、gui/README.mdを更新する
<!-- AC:END -->
