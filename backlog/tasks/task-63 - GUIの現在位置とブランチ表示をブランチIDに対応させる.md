---
id: TASK-63
title: GUIの現在位置とブランチ表示をブランチIDに対応させる
status: To Do
assignee: []
created_date: '2026-10-28 16:57'
labels: []
dependencies: []
references:
  - gui/src/App.tsx
  - gui/src/lib/sprout.ts
  - gui/src/lib/sproutMap.ts
  - gui/src/components/CommitPanel.tsx
  - gui/src/components/BudPanel.tsx
  - gui/src/components/SproutMap.tsx
  - src/sprout/cli.py
priority: medium
type: enhancement
ordinal: 63000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-62でブランチに不変のIDが導入され、現在位置は専用の状態テーブルで管理されるようになった。しかしGUIは現在のブランチを名前で照合し、現在位置が欠けると枝先で補い、詳細パネルやつぼみでは作成時のブランチ名しか表示していない。また初回コミット前に退避したつぼみはマップに表示されず、GUIから戻すことも捨てることもできない。

GUIがブランチIDで枝を識別し、名前変更・削除・同名再作成の後も正しいブランチ名と状態を表示できるようにする。後続のメモ・ラベル・タグ編集、ブランチ操作のGUI対応の基盤とする。

対象外: previewの追加・削除・並べ替え操作（TASK-38）、メモ・ラベル・タグ・ブランチの編集操作。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 status・go・commit・switch・branch作成のJSONで現在または対象のブランチIDを確認でき、ブランチの名前変更・削除・コメント変更のJSONも対象のブランチIDを返す。既存のフィールドは維持される
- [ ] #2 GUIは現在のブランチをIDで判定し、移動・保存・名前変更・同名再作成の後もマップと上部バーの現在ブランチ表示が正しい
- [ ] #3 GUIはCLIが返す現在位置をそのまま使い、現在位置が無い場合に枝先で補わない。初回コミット前は現在位置なしとして表示する
- [ ] #4 スナップショットとつぼみの詳細で、作成時のブランチ名に加え、ブランチの現在の名前、または削除済みであることを判別できる
- [ ] #5 初回コミット前に退避したつぼみがGUIに表示され、選択して変更内容の確認・復元・破棄ができる
- [ ] #6 スナップショットの詳細で、登録されている添付を表示順どおりに種類・名前・形式・サイズとともに確認できる（操作は含まない）
- [ ] #7 CLIとGUIの自動テストで、ブランチIDの出力、改名・削除・同名再作成時の表示、初回コミット前のつぼみ表示を検証し、READMEとgui/READMEを更新する
<!-- AC:END -->
