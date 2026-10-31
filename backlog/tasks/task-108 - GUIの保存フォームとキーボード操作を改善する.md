---
id: TASK-108
title: GUIの保存フォームとキーボード操作を改善する
status: To Do
assignee: []
created_date: '2026-10-30 17:55'
updated_date: '2026-10-31 09:31'
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

既存エラーの日本語表示はTASK-124を維持する。Escは開いている最も内側のメニュー/候補/ダイアログを先に閉じ、その1回の操作で親の詳細まで閉じたり入力を失ったりしない。TASK-126の補助メニューやTASK-125.16のラベル候補がある場合も、この優先順位と矛盾させない。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 変更がないときは保存を実行できず、理由が画面から分かる
- [ ] #2 メッセージ欄でCtrl+Enterを押すと保存でき、Escで最も内側のメニュー/候補/ダイアログを先に閉じ、必要に応じてキャンセルや詳細を閉じられる。1回のEscを親へ重複伝播させず入力を無断で失わない
- [ ] #3 矢印キーでマップの葉を移動でき、マップを1回のTabで通過して右パネルへ移れる
- [ ] #4 サムネイル欄の案内文が省略されずに読める
- [ ] #5 自動テストでキー操作とフォーカスの移動を検証し、gui/README.mdを更新する
<!-- AC:END -->
