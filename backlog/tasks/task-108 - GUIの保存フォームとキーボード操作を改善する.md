---
id: TASK-108
title: GUIの保存フォームとキーボード操作を改善する
status: To Do
assignee: []
created_date: '2026-10-30 17:55'
labels:
  - gui
  - usability
dependencies: []
references:
  - gui/src/components/SavePanel.tsx
  - gui/src/components/SproutMap.tsx
  - gui/src/App.tsx
  - gui/README.md
priority: medium
type: enhancement
ordinal: 107000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
変更がなくても「保存して葉にする」を押せ、押すと「nothing to commit」のエラーになる。Escでパネルを閉じられず、Ctrl+Enterで保存できず、Ctrl+Sはフォームを開くだけである。Tabでパネルへ移るにはマップの全要素（58コミットで61か所）を通る必要があり、矢印キーで葉を移動できない。サムネイル欄の案内文も途中で切れている。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 変更がないときは保存を実行できず、理由が画面から分かる
- [ ] #2 メッセージ欄でCtrl+Enterを押すと保存でき、Escでキャンセルや詳細の閉じる操作ができる。入力中の内容を無断で失わない
- [ ] #3 矢印キーでマップの葉を移動でき、マップを1回のTabで通過して右パネルへ移れる
- [ ] #4 サムネイル欄の案内文が省略されずに読める
- [ ] #5 自動テストでキー操作とフォーカスの移動を検証し、gui/README.mdを更新する
<!-- AC:END -->
