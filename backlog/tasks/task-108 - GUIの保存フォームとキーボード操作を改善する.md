---
id: TASK-108
title: GUIの保存フォームとキーボード操作を改善する
status: Done
assignee:
  - '@codex'
created_date: '2026-10-30 17:55'
updated_date: '2026-11-01 05:02'
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
- [x] #1 変更がないときは保存を実行できず、理由が画面から分かる
- [x] #2 メッセージ欄でCtrl+Enterを押すと保存でき、Escで最も内側のメニュー/候補/ダイアログを先に閉じ、必要に応じてキャンセルや詳細を閉じられる。1回のEscを親へ重複伝播させず入力を無断で失わない
- [x] #3 矢印キーでマップの葉を移動でき、マップを1回のTabで通過して右パネルへ移れる
- [x] #4 サムネイル欄の案内文が省略されずに読める
- [x] #5 自動テストでキー操作とフォーカスの移動を検証し、gui/README.mdを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 変更なしの保存をUIと実行入口で防ぎ理由を表示し、メッセージ欄のCtrl+Enterとサムネイル説明を改善する。 2. Escは子の消費済みイベントを尊重し、設定・比較・パネル・詳細を閉じても入力を保持する。 3. マップの葉・ブランチ・つぼみ・未保存を単一Tab停止と矢印移動にする。 4. キー操作・フォーカス・既存メニューと候補のテスト、ブラウザー確認、README更新を行う。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
GUI全272テスト成功、pnpm build成功。最後の保存フォーム確認条件の調整後、Esc関連2テストとビルドも成功。Playwrightで60枚の葉の矢印選択・単一Tab停止・右パネルへのTab退出・Ctrl+Enter保存、幅280pxの説明文が横に切れないことを検証。Tauriネイティブウィンドウ自体の手動確認は未実施。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
変更なしの保存を防止し、Ctrl+Enter保存、内側から閉じるEscと編集下書き保持、詳細の入力破棄確認、マップの単一Tab停止と矢印移動、サムネイル説明文の折り返しを実装。自動テスト・ビルド・実ブラウザーで検証しREADMEを更新。
<!-- SECTION:FINAL_SUMMARY:END -->
