---
id: TASK-125.7
title: GUIとサンプル生成を新しい正規CLI構文へ移行する
status: To Do
assignee: []
created_date: '2026-10-31 07:24'
updated_date: '2026-10-31 07:37'
labels:
  - cli
  - gui
  - usability
dependencies:
  - TASK-125.1
  - TASK-125.2
  - TASK-125.3
  - TASK-125.4
  - TASK-125.5
  - TASK-125.9
  - TASK-125.10
  - TASK-125.11
  - TASK-125.12
references:
  - gui/src/App.tsx
  - gui/src/components/PreviewImage.tsx
  - gui/src/components/ComparePanel.tsx
  - gui/src-tauri/src/lib.rs
  - scripts/create_sample_repo.py
  - gui/src/App.test.tsx
parent_task_id: TASK-125
priority: medium
type: enhancement
ordinal: 131000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
CLI再編に合わせてGUIと同梱スクリプトの呼び出しを正規構文へ統一する。GUIは手打ちaliasへ依存せずleaf/bud/branch/file/maintenance等を使う。
対象はAppや各パネル、プレビュー画像取得、Rust側のサムネイル取得とCLI/serve呼び出し、サンプルリポジトリ生成など実際の全利用箇所。GUIの表示用語や機能を増やすタスクではない。別途存在するTASK-88/89/90/91/121等のGUI機能追加とは範囲を分ける。
追補: go系・log系・message系・thumbnail系の操作統合後の正規構文を使う。特に移動、メモ編集、サムネイル生成元は旧案のbranch switch/leaf restore/leaf note/file coverへ移行しない。preview/LabelはTASK-125.13で方針を確認するまでは現行機能・既存呼び出しを保持し、その2領域の移行は決定後の実装タスクで追補する。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 決定済みのGUIの保存・履歴・詳細・分岐・移動・退避・部分復元・取り出し・説明編集・タグ・サムネイル・生成元・ゴミ箱・保守を統合後の正規構文で呼び出す
- [ ] #2 Rust側のサムネイル取得と常駐モードを含め、都度起動とserve経由の両方で操作・エラー通知・画像表示が従来どおり動作する
- [ ] #3 サンプル生成など同梱スクリプトの実コマンド呼び出しを移行し、生成される履歴・タグ・添付・つぼみ・ゴミ箱の内容を維持する
- [ ] #4 GUIのテストが新しい正規argvを検証し、GUIのテスト・型チェック・ビルドと該当Rustテストが成功する
- [ ] #5 決定済み領域で不要な旧構文の呼び出しを残さず、preview/LabelはTASK-125.13の確認前に削減・新構文移行せず現行動作を保持する
<!-- AC:END -->
