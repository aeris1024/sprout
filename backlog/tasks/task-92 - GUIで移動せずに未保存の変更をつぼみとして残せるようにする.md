---
id: TASK-92
title: GUIで移動せずに未保存の変更をつぼみとして残せるようにする
status: Done
assignee:
  - '@claude'
created_date: '2026-10-30 17:35'
updated_date: '2026-10-30 21:45'
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
- [x] #1 未保存の変更があるときだけ、つぼみとして残す操作を実行できる
- [x] #2 実行後は作成されたつぼみがマップに表示され、未保存の変更と上部バーの状態がCLIの結果と一致する
- [x] #3 失敗時は理由を通知し、作業ファイルとつぼみを変更しない
- [x] #4 自動テストで実行、変更がない場合、失敗時の動作を検証し、gui/README.mdを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. SavePanelに「つぼみとして残す」を追加し、bud --saveを実行 2. 成功時はワークスペースを再取得、失敗時は理由を通知 3. テストとgui/README.md更新
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
SavePanelにボタンを追加しApp.tsxのkeepAsBudから bud --save を実行。変更なしはボタン無効、nothing_to_save失敗時は再取得して通知。vitest 159件成功、実CLIで bud --save が作業ファイルを変えないことを確認。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
GUIの未保存の芽パネルに「つぼみとして残す」を追加(移動せず bud --save)。App.test.tsxに実行・変更なし・失敗の3テストを追加し、gui/README.mdを更新。vitest全159件とtscが成功。
<!-- SECTION:FINAL_SUMMARY:END -->
