---
id: TASK-63
title: GUIの現在位置とブランチ表示をブランチIDに対応させる
status: Done
assignee:
  - '@claude'
created_date: '2026-10-28 16:57'
updated_date: '2026-10-28 17:10'
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
- [x] #1 status・go・commit・switch・branch作成のJSONで現在または対象のブランチIDを確認でき、ブランチの名前変更・削除・コメント変更のJSONも対象のブランチIDを返す。既存のフィールドは維持される
- [x] #2 GUIは現在のブランチをIDで判定し、移動・保存・名前変更・同名再作成の後もマップと上部バーの現在ブランチ表示が正しい
- [x] #3 GUIはCLIが返す現在位置をそのまま使い、現在位置が無い場合に枝先で補わない。初回コミット前は現在位置なしとして表示する
- [x] #4 スナップショットとつぼみの詳細で、作成時のブランチ名に加え、ブランチの現在の名前、または削除済みであることを判別できる
- [x] #5 初回コミット前に退避したつぼみがGUIに表示され、選択して変更内容の確認・復元・破棄ができる
- [x] #6 スナップショットの詳細で、登録されている添付を表示順どおりに種類・名前・形式・サイズとともに確認できる（操作は含まない）
- [x] #7 CLIとGUIの自動テストで、ブランチIDの出力、改名・削除・同名再作成時の表示、初回コミット前のつぼみ表示を検証し、READMEとgui/READMEを更新する
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Repository: CommitResult・GoResultにbranch_idを追加し、現在のブランチID・名前・現在位置・枝先判定を1つのSQLスナップショットで返すhead_positionを追加する。delete_branch・rename_branch・set_branch_commentは対象のブランチIDを返す。
2. CLI: status・go・commit・switch・branch作成/削除/改名/コメント変更のJSONにbranch_idを追加する。既存フィールドは維持する。
3. GUI型: status・tree・goの現在位置と枝先判定、つぼみ一覧を必須にし、branch_idを追加する。App・芽のマップから枝先へのフォールバックを削除し、goの反映で現在ブランチをIDで判定する。
4. GUI表示: ブランチIDから現在の名前・作成時の名前・削除済みを判別する共通関数を作り、スナップショットとつぼみの詳細で使う。削除済みブランチのつぼみは戻しても今のブランチのままであることを示す。
5. 初回コミット前のつぼみ（base_commit_idがnull）を地面の『はじまり』横に並べ、コミットが無い場合も一覧から選択・復元・破棄できるようにする。
6. スナップショット詳細に添付一覧（種類・名前・形式・サイズ、CLIの表示順）を表示する。
7. Python・GUIテストを追加・更新し、README・gui/READMEを更新。pytest全体、vitest、tsc、vite buildで検証する。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 実装

Repositoryに現在のブランチID・名前・現在位置・枝先判定を1つのSQLスナップショットで返すhead_positionを追加した。CommitResult・GoResultにbranch_idを持たせ、delete_branch・rename_branch・set_branch_commentは対象IDを返す（更新もIDで行う）。CLIはstatus（パス指定を含む）・commit・go・switch・branch作成/削除/改名/コメント変更のJSONにbranch_idまたはidを追加した。既存フィールドは維持している。

GUIはstatus・tree・goの現在位置、枝先判定、つぼみ一覧を必須の型にし、Appと芽のマップから枝先へのフォールバックを削除した。goの反映で現在ブランチをIDで判定する。branchIdentity・branchIdentityLabelでブランチIDから現在の名前・作成時の名前・削除済みを判別し、葉とつぼみの詳細で表示する。削除済みブランチのつぼみには、戻しても今のブランチのままであることを表示する。

base_commit_idがnullのつぼみは地面の『はじまり』の横に並べ、スナップショットが無い場合は空のマップに一覧ボタンを出す。葉の詳細の『サムネイル』行を、CLIの表示順（role・position）による添付一覧（種類・元の名前・形式・サイズ）に置き換えた。

## 検証

- Python全体: .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp .test-tmp/task63-final3 は287 passed、19 skipped（Windowsのsymlink権限など環境条件）。
- 新規 tests/test_cli.py::test_json_reports_branch_identity_for_position_and_branch_edits で、作成・コメント変更・改名・switch・status・commit・go・削除・同名再作成のID出力を確認した。既存のJSON契約テストとserveテストにもbranch_idを追加した。
- GUI: vitest runは41 passed。改名・削除・同名再作成されたブランチの詳細表示、添付一覧、goの応答による現在ブランチのID判定、最初の保存前のつぼみ（マップ上と空のマップ）の選択・復元をDOMテストで確認した。マップのレイアウトテストで、枝先へのフォールバックが無いことと地面のつぼみの配置を確認した。
- tsc と vite build が成功。git diff --check も成功。
- Tauriの実ウィンドウでの手動確認は未実施。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
GUIがブランチIDで枝を識別するようにした。CLIのstatus・commit・go・switch・branch操作のJSONにブランチIDを追加し、GUIからは枝先へのフォールバックを削除した。詳細パネルでは、ブランチの現在の名前・作成時の名前・削除済みを判別できる。最初の保存前のつぼみと添付一覧も表示する。Python 287件成功（19件は環境条件でスキップ）、GUI 41件成功、型チェック・ビルド・差分チェックで確認した。
<!-- SECTION:FINAL_SUMMARY:END -->
